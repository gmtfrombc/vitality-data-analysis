"""Command-line ETL that ingests de-identified JSON export into SQLite.

Usage:
    python -m etl.json_ingest path/to/deidentified_patients.json [--db patient_data.db]

The script is **idempotent** – running twice will not create duplicates.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import sqlite3

from app.utils.db_migrations import apply_pending_migrations
from app.utils.saved_questions_db import DB_FILE  # reuse path helper

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Normalisers
# ---------------------------------------------------------------------------


def _norm_patients(raw: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(raw)
    allowed = {
        "id",
        "first_name",
        "last_name",
        "birth_date",
        "gender",
        "ethnicity",
        "engagement_score",
        "program_start_date",
        "program_end_date",
        "active",
        "etoh",
        "tobacco",
        "glp1_full",
    }
    present = [c for c in df.columns if c in allowed]
    return df[present]


def _extract_nested(raw: List[Dict[str, Any]], key: str) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for p in raw:
        nested = p.get(key) or []
        for item in nested:
            if "patient_id" not in item:
                item["patient_id"] = p["id"]
            rows.append(item)
    return pd.DataFrame(rows)


def _explode_scores(scores_df: pd.DataFrame) -> pd.DataFrame:
    if scores_df.empty:
        return scores_df
    melted = scores_df.melt(
        id_vars=["patient_id", "score_date"],
        var_name="score_type",
        value_name="score_value",
    )
    melted = melted.dropna(subset=["score_value"])
    melted = melted.rename(columns={"score_date": "date"})
    return melted


def _explode_mental(mh_df: pd.DataFrame) -> pd.DataFrame:
    if mh_df.empty:
        return mh_df
    melted = mh_df.melt(
        id_vars=["patient_id", "date"], var_name="assessment_type", value_name="score"
    )
    melted = melted.dropna(subset=["score"])
    return melted


def _explode_labs(lab_df: pd.DataFrame) -> pd.DataFrame:
    keep_cols = {"patient_id", "date"}
    long_rows = []
    for _, row in lab_df.iterrows():
        base = {"patient_id": row["patient_id"], "date": row["date"]}
        for col, val in row.items():
            if col in keep_cols or pd.isna(val):
                continue
            long_rows.append({**base, "test_name": col, "value": val})
    return pd.DataFrame(long_rows)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _bulk_upsert(
    df: pd.DataFrame, table: str, unique_cols: List[str], conn: sqlite3.Connection
):
    if df.empty:
        return 0
    placeholders = ", ".join(["?"] * len(df.columns))
    columns = ", ".join(df.columns)
    non_pk = [c for c in df.columns if c not in unique_cols]
    if non_pk:
        update_expr = ", ".join([f"{c}=excluded.{c}" for c in non_pk])
        conflict_clause = f"DO UPDATE SET {update_expr}"
    else:
        conflict_clause = "DO NOTHING"
    sql = (
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
        f"ON CONFLICT({', '.join(unique_cols)}) {conflict_clause};"
    )
    conn.executemany(sql, df.itertuples(index=False, name=None))
    return len(df)


# ---------------------------------------------------------------------------
# Main ingest
# ---------------------------------------------------------------------------


def ingest(json_path: Path, db_path: Path = Path(DB_FILE)) -> dict:
    apply_pending_migrations(str(db_path))
    raw = json.loads(Path(json_path).read_text())

    patients_df = _norm_patients(raw)
    vitals_df = _extract_nested(raw, "vitals").rename(
        columns={"systolic_pressure": "sbp", "diastolic_pressure": "dbp"}
    )
    scores_raw = _extract_nested(raw, "scores")
    scores_df = _explode_scores(scores_raw)
    mh_raw = _extract_nested(raw, "mental_health")
    mh_df = _explode_mental(mh_raw)
    labs_raw = _extract_nested(raw, "lab_results")
    labs_df = _explode_labs(labs_raw)
    pmh_df = _extract_nested(raw, "pmh_data").rename(columns={"name": "condition"})

    conn = sqlite3.connect(str(db_path))
    total = {}
    try:
        with conn:
            total["patients"] = _bulk_upsert(patients_df, "patients", ["id"], conn)
            total["vitals"] = _bulk_upsert(
                vitals_df, "vitals", ["patient_id", "date"], conn
            )
            total["scores"] = _bulk_upsert(
                scores_df, "scores", ["patient_id", "date", "score_type"], conn
            )
            total["mental_health"] = _bulk_upsert(
                mh_df, "mental_health", ["patient_id", "date", "assessment_type"], conn
            )
            total["lab_results"] = _bulk_upsert(
                labs_df, "lab_results", ["patient_id", "date", "test_name"], conn
            )
            # pmh_id auto; duplicates allowed
            total["pmh"] = _bulk_upsert(pmh_df, "pmh", ["pmh_id"], conn)
        logger.info("Ingest complete: %s", total)

        # --------------------------------------------------------------
        # Persist audit row so we can trace each import operation
        # --------------------------------------------------------------
        try:
            audit_cols = [
                "filename",
                "patients",
                "vitals",
                "scores",
                "mental_health",
                "lab_results",
                "pmh",
            ]
            placeholders = ", ".join(["?"] * len(audit_cols))
            sql = f"INSERT INTO ingest_audit ({', '.join(audit_cols)}) VALUES ({placeholders})"
            conn.execute(
                sql,
                (
                    Path(json_path).name,
                    total.get("patients", 0),
                    total.get("vitals", 0),
                    total.get("scores", 0),
                    total.get("mental_health", 0),
                    total.get("lab_results", 0),
                    total.get("pmh", 0),
                ),
            )
            logger.info("Ingest audit row inserted.")
        except Exception as audit_exc:  # noqa: BLE001
            logger.error("Failed to insert ingest_audit row: %s", audit_exc)
    finally:
        conn.close()

    # Return dict so callers (e.g., Panel UI) can show success metrics
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest de-identified patient JSON export into SQLite."
    )
    parser.add_argument(
        "json_path", type=Path, help="Path to deidentified_patients.json"
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        type=Path,
        default=Path(DB_FILE),
        help="SQLite DB file (default patient_data.db)",
    )
    args = parser.parse_args()
    ingest(args.json_path, args.db_path)
