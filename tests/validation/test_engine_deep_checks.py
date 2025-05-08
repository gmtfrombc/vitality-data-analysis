import sqlite3
import pandas as pd
import pytest

from app.utils.validation_engine import ValidationEngine
from app.utils.rule_loader import initialize_validation_rules

# Re-use the DB fixture from the other module so we don't duplicate setup
from tests.validation.test_engine_rules import mock_validation_db  # noqa: F401


@pytest.mark.validation
@pytest.mark.parametrize(
    "patient_id,expected_rule",
    [
        (1, None),  # clean – expect no issues
        (2, "PROGRAM_START_DATE_FREQUENCY_CHECK"),
        (3, "BMI_RANGE_CHECK"),
        (4, "WEIGHT_RANGE_CHECK"),
    ],
)
def test_engine_flags_expected_rules(patient_id, expected_rule):
    """Engine should raise / not raise the specified rules per patient."""
    engine = ValidationEngine(mock_validation_db)
    engine.validate_patient(str(patient_id))

    conn = sqlite3.connect(mock_validation_db)
    df = pd.read_sql_query(
        "SELECT rule_id FROM validation_results WHERE patient_id = ?",
        conn,
        params=(str(patient_id),),
    )

    rule_ids = set(df["rule_id"].tolist())
    conn.close()

    if expected_rule is None:
        assert not rule_ids, f"Patient {patient_id} unexpectedly has issues: {rule_ids}"
    else:
        assert expected_rule in rule_ids, (
            f"Patient {patient_id} missing expected rule {expected_rule}; got {rule_ids}"
        )


@pytest.mark.validation
def test_allowed_values_check_detects_invalid_value():
    """Insert a patient with active = 2 to trigger ACTIVE_CATEGORICAL_CHECK."""
    # Prepare DB – add bad patient row
    conn = sqlite3.connect(mock_validation_db)

    # make sure rules already seeded
    initialize_validation_rules(mock_validation_db)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patients (id, first_name, last_name, program_start_date, active, provider_visit_count, bmi, weight, provider, health_coach)
        VALUES (5, 'Bad', 'Active', '2025-01-01', 2, 0, 24.0, 155.0, 'Dr. Bad', 'Coach Bad')
        """
    )
    conn.commit()
    conn.close()

    engine = ValidationEngine(mock_validation_db)
    engine.validate_patient("5")

    conn = sqlite3.connect(mock_validation_db)
    df = pd.read_sql_query(
        "SELECT rule_id FROM validation_results WHERE patient_id = 5",
        conn,
    )
    conn.close()

    assert "ACTIVE_CATEGORICAL_CHECK" in set(df["rule_id"].tolist())
