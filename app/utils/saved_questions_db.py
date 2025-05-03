"""SQLite helper functions to persist *saved questions*.

Motivation
----------
`DataAnalysisAssistant` currently stores saved questions in a JSON file.  That
works in single-user desktop mode but breaks down once multiple users or
process instances need to share state.  We migrate the storage to SQLite so
that questions survive container restarts and remain consistent across users.

All functions are *thin* wrappers around the standard `sqlite3` library so we
avoid adding a heavyweight ORM dependency.
"""

from __future__ import annotations

import os
import sqlite3
import logging
from typing import List, Dict
import json
import shutil

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_FILE = os.getenv(
    "VP_DATA_DB",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "patient_data.db"),
)

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS saved_questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    query       TEXT    NOT NULL,
    created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
);
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_conn(db_file: str | None = None) -> sqlite3.Connection:
    """Return a SQLite connection and ensure the *saved_questions* table exists."""
    db_path = db_file or DB_FILE
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # easier dict conversion
    with conn:
        conn.execute(TABLE_SQL)
    return conn


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_saved_questions(db_file: str | None = None) -> List[Dict[str, str]]:
    """Fetch all saved questions as ``[{"name": ..., "query": ...}, ...]``.

    Returns an **empty list** when no questions exist.
    """
    try:
        with _get_conn(db_file) as conn:
            rows = conn.execute(
                "SELECT name, query FROM saved_questions ORDER BY id"
            ).fetchall()
            return [{"name": r["name"], "query": r["query"]} for r in rows]
    except Exception as exc:
        logger.error(
            "Failed to load saved questions from SQLite: %s", exc, exc_info=True
        )
        return []


def save_all_questions(
    questions: List[Dict[str, str]], *, db_file: str | None = None
) -> bool:
    """Replace table contents with *questions*.

    Parameters
    ----------
    questions
        List with schema ``{"name": str, "query": str}``.
    db_file
        Alternative database file (used by tests).
    """
    try:
        with _get_conn(db_file) as conn:
            with conn:
                conn.execute("DELETE FROM saved_questions")
                conn.executemany(
                    "INSERT INTO saved_questions (name, query) VALUES (?, ?)",
                    [(q["name"], q["query"]) for q in questions],
                )
        logger.info("Saved %d questions to SQLite", len(questions))
        return True
    except sqlite3.IntegrityError as exc:
        logger.error("Duplicate question name detected: %s", exc)
        return False
    except Exception as exc:
        logger.error("Failed to persist questions to SQLite: %s", exc, exc_info=True)
        return False


def upsert_question(name: str, query: str, *, db_file: str | None = None) -> None:
    """Insert *or* update a single question identified by *name*."""
    with _get_conn(db_file) as conn:
        with conn:
            conn.execute(
                "INSERT INTO saved_questions (name, query) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET query = excluded.query",
                (name, query),
            )


def delete_question(name: str, *, db_file: str | None = None) -> None:
    """Delete question with *name* if it exists."""
    with _get_conn(db_file) as conn:
        with conn:
            conn.execute("DELETE FROM saved_questions WHERE name = ?", (name,))


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------


def migrate_from_json(
    json_file: str, *, db_file: str | None = None, backup: bool = True
) -> bool:
    """One-off migration: import questions from *json_file* into SQLite.

    The function short-circuits when:
    • the JSON file does not exist or is empty
    • the DB table already has rows (assumed migrated)
    Returns True on successful migration, False otherwise.
    """

    if not os.path.exists(json_file):
        logger.info("No legacy JSON file at %s; nothing to migrate", json_file)
        return False

    # Abort if table already populated
    existing = load_saved_questions(db_file=db_file)
    if existing:
        logger.info(
            "SQLite already contains %d questions; skipping migration", len(existing)
        )
        return False

    try:
        with open(json_file, "r") as f:
            data = json.load(f)
        if not data:
            logger.warning("Legacy JSON %s empty; skipping migration", json_file)
            return False

        ok = save_all_questions(data, db_file=db_file)
        if not ok:
            logger.error("Failed to bulk insert questions during migration")
            return False

        # Backup or remove JSON
        if backup:
            bak_path = json_file + ".bak"
            shutil.move(json_file, bak_path)
            logger.info("Legacy JSON migrated and backed up to %s", bak_path)
        else:
            os.remove(json_file)
            logger.info("Legacy JSON migrated and removed")
        return True
    except Exception as exc:
        logger.error("Migration from JSON failed: %s", exc, exc_info=True)
        return False
