from __future__ import annotations

"""Utility to cache database schema for quick validation.

This helper loads the column names for every table in the active
SQLite database using ``PRAGMA table_info``.  The result is cached
in-memory for the duration of the Python process to avoid repeated
introspection queries.

It is intentionally lightweight (single SELECT per table) so importing
this module at startup has negligible overhead.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Set

from app.utils.saved_questions_db import DB_FILE  # Re-use central DB path helper

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal cache ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

_SCHEMA_CACHE: Dict[str, Set[str]] | None = None


# ---------------------------------------------------------------------------
# Public helpers ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


def load_schema(
    db_file: str | None = None, *, force_refresh: bool = False
) -> Dict[str, Set[str]]:  # noqa: D401
    """Return mapping ``{table_name: {col1, col2, …}}`` for *db_file*.

    Parameters
    ----------
    db_file : str | None
        Path to the SQLite database.  Uses the project-wide ``DB_FILE`` default
        when *None*.
    force_refresh : bool, default False
        When ``True`` the cache is ignored and a fresh introspection run is
        executed.
    """
    global _SCHEMA_CACHE  # noqa: PLW0603 – explicit cache mutation

    if _SCHEMA_CACHE is not None and not force_refresh:
        return _SCHEMA_CACHE

    db_path = db_file or DB_FILE
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Discover tables – ignore SQLite internal ones
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()

        schema: Dict[str, Set[str]] = {}
        for row in tables:
            tbl_name: str = row["name"]
            cols = conn.execute(f"PRAGMA table_info({tbl_name});").fetchall()
            schema[tbl_name] = {col["name"] for col in cols}

        _SCHEMA_CACHE = schema  # cache for future calls
        logger.info("Schema cache loaded – %s tables", len(schema))
        return schema
    finally:
        try:
            conn.close()
        except Exception:  # pragma: no cover
            pass


def list_tables(db_file: str | None = None) -> List[str]:  # noqa: D401
    """Return list of user tables in the active database."""
    return list(load_schema(db_file).keys())


def get_columns(table: str, *, db_file: str | None = None) -> Set[str]:  # noqa: D401
    """Return set of column names for *table* (empty set if not found)."""
    return load_schema(db_file).get(table, set())


def is_valid_column(
    table: str, column: str, *, db_file: str | None = None
) -> bool:  # noqa: D401
    """Return ``True`` if *column* exists in *table* according to cached schema."""
    return column in load_schema(db_file).get(table, set())
