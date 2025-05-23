# WARNING: This test previously modified the production database (patient_data.db)!
# It is unsafe and should not be run as-is. Refactored below to use a temp DB only.

import sqlite3
import tempfile
import os
import pytest
from app.utils.db_migrations import apply_pending_migrations
from app.db_query import query_dataframe as qdf


def setup_temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    apply_pending_migrations(path)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    # Insert minimal patient and vitals data for test
    cursor.execute(
        """
        INSERT INTO patients (id, first_name, last_name, active) VALUES ('p1', 'Test', 'User', 1)
    """
    )
    cursor.execute(
        """
        INSERT INTO vitals (patient_id, date, weight, bmi) VALUES ('p1', '2025-01-01', 80, 32.5)
    """
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture(scope="module")
def temp_db_path():
    path = setup_temp_db()
    yield path
    os.unlink(path)


def test_active_column_values(temp_db_path, monkeypatch):
    # Patch MH_DB_PATH so qdf uses our temp DB
    monkeypatch.setenv("MH_DB_PATH", temp_db_path)
    # Now run the same queries as before
    print("\n1. Distinct values in patients.active column:")
    print(qdf("SELECT DISTINCT active FROM patients"))
    print("\n2. Patient count with BMI > 30 (no active filter):")
    print(
        qdf(
            """
        SELECT COUNT(DISTINCT patients.id) AS patient_count
        FROM patients
        INNER JOIN vitals ON patients.id = vitals.patient_id
        WHERE vitals.bmi > 30
    """
        )
    )
