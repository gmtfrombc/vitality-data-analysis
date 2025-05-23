"""Test that setting the MH_DB_PATH environment variable overrides the default DB path."""

from __future__ import annotations

import importlib


import pytest


@pytest.mark.parametrize("table_name", ["patients", "vitals"])
def test_db_path_env_override(tmp_path, monkeypatch, table_name):
    """Ensure :pyfunc:`db_query.query_dataframe` uses the path from ``MH_DB_PATH``."""

    # ------------------------------------------------------------------
    # 1. Build a minimal SQLite file with a single table
    # ------------------------------------------------------------------
    mock_db = tmp_path / "mock.db"
    # Do not create the table manually; just create the file and run migrations
    from app.utils.db_migrations import apply_pending_migrations

    apply_pending_migrations(str(mock_db))

    # ------------------------------------------------------------------
    # 2. Point code at our mock DB – must happen *before* we import db_query
    # ------------------------------------------------------------------
    monkeypatch.setenv("MH_DB_PATH", str(mock_db))

    # Force fresh import to pick up env var
    if "db_query" in importlib.sys.modules:
        importlib.reload(importlib.import_module("db_query"))
    else:
        import app.db_query as db_query  # noqa: F401 – imported for side-effect

    import app.db_query as db_query  # pylint: disable=reimported

    # ------------------------------------------------------------------
    # 3. Run a trivial query via helper – should succeed against mock DB
    # ------------------------------------------------------------------
    df = db_query.query_dataframe("SELECT name FROM sqlite_master WHERE type='table';")

    assert not df.empty, "Expected at least one table in schema query"
    assert table_name in df["name"].tolist(), "Schema query did not hit mock DB"

    # Confirm helper resolves path correctly
    assert db_query.get_db_path() == str(mock_db)
