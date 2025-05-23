import sqlite3
from typing import Dict, List

import pandas as pd
import pytest

from app.utils.validation_engine import ValidationEngine
from app.utils.rule_loader import initialize_validation_rules
from app.utils.db_migrations import apply_pending_migrations


@pytest.fixture(scope="module")
def mock_validation_db(tmp_path_factory):
    """Create a tiny SQLite DB with controlled data for validation-rule tests."""
    db_path = tmp_path_factory.mktemp("mock_db") / "validation_test.db"

    conn = sqlite3.connect(db_path)
    apply_pending_migrations(str(db_path))
    cursor = conn.cursor()

    # Add provider and health_coach columns to patients table for test
    cursor.execute(
        """
        ALTER TABLE patients ADD COLUMN provider TEXT;
    """
    )
    cursor.execute(
        """
        ALTER TABLE patients ADD COLUMN health_coach TEXT;
    """
    )

    # --------------------------------------------------
    # Seed patient rows
    # --------------------------------------------------
    patients: List[Dict] = [
        # Patient 1 – all good
        {
            "id": 1,
            "first_name": "Clean",
            "last_name": "Patient",
            "program_start_date": "2025-01-01",
            "program_end_date": "2025-04-01",
            "active": 1,
            "provider_visits": 3,
            "health_coach_visits": 2,
            "provider": "Dr. Good",
            "health_coach": "Coach Well",
        },
        # Patient 2 – missing program_start_date (triggers not_null_check)
        {
            "id": 2,
            "first_name": "Missing",
            "last_name": "StartDate",
            "program_start_date": None,
            "program_end_date": "2025-04-01",
            "active": 1,
            "provider_visits": 3,
            "health_coach_visits": 2,
            "provider": None,
            "health_coach": None,
        },
        # Patient 3 – extreme BMI (triggers BMI_RANGE_CHECK)
        {
            "id": 3,
            "first_name": "High",
            "last_name": "BMI",
            "program_start_date": "2025-01-01",
            "program_end_date": None,
            "active": 0,
            "provider_visits": 3,
            "health_coach_visits": 2,
            "provider": None,
            "health_coach": None,
        },
        # Patient 4 – extreme weight (triggers WEIGHT_RANGE_CHECK)
        {
            "id": 4,
            "first_name": "Heavy",
            "last_name": "Weight",
            "program_start_date": "2025-01-01",
            "program_end_date": None,
            "active": 1,
            "provider_visits": 7,
            "health_coach_visits": 2,
            "provider": None,
            "health_coach": None,
        },
    ]

    cursor.executemany(
        """
        INSERT INTO patients (id, first_name, last_name, program_start_date, program_end_date, active, provider_visits, health_coach_visits, provider, health_coach)
        VALUES (:id, :first_name, :last_name, :program_start_date, :program_end_date, :active, :provider_visits, :health_coach_visits, :provider, :health_coach)
        """,
        patients,
    )

    # --------------------------------------------------
    # Minimal vitals rows (only needed for BMI/weight checks)
    # --------------------------------------------------
    vitals_rows = [
        (1, "2025-04-15", 160.0, 24.0, 120, 80),
        (2, "2025-04-15", 170.0, 25.0, 118, 78),
        (3, "2025-04-15", 400.0, 85.0, 130, 88),
        (4, "2025-04-15", 600.0, 35.0, 140, 90),
    ]
    cursor.executemany(
        """
        INSERT INTO vitals (patient_id, date, weight, bmi, sbp, dbp)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        vitals_rows,
    )

    conn.commit()
    conn.close()

    # Seed full rule catalogue (YAML) into our mock DB
    initialize_validation_rules(str(db_path))

    return str(db_path)


def _count_results(conn):
    """Utility: return mapping of rule_id → count in validation_results."""
    df = pd.read_sql_query(
        "SELECT rule_id, COUNT(*) as cnt FROM validation_results GROUP BY rule_id", conn
    )
    return {row["rule_id"]: int(row["cnt"]) for _, row in df.iterrows()}


@pytest.mark.validation
def test_validation_engine_detects_known_issues(mock_validation_db):
    """Engine should flag the intentional data problems and ignore the clean patient."""
    engine = ValidationEngine(mock_validation_db)

    # Run validation for *all* patients
    engine.validate_all_patients()

    conn = sqlite3.connect(mock_validation_db)

    results_by_rule = _count_results(conn)

    # Clean patient (id=1) should not have any issues
    df_clean = pd.read_sql_query(
        "SELECT * FROM validation_results WHERE patient_id = 1", conn
    )
    assert df_clean.empty, "Clean patient unexpectedly has validation issues"

    # Patient 2 – program start date missing
    assert results_by_rule.get("PROGRAM_START_DATE_FREQUENCY_CHECK", 0) >= 1

    # Patient 3 – BMI out of range
    assert results_by_rule.get("BMI_RANGE_CHECK", 0) >= 1

    # Patient 4 – weight out of range
    assert results_by_rule.get("WEIGHT_RANGE_CHECK", 0) >= 1

    # Program end date missing for patients 3 and 4
    assert results_by_rule.get("PROGRAM_END_DATE_FREQUENCY_CHECK", 0) >= 2

    conn.close()
