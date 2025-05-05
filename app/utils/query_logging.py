"""Helper functions to persist assistant query / response interactions.

This tiny wrapper avoids pulling in an ORM while still giving us a durable audit
trail that powers *Continuous Feedback & Evaluation* (WS-6).

Schema
------
`migrations/006_add_assistant_logs_table.sql` creates the table:

```
assistant_logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query           TEXT NOT NULL,
    intent_json     TEXT,
    generated_code  TEXT,
    result_summary  TEXT,
    duration_ms     INTEGER,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
)
```

The helpers below are intentionally lenient: if the migration has not yet run
(e.g., when tests use a fresh temporary DB) they will create the table on the
fly.  This keeps unit tests self-contained.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, List, Dict

# Re-use the same DB path as other helpers to keep everything in one file.
try:
    from app.utils.saved_questions_db import DB_FILE  # pragma: no cover
except Exception:  # Fallback when import path changes in tests
    DB_FILE = os.getenv(
        "VP_DATA_DB",
        os.path.join(os.path.dirname(__file__), "..", "..", "patient_data.db"),
    )

logger = logging.getLogger(__name__)

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS assistant_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query            TEXT    NOT NULL,
    intent_json      TEXT,
    generated_code   TEXT,
    result_summary   TEXT,
    duration_ms      INTEGER,
    created_at       TEXT    DEFAULT CURRENT_TIMESTAMP
);
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_conn(db_file: str | None = None) -> sqlite3.Connection:  # pragma: no cover
    """Return SQLite connection ensuring *assistant_logs* table exists."""
    path = db_file or DB_FILE
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(_CREATE_SQL)
    return conn


def _safe_json(obj: Any) -> str:
    """Best-effort JSON serialiser that never raises."""

    def _default(o):  # noqa: D401 – short lambda style
        try:
            return o.__dict__
        except Exception:
            return str(o)

    try:
        return json.dumps(obj, default=_default, ensure_ascii=False)
    except TypeError:
        # Fallback to string when not serialisable
        return json.dumps(str(obj))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def log_interaction(
    query: str,
    intent: Any = None,
    generated_code: str | None = None,
    result: Any = None,
    duration_ms: int | None = None,
    *,
    db_file: str | None = None,
) -> None:
    """Persist a single assistant interaction.

    Parameters
    ----------
    query
        Original user query.
    intent
        Parsed intent object or dict; stored as JSON.
    generated_code
        The Python code snippet emitted by the assistant.
    result
        Final *summary* to display to the user OR any serialisable short string.
    duration_ms
        Total processing time in milliseconds.
    db_file
        Override DB path (used by tests).
    """

    # Compress / trim large blobs so DB doesn't bloat
    code_trim = (generated_code or "")[:10_000]  # 10 KB guard

    # Take only a short textual summary of result to avoid storing full DataFrames
    if result is None:
        result_summary = None
    elif isinstance(result, (str, int, float)):
        result_summary = str(result)
    else:
        # Try first 1k of JSON serialised form
        result_summary = _safe_json(result)[:1_000]

    try:
        with _get_conn(db_file) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO assistant_logs (
                        query, intent_json, generated_code, result_summary, duration_ms
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        query,
                        _safe_json(intent),
                        code_trim,
                        result_summary,
                        duration_ms,
                    ),
                )
    except Exception as exc:  # pragma: no cover – best-effort logging
        logger.error("Failed to record assistant interaction: %s", exc, exc_info=True)


def fetch_recent(
    limit: int = 20, *, db_file: str | None = None
) -> List[Dict[str, Any]]:
    """Return the *latest* `limit` interactions."""
    with _get_conn(db_file) as conn:
        rows = conn.execute(
            "SELECT * FROM assistant_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
