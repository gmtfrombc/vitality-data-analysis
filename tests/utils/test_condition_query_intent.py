"""Tests for condition mapping integration with query intent."""

from unittest.mock import patch

from app.utils.query_intent import (
    get_condition_filter_sql,
    get_canonical_condition,
    _normalise_field_name,
    PMH_TABLE,
)


def test_condition_field_normalization():
    """Test that condition-related fields are normalized correctly."""
    # Test direct match
    assert _normalise_field_name("condition") == "condition"

    # Test synonyms
    assert _normalise_field_name("diagnosis") == "condition"
    assert _normalise_field_name("medical condition") == "condition"
    assert _normalise_field_name("health condition") == "condition"
    assert _normalise_field_name("problem") == "condition"
    assert _normalise_field_name("medical problem") == "condition"
    assert _normalise_field_name("pmh") == "condition"
    assert _normalise_field_name("diagnoses") == "condition"
    assert _normalise_field_name("conditions") == "condition"

    # Test case insensitivity
    assert _normalise_field_name("DIAGNOSIS") == "condition"
    assert _normalise_field_name("Medical Condition") == "condition"


@patch("app.utils.condition_mapper.condition_mapper.get_canonical_condition")
def test_get_canonical_condition(mock_mapper_get_canonical):
    """Test that get_canonical_condition delegates to the condition mapper."""
    # Setup the mock
    mock_mapper_get_canonical.return_value = "type_2_diabetes"

    # Test the function
    assert get_canonical_condition("t2dm") == "type_2_diabetes"
    mock_mapper_get_canonical.assert_called_once_with("t2dm")


@patch("app.utils.condition_mapper.condition_mapper.get_all_codes_as_sql_list")
def test_get_condition_filter_sql_success(mock_get_codes):
    """Test generating SQL filter for a condition with mapped codes."""
    # Setup the mock
    mock_get_codes.return_value = "'E11.9', 'E11.8'"

    # Test the function
    sql, success = get_condition_filter_sql("type 2 diabetes")

    # Verify results
    assert success is True
    assert sql == f"{PMH_TABLE}.code IN ('E11.9', 'E11.8')"
    mock_get_codes.assert_called_once_with("type 2 diabetes")


@patch("app.utils.condition_mapper.condition_mapper.get_all_codes_as_sql_list")
def test_get_condition_filter_sql_failure(mock_get_codes):
    """Test handling when no codes are found for a condition."""
    # Setup the mock to return empty list
    mock_get_codes.return_value = ""

    # Test the function
    sql, success = get_condition_filter_sql("unknown condition")

    # Verify results
    assert success is False
    assert sql == ""
    mock_get_codes.assert_called_once_with("unknown condition")
