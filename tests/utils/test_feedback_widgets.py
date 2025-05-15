"""Tests for feedback widgets.

Tests for the UI feedback widget components used in the continuous
feedback and evaluation system.
"""

import panel as pn
from unittest.mock import patch

from app.utils.feedback_widgets import FeedbackWidget, create_feedback_widget


def test_feedback_widget_initialization():
    """Test that the FeedbackWidget initializes correctly."""
    # Create a widget
    query = "What is the average BMI of patients?"
    widget = FeedbackWidget(query=query)

    # Check basic properties
    assert widget.query == query
    assert widget.rating == ""
    assert widget.show_comment is False
    assert widget.comment == ""
    assert widget.submitted is False

    # Check UI components
    assert widget.thumbs_up is not None
    assert widget.thumbs_down is not None
    assert widget.comment_input is not None
    assert widget.submit_button is not None
    assert widget.thank_you is not None

    # Default button states
    assert widget.thumbs_up.button_type == "success"
    assert widget.thumbs_down.button_type == "danger"
    assert widget.submit_button.disabled is True
    assert widget.comment_input.visible is True
    assert widget.thank_you.visible is False


def test_feedback_widget_thumbs_up():
    """Test thumbs up behavior."""
    widget = FeedbackWidget(query="Test query")

    # Simulate thumbs up click
    widget._on_thumbs_up(None)

    # Check state changes
    assert widget.rating == "up"
    assert widget.thumbs_up.button_type == "success"
    assert widget.thumbs_down.button_type == "light"
    assert widget.submit_button.disabled is False
    assert widget.show_comment is False
    assert widget.comment_input.visible is True


def test_feedback_widget_thumbs_down():
    """Test thumbs down behavior."""
    widget = FeedbackWidget(query="Test query")

    # Simulate thumbs down click
    widget._on_thumbs_down(None)

    # Check state changes
    assert widget.rating == "down"
    assert widget.thumbs_up.button_type == "light"
    assert widget.thumbs_down.button_type == "danger"
    assert widget.submit_button.disabled is False
    assert widget.show_comment is True
    assert widget.comment_input.visible is True


@patch("app.utils.feedback_widgets.insert_feedback")
def test_feedback_widget_submit(mock_insert):
    """Test submission flow."""
    # Configure mock
    mock_insert.return_value = True

    # Create widget and simulate rating
    widget = FeedbackWidget(query="Test query")
    widget._on_thumbs_up(None)

    # Simulate submission
    widget._on_submit(None)

    # Check database call
    mock_insert.assert_called_once_with(
        question="Test query", rating="up", comment=None
    )

    # Check UI state after submission
    assert widget.submitted is True
    assert widget.thumbs_up.visible is False
    assert widget.thumbs_down.visible is False
    assert widget.submit_button.visible is False
    assert widget.thank_you.visible is True


def test_create_feedback_widget():
    """Test the helper function returns a valid Panel component."""
    query = "Test query"
    result = create_feedback_widget(query)

    # Should be a Panel component
    assert isinstance(result, pn.viewable.Viewable)
