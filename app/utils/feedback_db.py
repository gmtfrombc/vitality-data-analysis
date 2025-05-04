"""SQLite helper for storing user feedback on assistant answers.

Part of *WS-6 Continuous Feedback & Evaluation* work stream.

The table allows clinicians (or testers) to give a quick thumbs-up / thumbs-down
rating after each answer along with an optional free-text comment.  Captured
feedback will be triaged weekly and turned into regression tests or feature
requests.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Reuse DB location from existing utils
from app.utils.saved_questions_db import (
    DB_FILE,
)  # noqa: F401 – only DB_FILE used

__all__ = [
    "insert_feedback",
    "load_feedback",
]

FEEDBACK_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS assistant_feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT    DEFAULT 'anon',
    question    TEXT    NOT NULL,
    rating      TEXT    CHECK(rating IN ('up','down')) NOT NULL,
    comment     TEXT,
    created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
);
"""


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _get_conn(db_file: str | None = None) -> sqlite3.Connection:
    """Return connection and ensure *assistant_feedback* table exists."""
    db_path = db_file or DB_FILE
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute(FEEDBACK_TABLE_SQL)
    return conn


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def insert_feedback(
    question: str,
    rating: str,
    *,
    comment: str | None = None,
    user_id: str | None = None,
    db_file: str | None = None,
) -> bool:
    """Insert one feedback record.

    Parameters
    ----------
    question
        The NL question posed by the user.
    rating
        Either ``"up"`` or ``"down"``.
    comment
        Optional free-text elaboration.
    user_id
        Optional user identifier (default ``'anon'``).
    db_file
        Override database path (used in tests).
    """
    if rating not in {"up", "down"}:
        raise ValueError("rating must be 'up' or 'down'")

    uid = user_id or "anon"
    try:
        with _get_conn(db_file) as conn:
            conn.execute(
                "INSERT INTO assistant_feedback (user_id, question, rating, comment) VALUES (?, ?, ?, ?)",
                (uid, question, rating, comment),
            )
        return True
    except Exception:
        return False


def load_feedback(*, db_file: str | None = None, limit: int = 100) -> list[dict]:
    """Return latest feedback rows as list of dicts (max *limit*)."""
    with _get_conn(db_file) as conn:
        # Enable row_factory for proper dict access
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT user_id, question, rating, comment, created_at FROM assistant_feedback ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
