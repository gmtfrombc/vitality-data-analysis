"""Tests for etl.json_ingest.ingest."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from etl.json_ingest import ingest

# Minimal sample JSON with two patients and nested vitals
SAMPLE = [
    {
        "id": "p1",
        "first_name": "A",
        "last_name": "B",
        "vitals": [
            {"patient_id": "p1", "date": "2025-01-01", "weight": 80},
            {"patient_id": "p1", "date": "2025-01-15", "weight": 79},
        ],
    },
    {
        "id": "p2",
        "first_name": "C",
        "last_name": "D",
        "vitals": [{"patient_id": "p2", "date": "2025-02-01", "weight": 90}],
    },
]


@pytest.fixture()
def tmp_json_file(tmp_path: Path):
    f = tmp_path / "patients.json"
    f.write_text(json.dumps(SAMPLE))
    return f


@pytest.fixture()
def tmp_db_file(tmp_path: Path):
    db_file = tmp_path / "test.db"
    from app.utils.db_migrations import apply_pending_migrations

    apply_pending_migrations(str(db_file))
    return db_file


def _count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_ingest_idempotent(tmp_json_file: Path, tmp_db_file: Path):
    # first run
    ingest(tmp_json_file, tmp_db_file)
    conn = sqlite3.connect(tmp_db_file)
    try:
        assert _count(conn, "patients") == 2
        assert _count(conn, "vitals") == 3
    finally:
        conn.close()

    # second run should not duplicate
    ingest(tmp_json_file, tmp_db_file)
    conn = sqlite3.connect(tmp_db_file)
    try:
        assert _count(conn, "patients") == 2
        assert _count(conn, "vitals") == 3
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# New test – ensure ingest adds new patient rows when provided with fresh data
# ---------------------------------------------------------------------------


def test_ingest_additional_data(tmp_path: Path, tmp_db_file: Path):  # noqa: D103 – test
    # ------------------
    # 1. Initial ingest – two patients
    # ------------------
    f1 = tmp_path / "initial.json"
    f1.write_text(json.dumps(SAMPLE))

    ingest(f1, tmp_db_file)

    conn = sqlite3.connect(tmp_db_file)
    try:
        assert _count(conn, "patients") == 2
        assert _count(conn, "vitals") == 3
    finally:
        conn.close()

    # ------------------
    # 2. Second ingest – add new patient *and* an extra vitals record for p1
    # ------------------
    sample_extra = SAMPLE + [
        {
            "id": "p3",
            "first_name": "E",
            "last_name": "F",
            "vitals": [{"patient_id": "p3", "date": "2025-03-01", "weight": 85}],
        }
    ]
    # Also append a new vitals row for p1 to ensure upsert path handles duplicates gracefully
    sample_extra[0]["vitals"].append(
        {"patient_id": "p1", "date": "2025-02-20", "weight": 78}
    )

    f2 = tmp_path / "update.json"
    f2.write_text(json.dumps(sample_extra))

    result_counts = ingest(f2, tmp_db_file)

    # Confirm return dict has expected keys
    assert set(result_counts) >= {"patients", "vitals"}

    conn = sqlite3.connect(tmp_db_file)
    try:
        # New patient should have been inserted (total 3)
        assert _count(conn, "patients") == 3
        # New vitals rows: previous 3 + 1 new for p1 + 1 for p3 = 5
        assert _count(conn, "vitals") == 5
    finally:
        conn.close()
