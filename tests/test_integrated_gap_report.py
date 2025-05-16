"""Tests for the integrated gap report page.

This module tests the integrated UI for condition gaps and silent dropouts.
"""

import pytest
import pandas as pd
import panel as pn
from unittest.mock import patch

from app.pages.gap_report_page import GapReportPage


@pytest.fixture
def gap_report_page():
    """Create a GapReportPage instance for testing."""
    return GapReportPage()


@pytest.fixture
def mock_condition_data():
    """Create mock data for condition gap reports."""
    return pd.DataFrame(
        {
            "patient_id": [1, 2, 3],
            "bmi": [32.1, 35.2, 30.5],
            "date": ["2025-05-01", "2025-05-02", "2025-05-03"],
        }
    )


@pytest.fixture
def mock_dropout_data():
    """Create mock data for silent dropout reports."""
    return pd.DataFrame(
        {
            "patient_id": [4, 5, 6],
            "first_name": ["John", "Jane", "Sam"],
            "last_name": ["Doe", "Smith", "Johnson"],
            "last_lab_date": ["2025-01-15", "2025-01-20", "2025-01-10"],
            "most_recent_activity": ["2025-01-15", "2025-01-20", "2025-01-10"],
            "days_since_activity": [120, 115, 125],
            "activity_count": [3, 4, 2],
        }
    )


def test_gap_report_initialization(gap_report_page):
    """Test that the page initializes correctly."""
    # Check default report type
    assert gap_report_page.report_type == "Condition Gaps"

    # Check default condition
    assert gap_report_page.condition in gap_report_page._condition_options

    # Check parameter defaults
    assert gap_report_page.active_only is True
    assert gap_report_page.inactivity_days == 90
    assert gap_report_page.minimum_activity_count == 2


def test_report_type_toggle(gap_report_page):
    """Test toggling between report types updates the UI correctly."""
    # Initial state
    assert gap_report_page.param.condition.objects == gap_report_page._condition_options

    # Change to Engagement Issues
    gap_report_page.report_type = "Engagement Issues"

    # Check dropdown contents changed
    assert (
        gap_report_page.param.condition.objects == gap_report_page._engagement_options
    )
    assert gap_report_page.condition == "Silent Dropouts"


@patch("app.pages.gap_report_page.get_condition_gap_report")
def test_generate_condition_report(
    mock_get_condition, gap_report_page, mock_condition_data
):
    """Test generating a condition gap report."""
    # Mock the condition gap report function
    mock_get_condition.return_value = mock_condition_data

    # Run the report
    gap_report_page._generate_report()

    # Check the report was generated correctly
    mock_get_condition.assert_called_once_with(
        gap_report_page.condition, active_only=gap_report_page.active_only
    )

    # Check the table was updated
    assert gap_report_page._table_panel.value.equals(mock_condition_data)

    # Check visibility
    assert gap_report_page._table_panel.visible is True
    assert gap_report_page._blank.visible is False
    assert gap_report_page._mark_inactive_btn.visible is False
    assert gap_report_page._total_count.visible is True


@patch("app.pages.gap_report_page.get_clinical_inactivity_report")
def test_generate_dropout_report(mock_get_dropout, gap_report_page, mock_dropout_data):
    """Test generating a silent dropout report."""
    # Set to Engagement Issues
    gap_report_page.report_type = "Engagement Issues"

    # Mock the dropout report function
    mock_get_dropout.return_value = mock_dropout_data

    # Run the report
    gap_report_page._generate_report()

    # Check the report was generated correctly
    mock_get_dropout.assert_called_once_with(
        inactivity_days=gap_report_page.inactivity_days,
        minimum_activity_count=gap_report_page.minimum_activity_count,
        active_only=gap_report_page.active_only,
    )

    # Check the table was updated
    assert gap_report_page._table_panel.value.equals(mock_dropout_data)

    # Check visibility
    assert gap_report_page._table_panel.visible is True
    assert gap_report_page._blank.visible is False
    assert gap_report_page._mark_inactive_btn.visible is True
    assert gap_report_page._total_count.visible is True


@patch("app.pages.gap_report_page.mark_patient_as_inactive")
def test_mark_inactive_functionality(mock_mark_inactive, gap_report_page):
    """Test marking patients as inactive."""
    # Create a mocked version of the _mark_selected_inactive method to verify it works
    original_method = gap_report_page._mark_selected_inactive

    # Create simple flags to verify the method was called with correct data
    test_data = {"method_called": False, "patient_ids": []}

    def mock_mark_selected_inactive(*args, **kwargs):
        test_data["method_called"] = True
        test_data["patient_ids"] = gap_report_page._selected_patients
        return original_method(*args, **kwargs)

    # Replace the method with our mocked version
    gap_report_page._mark_selected_inactive = mock_mark_selected_inactive

    # Set up test data
    gap_report_page._selected_patients = [1, 3]
    mock_mark_inactive.side_effect = [True, True]  # Both operations successful

    # Call the method through our wrapper
    gap_report_page._mark_selected_inactive()

    # Verify our mock was called with the correct data
    assert test_data["method_called"] is True
    assert test_data["patient_ids"] == [1, 3]
    assert mock_mark_inactive.call_count == 2
    mock_mark_inactive.assert_any_call(1)
    mock_mark_inactive.assert_any_call(3)


def test_view_layout(gap_report_page):
    """Test the view layout contains all necessary components."""
    view = gap_report_page.view()

    # Check it's a Column layout
    assert isinstance(view, pn.Column)

    # Verify essential components
    component_types = [type(comp) for comp in view.objects]

    # Check for headings - should have at least one Markdown heading
    markdown_components = [
        obj for obj in view.objects if isinstance(obj, pn.pane.Markdown)
    ]
    assert len(markdown_components) > 0

    # Find the toggle for report type selection
    toggle_components = []
    for obj in view.objects:
        if isinstance(obj, pn.Row):
            for item in obj.objects:
                if isinstance(item, pn.widgets.Switch):
                    toggle_components.append(item)
                # Look one level deeper for nested components
                elif isinstance(item, pn.Row) or isinstance(item, pn.Column):
                    for nested_item in item.objects:
                        if isinstance(nested_item, pn.widgets.Switch):
                            toggle_components.append(nested_item)

    # Should have at least one switch component (might be wrapped in a Row)
    assert len(toggle_components) > 0

    # Find the button components (e.g., Run button)
    buttons = []
    for obj in view.objects:
        if isinstance(obj, pn.Row):
            for item in obj.objects:
                if isinstance(item, pn.widgets.Button):
                    buttons.append(item)

    # Should have at least one button
    assert len(buttons) > 0


def test_error_handling(gap_report_page):
    """Test error handling during report generation."""
    # Mock a function to raise an exception
    with patch(
        "app.pages.gap_report_page.get_condition_gap_report",
        side_effect=Exception("Test error"),
    ):

        # Run the report (should catch the exception)
        gap_report_page._generate_report()

        # Check error handling
        assert gap_report_page._df.empty
        assert gap_report_page._status.visible is True
        assert "Error" in gap_report_page._status.object
        assert gap_report_page._download_btn.disabled is True
