"""Tests for etl.json_ingest.ingest."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from etl.json_ingest import ingest

# Minimal sample JSON with two patients and nested vitals
SAMPLE = [
    {
        "id": "p1",
        "first_name": "A",
        "last_name": "B",
        "vitals": [
            {"patient_id": "p1", "date": "2025-01-01", "weight": 80},
            {"patient_id": "p1", "date": "2025-01-15", "weight": 79},
        ],
    },
    {
        "id": "p2",
        "first_name": "C",
        "last_name": "D",
        "vitals": [{"patient_id": "p2", "date": "2025-02-01", "weight": 90}],
    },
]


@pytest.fixture()
def tmp_json_file(tmp_path: Path):
    f = tmp_path / "patients.json"
    f.write_text(json.dumps(SAMPLE))
    return f


@pytest.fixture()
def tmp_db_file(tmp_path: Path):
    return tmp_path / "test.db"


def _count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_ingest_idempotent(tmp_json_file: Path, tmp_db_file: Path):
    # first run
    ingest(tmp_json_file, tmp_db_file)
    conn = sqlite3.connect(tmp_db_file)
    try:
        assert _count(conn, "patients") == 2
        assert _count(conn, "vitals") == 3
    finally:
        conn.close()

    # second run should not duplicate
    ingest(tmp_json_file, tmp_db_file)
    conn = sqlite3.connect(tmp_db_file)
    try:
        assert _count(conn, "patients") == 2
        assert _count(conn, "vitals") == 3
    finally:
        conn.close()
