import argparse
import datetime as _dt
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List

# Re-use DB path from utils
try:
    from app.utils.saved_questions_db import DB_FILE  # type: ignore
except Exception:
    DB_FILE = "patient_data.db"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


###############################################################################
# Helper functions
###############################################################################


def _connect(db_file: str | None = None) -> sqlite3.Connection:
    """Return SQLite connection with row_factory=sqlite3.Row."""
    path = db_file or DB_FILE
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_feedback(
    hours: int = 24, conn: sqlite3.Connection | None = None
) -> List[Dict]:
    """Return feedback rows from last *hours* sorted by newest first."""
    close_after = False
    if conn is None:
        conn = _connect()
        close_after = True

    since_ts = (_dt.datetime.utcnow() - _dt.timedelta(hours=hours)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    rows = conn.execute(
        """
        SELECT id, user_id, question, rating, comment, created_at
        FROM assistant_feedback
        WHERE datetime(created_at) >= ?
        ORDER BY created_at DESC
        """,
        (since_ts,),
    ).fetchall()

    if close_after:
        conn.close()
    return [dict(r) for r in rows]


def _fetch_logs(hours: int = 24, conn: sqlite3.Connection | None = None) -> List[Dict]:
    """Return assistant_logs rows for last *hours*."""
    close_after = False
    if conn is None:
        conn = _connect()
        close_after = True

    since_ts = (_dt.datetime.utcnow() - _dt.timedelta(hours=hours)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    rows = conn.execute(
        """
        SELECT query, generated_code, result_summary, duration_ms, created_at
        FROM assistant_logs
        WHERE datetime(created_at) >= ?
        ORDER BY created_at DESC
        """,
        (since_ts,),
    ).fetchall()

    if close_after:
        conn.close()
    return [dict(r) for r in rows]


###############################################################################
# Core triage logic
###############################################################################


def summarise(feedback: List[Dict]) -> Dict:
    """Return summary dict with rating counts and severity counts."""
    ratings = {"up": 0, "down": 0}
    severities = {"minor": 0, "wrong": 0, "dangerous": 0, "un-tagged": 0}

    for row in feedback:
        rating = row.get("rating")
        if rating in ratings:
            ratings[rating] += 1

        if rating == "down":
            comment = (row.get("comment") or "").lower()
            if "[minor" in comment:
                severities["minor"] += 1
            elif "[wrong" in comment:
                severities["wrong"] += 1
            elif "[dangerous" in comment:
                severities["dangerous"] += 1
            else:
                severities["un-tagged"] += 1
    return {"total": len(feedback), "ratings": ratings, "severity": severities}


def _print_summary(summary: Dict):
    print("=== Feedback Summary ===")
    print(f"Total entries: {summary['total']}")
    print(f" 👍  Up:   {summary['ratings']['up']}")
    print(f" 👎  Down: {summary['ratings']['down']}")
    print("--- Severity (👎 only) ---")
    for sev, cnt in summary["severity"].items():
        print(f"{sev:<10}: {cnt}")
    print()


def _join_feedback_logs(feedback: List[Dict], logs: List[Dict]) -> List[Dict]:
    """Attach generated_code to feedback rows when available (best-effort match by question)."""
    log_map = {}
    for log in logs:
        q = log.get("query")
        if q:
            # Keep first (most recent) log occurrence only
            log_map.setdefault(q, log)
    for row in feedback:
        row["generated_code"] = (log_map.get(row["question"], {}) or {}).get(
            "generated_code"
        )
    return feedback


def main():  # noqa: C901 – simple CLI tool
    parser = argparse.ArgumentParser(description="Triage recent assistant feedback.")
    parser.add_argument(
        "--hours", type=int, default=24, help="Look-back window in hours (default: 24)"
    )
    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Include generated code snippets (truncated)",
    )
    args = parser.parse_args()

    conn = _connect()
    feedback = _fetch_feedback(args.hours, conn)
    logs = _fetch_logs(args.hours, conn)

    feedback = _join_feedback_logs(feedback, logs)
    summary = summarise(feedback)
    _print_summary(summary)

    if not feedback:
        print("No feedback rows found in the given time window.")
        return

    print("=== Detailed Feedback (most recent first) ===")
    for row in feedback:
        print("\n-----")
        print(f"Time     : {row['created_at']}")
        print(f"Rating   : {row['rating']}")
        print(f"Question : {row['question'][:120]}")
        comment = row.get("comment") or ""
        if comment:
            print(f"Comment  : {comment}")
        if args.show_code and row.get("generated_code"):
            code_snip = row["generated_code"][:500]
            print("Code     :\n" + code_snip)
    print("\nDone.")


if __name__ == "__main__":
    main()
