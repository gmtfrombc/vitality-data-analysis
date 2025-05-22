"""Unit tests for app.utils.saved_questions_db helper (WS-3-A).

These tests use a temporary on-disk SQLite file to avoid the `:memory:` per-connection
trap where each helper call would receive a fresh database.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from app.utils import saved_questions_db as sqdb
from app.utils.db_migrations import apply_pending_migrations


def _tmp_db_file() -> str:
    """Return a path to a fresh temporary SQLite file."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    return tmp.name


@pytest.fixture()
def db_path():
    path = _tmp_db_file()
    apply_pending_migrations(path)
    yield path
    # Teardown – remove file if it still exists
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def test_upsert_and_load(db_path):
    # Upsert two questions
    sqdb.upsert_question("Q1", "How many patients?", db_file=db_path)
    sqdb.upsert_question("Q2", "Average BMI", db_file=db_path)

    # Load them back
    loaded = sqdb.load_saved_questions(db_file=db_path)
    names = sorted(q["name"] for q in loaded)
    assert names == ["Q1", "Q2"]

    # Upsert same name with new query (update path)
    sqdb.upsert_question("Q1", "How many *active* patients?", db_file=db_path)
    updated = {
        q["name"]: q["query"] for q in sqdb.load_saved_questions(db_file=db_path)
    }
    assert updated["Q1"] == "How many *active* patients?"


def test_delete_question(db_path):
    sqdb.upsert_question("Q_del", "Foo", db_file=db_path)
    assert sqdb.load_saved_questions(db_file=db_path)  # not empty

    # delete and verify removal
    sqdb.delete_question("Q_del", db_file=db_path)
    remaining = sqdb.load_saved_questions(db_file=db_path)
    assert all(q["name"] != "Q_del" for q in remaining)


def test_save_all_questions_duplicate_name_returns_false(db_path):
    questions = [
        {"name": "Dup", "query": "X"},
        # duplicate name triggers UNIQUE constraint
        {"name": "Dup", "query": "Y"},
    ]
    ok = sqdb.save_all_questions(questions, db_file=db_path)
    assert ok is False


def test_load_saved_questions_bad_path_returns_empty_list(tmp_path):
    # Point to a directory path that cannot be used as a file
    bad_path = tmp_path / "nonexistent" / "subdir" / "file.db"
    loaded = sqdb.load_saved_questions(db_file=str(bad_path))
    assert loaded == []
