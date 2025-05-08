import os
import sqlite3
import tempfile
from typing import Dict, List

import pandas as pd
import pytest

from app.utils.validation_engine import ValidationEngine
from app.utils.rule_loader import initialize_validation_rules


@pytest.fixture(scope="module")
def mock_validation_db(tmp_path_factory):
    """Create a tiny SQLite DB with controlled data for validation-rule tests."""
    db_path = tmp_path_factory.mktemp("mock_db") / "validation_test.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # --------------------------------------------------
    # Minimal schema (subset of production)
    # --------------------------------------------------
    cursor.executescript(
        """
        CREATE TABLE patients (
            id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            program_start_date TEXT,
            program_end_date TEXT,
            active INTEGER,
            provider_visit_count INTEGER,
            bmi REAL,
            weight REAL,
            provider TEXT,
            health_coach TEXT
        );

        CREATE TABLE vitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            date TEXT,
            weight REAL,
            bmi REAL,
            systolic_pressure REAL,
            diastolic_pressure REAL
        );

        /* Validation-system tables */
        CREATE TABLE validation_rules (
            rule_id TEXT PRIMARY KEY,
            description TEXT,
            rule_type TEXT,
            validation_logic TEXT,
            parameters TEXT,
            severity TEXT,
            is_active INTEGER DEFAULT 1,
            updated_at TEXT
        );

        CREATE TABLE validation_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT,
            patient_id TEXT,
            field_name TEXT,
            issue_description TEXT,
            status TEXT,
            detected_at TEXT
        );
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
            "provider_visit_count": 3,
            "bmi": 24.0,
            "weight": 160.0,
            "provider": "Dr. Clean",
            "health_coach": "Coach Clean"
        },
        # Patient 2 – missing program_start_date (triggers not_null_check)
        {
            "id": 2,
            "first_name": "Missing",
            "last_name": "StartDate",
            "program_start_date": None,
            "program_end_date": "2025-04-01",
            "active": 1,
            "provider_visit_count": 3,
            "bmi": 25.0,
            "weight": 170.0,
            "provider": "Dr. Missing",
            "health_coach": "Coach Missing"
        },
        # Patient 3 – extreme BMI (triggers BMI_RANGE_CHECK)
        {
            "id": 3,
            "first_name": "High",
            "last_name": "BMI",
            "program_start_date": "2025-01-01",
            "program_end_date": None,
            "active": 0,
            "provider_visit_count": 3,
            "bmi": 85.0,  # way above 70
            "weight": 400.0,
            "provider": "Dr. High",
            "health_coach": "Coach High"
        },
        # Patient 4 – extreme weight (triggers WEIGHT_RANGE_CHECK)
        {
            "id": 4,
            "first_name": "Heavy",
            "last_name": "Weight",
            "program_start_date": "2025-01-01",
            "program_end_date": None,
            "active": 1,
            "provider_visit_count": 7,
            "bmi": 35.0,
            "weight": 600.0,  # above 500
            "provider": "Dr. Heavy",
            "health_coach": "Coach Heavy"
        },
    ]

    cursor.executemany(
        """
        INSERT INTO patients (id, first_name, last_name, program_start_date, program_end_date, active, provider_visit_count, bmi, weight, provider, health_coach)
        VALUES (:id, :first_name, :last_name, :program_start_date, :program_end_date, :active, :provider_visit_count, :bmi, :weight, :provider, :health_coach)
        """,
        patients,
    )

    # --------------------------------------------------
    # Minimal vitals rows (only needed for BMI/weight checks)
    # --------------------------------------------------
    vitals_rows = [
        (1, 1, "2025-04-15", 160.0, 24.0, 120, 80),
        (2, 2, "2025-04-15", 170.0, 25.0, 118, 78),
        (3, 3, "2025-04-15", 400.0, 85.0, 130, 88),
        (4, 4, "2025-04-15", 600.0, 35.0, 140, 90),
    ]
    cursor.executemany(
        """
        INSERT INTO vitals (id, patient_id, date, weight, bmi, systolic_pressure, diastolic_pressure)
        VALUES (?, ?, ?, ?, ?, ?, ?)
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
        "SELECT rule_id, COUNT(*) as cnt FROM validation_results GROUP BY rule_id", conn)
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
        "SELECT * FROM validation_results WHERE patient_id = 1", conn)
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
