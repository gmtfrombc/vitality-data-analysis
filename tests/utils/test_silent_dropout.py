"""Unit tests for the silent dropout detection utility."""

import pandas as pd
from unittest.mock import patch, MagicMock
import pytest
from datetime import datetime, timedelta

from app.utils.silent_dropout import (
    get_silent_dropout_report,
    update_last_visit_date_for_patients,
    mark_patient_as_inactive,
)


@pytest.fixture
def mock_query_dataframe():
    """Mock for the query_dataframe function."""
    with patch("app.utils.silent_dropout.query_dataframe") as mock:
        # Setup default mock return values
        mock.return_value = pd.DataFrame(
            {
                "patient_id": ["P001", "P002"],
                "first_name": ["John", "Jane"],
                "last_name": ["Doe", "Smith"],
                "provider_visits": [2, 5],
                "last_visit_date": ["2025-01-15", "2025-03-01"],
                "days_since_visit": [120, 75],
            }
        )
        yield mock


@pytest.fixture
def mock_sqlite3_connect():
    """Mock for sqlite3.connect."""
    with patch("sqlite3.connect") as mock:
        # Set up mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Configure cursor to return rowcount=5 by default
        mock_cursor.rowcount = 5

        # Connect mock cursor to mock connection
        mock_conn.cursor.return_value = mock_cursor

        # Configure the connect mock to return our mock connection
        mock.return_value = mock_conn

        yield mock, mock_conn, mock_cursor


def test_get_silent_dropout_report(mock_query_dataframe):
    """Test the silent dropout report generation."""
    # Call function with default parameters
    result = get_silent_dropout_report()

    # Check function was called correctly
    mock_query_dataframe.assert_called_once()

    # Verify SQL format using flexible checks
    call_args = mock_query_dataframe.call_args[0]
    sql = call_args[0]
    assert "patient_id" in sql
    assert "LEFT JOIN patient_visit_metrics" in sql

    # Check active filter is in the SQL when active_only=True
    assert "active = 1" in sql

    # Verify threshold date is passed correctly
    expected_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert mock_query_dataframe.call_args[1]["params"] == (expected_date,)

    # Verify output format
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 6)
    assert "days_since_visit" in result.columns
    assert result["days_since_visit"].tolist() == [120, 75]


def test_get_silent_dropout_report_custom_threshold(mock_query_dataframe):
    """Test report generation with custom threshold."""
    # Call with custom threshold
    result = get_silent_dropout_report(threshold_days=60, active_only=False)

    # Verify SQL format
    call_args = mock_query_dataframe.call_args[0]
    sql = call_args[0]

    # Verify no active filter in SQL when active_only=False
    assert "patient_id" in sql
    assert "active = 1" not in sql

    # Verify threshold date is passed correctly
    expected_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    assert mock_query_dataframe.call_args[1]["params"] == (expected_date,)


def test_update_last_visit_date_for_patients(mock_sqlite3_connect):
    """Test updating last visit dates."""
    _, _, mock_cursor = mock_sqlite3_connect

    # Set up rowcount for this test
    mock_cursor.rowcount = 5

    # Patch the _check_column_exists function to return True
    with patch("app.utils.silent_dropout._check_column_exists", return_value=True):
        # Call the function
        result = update_last_visit_date_for_patients()

        # Verify cursor.execute was called with SQL containing the right components
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        sql = call_args[0]

        # Check SQL is correct
        assert "UPDATE patient_visit_metrics" in sql
        assert "last_visit_date" in sql
        assert "provider_visits > 0" in sql

        # Verify function returns the rowcount
        assert result == 5


def test_mark_patient_as_inactive(mock_sqlite3_connect):
    """Test marking a patient as inactive."""
    _, _, mock_cursor = mock_sqlite3_connect

    # Test success case
    mock_cursor.rowcount = 1
    result = mark_patient_as_inactive("P001")

    # Verify function was called correctly
    mock_cursor.execute.assert_called_once()

    # Check if patient_id is in the parameters
    call_args = mock_cursor.execute.call_args
    assert call_args[0][1] == ("P001",)

    # Verify result
    assert result is True

    # Test failure case
    mock_cursor.reset_mock()
    mock_cursor.rowcount = 0
    result = mark_patient_as_inactive("non_existent_id")
    assert result is False


def test_get_silent_dropout_report_empty_result(mock_query_dataframe):
    """Test handling of empty result sets."""
    # Set mock to return empty DataFrame
    mock_query_dataframe.return_value = pd.DataFrame()

    # Call function
    result = get_silent_dropout_report()

    # Verify result is empty DataFrame
    assert isinstance(result, pd.DataFrame)
    assert result.empty
