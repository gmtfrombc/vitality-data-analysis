"""Simple SQLite migration helper.

Keeps a `schema_migrations(version INTEGER PRIMARY KEY)` table and applies
any `migrations/NNN_description.sql` files in ascending order.
"""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path
import subprocess
import sys

logger = logging.getLogger(__name__)

# Repo root path (<workspace>/)
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"  # ../../migrations


def _ensure_schema_migrations_table(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _get_applied_migrations(conn: sqlite3.Connection) -> set[str]:
    _ensure_schema_migrations_table(conn)
    rows = conn.execute("SELECT filename FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def apply_pending_migrations(db_file: str) -> None:
    """Apply any .sql or .py migration files in migrations/ that haven't been applied yet."""
    conn = sqlite3.connect(db_file)
    try:
        applied = _get_applied_migrations(conn)
        migration_files = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.*"))
        for path in migration_files:
            fname = path.name
            if fname in applied:
                continue
            logger.info(f"Applying DB migration {fname}")
            if path.suffix == ".sql":
                sql = path.read_text()
                conn.executescript(sql)
                conn.commit()
            elif path.suffix == ".py":
                conn.commit()
                conn.close()
                result = subprocess.run(
                    [sys.executable, str(path), db_file], capture_output=True, text=True
                )
                logger.info(result.stdout)
                if result.returncode != 0:
                    logger.error(f"Migration {fname} failed: {result.stderr}")
                    raise RuntimeError(f"Migration {fname} failed")
                conn = sqlite3.connect(db_file)  # Reopen connection
            else:
                logger.warning(f"Skipping unknown migration type: {fname}")
                continue
            conn.execute("INSERT INTO schema_migrations(filename) VALUES (?)", (fname,))
            conn.commit()
    finally:
        conn.close()
