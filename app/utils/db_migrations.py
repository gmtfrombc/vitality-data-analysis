"""Simple SQLite migration helper.

Keeps a `schema_migrations(version INTEGER PRIMARY KEY)` table and applies
any `migrations/NNN_description.sql` files in ascending order.
"""

from __future__ import annotations

import sqlite3
import glob
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Repo root path (<workspace>/)
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"  # ../../migrations


def _get_applied_versions(conn: sqlite3.Connection) -> set[int]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
    )
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def apply_pending_migrations(db_file: str) -> None:
    """Apply any .sql files whose numeric prefix is > latest applied."""
    conn = sqlite3.connect(db_file)
    try:
        with conn:
            applied = _get_applied_versions(conn)
            migration_files = sorted(glob.glob(str(MIGRATIONS_DIR / "*.sql")))
            for path in migration_files:
                # Only process files whose prefix can be parsed as an int
                prefix = Path(path).name.split("_", 1)[0]
                try:
                    version = int(prefix)
                except ValueError:
                    logger.debug("Skipping non-versioned migration file: %s", path)
                    continue

                if version in applied:
                    continue
                logger.info("Applying DB migration %s", path)
                sql = Path(path).read_text()
                conn.executescript(sql)
                conn.execute(
                    "INSERT INTO schema_migrations(version) VALUES (?)", (version,)
                )
    finally:
        conn.close()
