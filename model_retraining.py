#!/usr/bin/env python3
"""model_retraining.py – Continuous feedback analysis & intent-classifier retraining

This script supports the *Continuous Feedback & Evaluation* workflow described in
``docs/ROADMAP_TESTING.md``.  It runs as an interactive CLI utility that:

1. Loads ☆negative☆ feedback (thumbs-down) from the ``assistant_feedback`` table
   in the SQLite database (see :pyfunc:`db_query.get_db_path`).
2. Analyses common issues & proposes actionable improvements to default
   assumptions / templates.
3. Presents each recommendation to the human-in-the-loop for approve / modify /
   decline decisions.
4. Applies approved changes:
   • Updates local training data for the *intent classifier*.
   • Retrains a lightweight text-classifier model (scikit-learn) – **fallback**
     only; the production system still prefers GPT-4 when available.
   • Saves the trained model to ``models/intent_classifier.pkl`` so the
     application can optionally use it when offline or as an ensemble signal.
   • Logs template-update suggestions to ``docs/template_change_queue.md`` so
     devs can review them in code-review.
5. Generates a markdown report summarising the run and stores it under
   ``logs/daily_retraining_report_<YYYY-MM-DD>.md``.

The script is *idempotent*: running it multiple times per day will append to the
existing report rather than overwrite it.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

# ---------------------------------------------------------------------------
# Optional heavy import – wrap to keep script functional when dependency absent
# ---------------------------------------------------------------------------
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import train_test_split
    import joblib

    _SKLEARN_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover – informative fallback
    _SKLEARN_AVAILABLE = False

# ---------------------------------------------------------------------------
# Local project imports – safe absolute paths
# ---------------------------------------------------------------------------
try:
    import db_query  # noqa: WPS433 – deliberately importing project module
except ImportError as exc:  # pragma: no cover
    print(
        "Error: Could not import project module 'db_query'. Ensure PYTHONPATH is set."
    )
    raise exc

# ---------------------------------------------------------------------------
# Constants & paths
# ---------------------------------------------------------------------------
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

TRAINING_DATA_PATH = (
    Path(__file__).resolve().parent / "data" / "intent_training_data.jsonl"
)
TRAINING_DATA_PATH.parent.mkdir(exist_ok=True, parents=True)

TEMPLATE_CHANGE_QUEUE = Path("docs/template_change_queue.md")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log_format = "% (asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("model_retraining")

# ---------------------------------------------------------------------------
# CLI Helpers
# ---------------------------------------------------------------------------


def _parse_args(argv: List[str] | None = None) -> argparse.Namespace:  # noqa: D401
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Analyze thumbs-down feedback & retrain intent classifier.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="How many days of feedback to analyse (default: 1)",
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        type=str,
        default=None,
        help="Optional path to SQLite DB (falls back to db_query.get_db_path())",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Step 1 – Fetch feedback
# ---------------------------------------------------------------------------


def _load_negative_feedback(
    days: int, db_path: str | None = None
) -> pd.DataFrame:  # noqa: D401
    """Return DataFrame with thumbs-down feedback from the past *days*."""

    db_file = db_path or db_query.get_db_path()
    if not os.path.exists(db_file):
        raise FileNotFoundError(f"SQLite database not found at {db_file}")

    since_dt = _dt.datetime.now() - _dt.timedelta(days=days)
    since_iso = since_dt.isoformat(timespec="seconds")

    conn = sqlite3.connect(db_file)
    try:
        df = pd.read_sql_query(
            """
            SELECT question, comment, created_at
            FROM assistant_feedback
            WHERE rating = 'down' AND created_at >= ?
            ORDER BY created_at DESC
            """,
            conn,
            params=(since_iso,),
            parse_dates=["created_at"],
        )
    finally:
        conn.close()

    logger.info("Loaded %s negative feedback entries (since %s)", len(df), since_iso)
    return df


# ---------------------------------------------------------------------------
# Step 2 – Basic heuristic analysis
# ---------------------------------------------------------------------------

_METRIC_KEYWORDS = {
    "bmi": ["bmi", "body mass index"],
    "weight": ["weight", "lbs", "kg"],
    "blood_pressure": ["blood pressure", "sbp", "dbp"],
    "a1c": ["a1c", "hba1c"],
    "height": ["height", "cm", "inches"],
}


def _extract_metric(text: str) -> str | None:  # noqa: D401
    text_lower = text.lower()
    for metric, keywords in _METRIC_KEYWORDS.items():
        if any(k in text_lower for k in keywords):
            return metric
    return None


class Suggestion(
    Dict
):  # simple dot-access convenience               # noqa: D401 – simple container
    """Container for a recommendation."""

    metric: str
    rationale: str
    proposal: str


def _analyse_feedback(df: pd.DataFrame) -> List[Suggestion]:  # noqa: D401
    """Generate a list of suggestions from feedback DataFrame."""

    suggestions: Dict[str, Suggestion] = {}

    for _, row in df.iterrows():
        combined_text = f"{row['question']}  {row.get('comment', '')}"
        metric = _extract_metric(combined_text)
        if not metric:
            # Bucket into generic category – skip for now
            continue

        suggestions.setdefault(
            metric,
            Suggestion(
                metric=metric,
                rationale="Multiple users expressed confusion around default assumptions.",
                proposal="",
            ),
        )
        # Simple heuristic: propose changing default active/inactive assumption
        suggestions[metric]["proposal"] = (
            f"Consider clarifying or changing the default assumption for '{metric.upper()}' – "
            "default to *active patients only* unless user specifies otherwise."
        )

    logger.info("Generated %s unique suggestion(s)", len(suggestions))
    return list(suggestions.values())


# ---------------------------------------------------------------------------
# Step 3/4 – Interactive CLI
# ---------------------------------------------------------------------------

_DEF_PROMPT = "Approve (y) / Modify (m) / Decline (n)? [y/m/n]: "


def _interactive_review(
    suggestions: List[Suggestion],
) -> List[Suggestion]:  # noqa: D401
    """Prompt the user to approve/modify/decline each suggestion."""

    approved: List[Suggestion] = []

    for suggestion in suggestions:
        print("\n—————————————————————————————————————————")
        print(f"Metric      : {suggestion['metric'].upper()}")
        print(f"Proposal    : {suggestion['proposal']}")
        print(f"Rationale   : {suggestion['rationale']}")

        while True:  # prompt until valid
            choice = input(_DEF_PROMPT).strip().lower()
            if choice in {"y", "n", "m"}:
                break

        if choice == "n":
            continue  # declined
        if choice == "m":
            new_text = input("Enter modified proposal: ").strip()
            if new_text:
                suggestion["proposal"] = new_text
            approved.append(suggestion)
        else:  # approved as-is
            approved.append(suggestion)

    logger.info("User approved %s suggestion(s)", len(approved))
    return approved


# ---------------------------------------------------------------------------
# Step 5 – Retrain intent classifier (optional)
# ---------------------------------------------------------------------------


def _load_training_data() -> List[Dict[str, str]]:  # noqa: D401
    """Load existing training records (JSONL)."""

    if not TRAINING_DATA_PATH.exists():
        return []

    records: List[Dict[str, str]] = []
    with TRAINING_DATA_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _append_training_examples(approved: List[Suggestion]):  # noqa: D401
    """Append simple synthetic records for each approved suggestion."""

    new_records: List[Dict[str, str]] = []
    for sug in approved:
        metric = sug["metric"]
        # Create synthetic negative example: user complaint implies current default wrong
        new_records.append(
            {"text": f"average {metric} of patients", "label": "clarify_active_status"}
        )
    if not new_records:
        return False

    with TRAINING_DATA_PATH.open("a", encoding="utf-8") as f:
        for rec in new_records:
            f.write(json.dumps(rec) + "\n")
    logger.info("Appended %s training record(s)", len(new_records))
    return True


def _retrain_classifier():  # noqa: D401
    """Retrain text-classification model using scikit-learn (if available)."""

    if not _SKLEARN_AVAILABLE:
        logger.warning("scikit-learn not installed – skipping classifier retraining.")
        return False

    records = _load_training_data()
    if not records:
        logger.warning("No training data available – skipping retraining.")
        return False

    texts = [r["text"] for r in records]
    labels = [r["label"] for r in records]

    X_train, X_val, y_train, y_val = train_test_split(
        texts, labels, test_size=0.2, random_state=42
    )

    pipeline: Pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(stop_words="english")),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )

    pipeline.fit(X_train, y_train)
    val_score = pipeline.score(X_val, y_val)

    model_path = MODELS_DIR / "intent_classifier.pkl"
    joblib.dump(pipeline, model_path)

    logger.info("Classifier retrained – validation accuracy: %.2f%%", val_score * 100)
    logger.info("Model saved to %s", model_path)
    return True


# ---------------------------------------------------------------------------
# Step 6 – Update template change queue
# ---------------------------------------------------------------------------


def _record_template_changes(approved: List[Suggestion]):  # noqa: D401
    """Append approved suggestions to template queue file."""

    if not approved:
        return False

    with TEMPLATE_CHANGE_QUEUE.open("a", encoding="utf-8") as f:
        for sug in approved:
            ts = _dt.datetime.now().isoformat(timespec="seconds")
            f.write(f"* {ts} – {sug['proposal']}  \n")

    logger.info("Recorded %s proposal(s) to template change queue", len(approved))
    return True


# ---------------------------------------------------------------------------
# Step 7 – Write daily report
# ---------------------------------------------------------------------------


def _write_report(df: pd.DataFrame, approved: List[Suggestion]):  # noqa: D401
    """Write markdown report summarising actions."""

    date_str = _dt.date.today().isoformat()
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    report_path = logs_dir / f"daily_retraining_report_{date_str}.md"

    lines: List[str] = []
    lines.append(f"# Daily Retraining Report – {date_str}\n")
    lines.append("## Feedback Processed\n")
    lines.append(f"Total negative feedback analysed: **{len(df)}**\n")

    if approved:
        lines.append("## Approved Changes\n")
        for sug in approved:
            lines.append(f"* **{sug['metric'].upper()}** – {sug['proposal']}")
    else:
        lines.append("No changes approved today.")

    # Write / append
    mode = "a" if report_path.exists() else "w"
    with report_path.open(mode, encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    logger.info("Report written to %s", report_path)
    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: List[str] | None = None):  # noqa: D401 – CLI entrypoint
    args = _parse_args(argv)

    df_feedback = _load_negative_feedback(days=args.days, db_path=args.db_path)
    if df_feedback.empty:
        print("No negative feedback to process – exiting.")
        return

    suggestions = _analyse_feedback(df_feedback)
    if not suggestions:
        print("No actionable suggestions generated – exiting.")
        return

    approved_changes = _interactive_review(suggestions)

    # Apply actions ---------------------------------------------------------
    if approved_changes:
        _append_training_examples(approved_changes)
        _retrain_classifier()
        _record_template_changes(approved_changes)

    _write_report(df_feedback, approved_changes)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(1)
