"""Tests for app.utils.db_migrations.apply_pending_migrations."""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from app.utils.db_migrations import apply_pending_migrations


@pytest.fixture()
def tmp_db():
    # Create fresh DB with only baseline patients table (pre-migration)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.executescript(
        """
        CREATE TABLE patients (
            id TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT
        );
        CREATE TABLE pmh (
            pmh_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            condition TEXT
        );
        """
    )
    conn.close()
    apply_pending_migrations(tmp.name)
    yield tmp.name
    try:
        os.remove(tmp.name)
    except FileNotFoundError:
        pass


def test_apply_pending_migrations_adds_columns(tmp_db):
    conn = sqlite3.connect(tmp_db)
    try:
        cols_patients = {r[1] for r in conn.execute("PRAGMA table_info(patients)")}
        assert {
            "provider_id",
            "health_coach_id",
            "lesson_status",
            "lessons_completed",
            "provider_visits",
            "health_coach_visits",
            "cancelled_visits",
            "no_show_visits",
            "rescheduled_visits",
            "roles",
        }.issubset(cols_patients)

        cols_pmh = {r[1] for r in conn.execute("PRAGMA table_info(pmh)")}
        assert "code" in cols_pmh

        # Ensure version recorded
        versions = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        assert 2 in versions
    finally:
        conn.close()
