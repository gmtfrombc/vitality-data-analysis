"""Test date range filtering functionality."""

import pytest
from datetime import datetime
from app.utils.query_intent import QueryIntent, DateRange, Filter
from app.utils.ai.code_generator import generate_code


def test_date_range_validation():
    """Test that DateRange validates start/end dates properly."""
    # Valid date range
    date_range = DateRange(start_date="2025-01-01", end_date="2025-01-31")
    assert isinstance(date_range.start_date, datetime)
    assert isinstance(date_range.end_date, datetime)

    # String date formats
    date_range = DateRange(start_date="January 1, 2025", end_date="January 31, 2025")
    assert date_range.start_date.month == 1
    assert date_range.start_date.day == 1
    assert date_range.end_date.month == 1
    assert date_range.end_date.day == 31

    # Invalid date order
    with pytest.raises(ValueError):
        DateRange(start_date="2025-02-01", end_date="2025-01-01")


def test_query_intent_with_time_range():
    """Test QueryIntent with global time range."""
    intent = QueryIntent(
        analysis_type="trend",
        target_field="weight",
        time_range=DateRange(start_date="2025-01-01", end_date="2025-03-31"),
    )

    assert intent.has_date_filter() is True
    assert intent.get_date_range() is not None
    assert intent.get_date_range().start_date.month == 1
    assert intent.get_date_range().end_date.month == 3


def test_filter_with_date_range():
    """Test Filter with date_range field."""
    filter_with_date = Filter(
        field="date",
        date_range=DateRange(start_date="2025-01-01", end_date="2025-03-31"),
    )

    # Test validation - can't have both value and date_range
    with pytest.raises(ValueError):
        Filter(
            field="date",
            value="2025-01-01",
            date_range=DateRange(start_date="2025-01-01", end_date="2025-03-31"),
        )


def test_get_date_range_priority():
    """Test that global time_range takes precedence over filter date ranges."""
    # Create intent with both global time_range and a date filter
    filter_with_date = Filter(
        field="date",
        date_range=DateRange(start_date="2025-04-01", end_date="2025-06-30"),
    )

    intent = QueryIntent(
        analysis_type="trend",
        target_field="weight",
        filters=[filter_with_date],
        time_range=DateRange(start_date="2025-01-01", end_date="2025-03-31"),
    )

    # Global time_range should take precedence
    date_range = intent.get_date_range()
    assert date_range is not None
    assert date_range.start_date.month == 1  # From global time_range
    assert date_range.end_date.month == 3  # From global time_range


def test_code_generation_with_date_range():
    """Test that date ranges are properly included in generated SQL queries."""
    # Setup intent with date range
    intent = QueryIntent(
        analysis_type="average",
        target_field="weight",
        time_range=DateRange(start_date="2025-01-01", end_date="2025-03-31"),
    )

    # Generate code
    code = generate_code(intent)

    # Verify the date range appears in the SQL query
    assert code is not None
    assert "date BETWEEN '2025-01-01' AND '2025-03-31'" in code

    # Test with trend analysis
    intent = QueryIntent(
        analysis_type="trend",
        target_field="bmi",
        time_range=DateRange(start_date="2025-01-01", end_date="2025-03-31"),
    )

    code = generate_code(intent)
    assert code is not None
    assert "date BETWEEN '2025-01-01' AND '2025-03-31'" in code


def test_filter_date_range_in_code_generation():
    """Test date ranges in filters are included in generated SQL."""
    # Create intent with date filter
    filter_with_date = Filter(
        field="date",
        date_range=DateRange(start_date="2025-01-01", end_date="2025-03-31"),
    )

    intent = QueryIntent(
        analysis_type="distribution", target_field="weight", filters=[filter_with_date]
    )

    # Generate code
    code = generate_code(intent)

    # Verify the date range appears in the SQL query
    assert code is not None
    assert "date BETWEEN '2025-01-01' AND '2025-03-31'" in code
