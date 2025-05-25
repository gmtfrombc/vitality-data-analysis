"""
Tests for EnhancedFeedbackWidget - Sprint 2 functionality.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.utils.enhanced_feedback_widget import (
    EnhancedFeedbackWidget,
    create_enhanced_feedback_widget,
)
from app.utils.db_migrations import apply_pending_migrations


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    try:
        Path(path).unlink()
        apply_pending_migrations(path)
        yield path
    finally:
        if Path(path).exists():
            Path(path).unlink()


class TestEnhancedFeedbackWidget:
    """Test the enhanced feedback widget functionality."""

    @patch("app.utils.enhanced_feedback_widget.insert_feedback")
    def test_positive_feedback(self, mock_insert):
        """Test positive feedback flow."""
        mock_insert.return_value = True

        widget = EnhancedFeedbackWidget(
            query="What is the average BMI?",
            original_intent_json='{"analysis_type": "average", "target_field": "bmi"}',
        )

        # Simulate thumbs up click
        widget._on_thumbs_up(None)

        # Verify feedback was recorded
        mock_insert.assert_called_once_with(
            question="What is the average BMI?", rating="up"
        )

        # Verify UI state
        assert widget.feedback_submitted
        assert widget.thank_you_section.visible

    @patch("app.utils.enhanced_feedback_widget.insert_feedback")
    def test_negative_feedback_flow(self, mock_insert):
        """Test negative feedback flow with correction capture."""
        mock_insert.return_value = True

        # Mock the feedback ID retrieval
        with patch.object(
            EnhancedFeedbackWidget, "_get_latest_feedback_id", return_value=123
        ):
            widget = EnhancedFeedbackWidget(
                query="What is the average BMI?",
                original_intent_json='{"analysis_type": "average", "target_field": "bmi"}',
                original_code="SELECT AVG(bmi) FROM vitals",
            )

            # Simulate thumbs down click
            widget._on_thumbs_down(None)

            # Verify feedback was recorded
            mock_insert.assert_called_once_with(
                question="What is the average BMI?", rating="down"
            )

            # Verify correction interface is shown
            assert not widget.feedback_section.visible
            assert widget.correction_section.visible

    def test_correction_submission(self, temp_db):
        """Test correction submission functionality."""
        # Create widget with mock correction service
        with patch(
            "app.utils.enhanced_feedback_widget.CorrectionService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.capture_correction_session.return_value = 456
            mock_service.analyze_error_type.return_value = "missing_filter"
            mock_service.generate_correction_suggestions.return_value = [
                {
                    "type": "add_filter",
                    "description": "Add patient status filter",
                    "action": "Add Filter(field='active', value=1)",
                }
            ]

            widget = EnhancedFeedbackWidget(
                query="What is the average BMI?",
                original_intent_json='{"analysis_type": "average", "target_field": "bmi"}',
            )
            widget.feedback_id = 123

            # Set correction text
            widget.correct_answer_input.value = "Should only include active patients"

            # Submit correction
            widget._on_submit_correction(None)

            # Verify correction session was created
            mock_service.capture_correction_session.assert_called_once()

            # Verify UI shows analysis section
            assert widget.analysis_section.visible

    def test_skip_correction(self):
        """Test skipping correction goes to thank you."""
        widget = EnhancedFeedbackWidget(query="Test query")

        widget._on_skip_correction(None)

        assert widget.thank_you_section.visible
        assert widget.feedback_submitted

    def test_empty_correction_validation(self):
        """Test that empty corrections are rejected."""
        widget = EnhancedFeedbackWidget(query="Test query")
        widget.feedback_id = 123

        # Try to submit empty correction
        widget.correct_answer_input.value = ""
        widget._on_submit_correction(None)

        # Should update placeholder with error message
        assert (
            "Please provide a correct answer" in widget.correct_answer_input.placeholder
        )

    def test_create_enhanced_feedback_widget_function(self):
        """Test the factory function for creating enhanced feedback widgets."""
        widget = create_enhanced_feedback_widget(
            query="Test query",
            original_intent_json='{"analysis_type": "count"}',
            original_code="SELECT COUNT(*) FROM patients",
            original_results='{"count": 100}',
        )

        # Should return a Panel Column
        import panel as pn

        assert isinstance(widget, pn.Column)

    @patch("app.utils.enhanced_feedback_widget.CorrectionService")
    def test_error_handling_in_correction_submission(self, mock_service_class):
        """Test error handling when correction submission fails."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.capture_correction_session.side_effect = Exception(
            "Database error"
        )

        widget = EnhancedFeedbackWidget(query="Test query")
        widget.feedback_id = 123
        widget.correct_answer_input.value = "Correct answer"

        # Submit correction - should handle error gracefully
        widget._on_submit_correction(None)

        # Should show thank you instead of crashing
        assert widget.thank_you_section.visible

    @patch("app.utils.enhanced_feedback_widget.insert_feedback")
    def test_feedback_recording_failure(self, mock_insert):
        """Test handling of feedback recording failures."""
        mock_insert.return_value = False

        widget = EnhancedFeedbackWidget(query="Test query")

        # Try to record feedback
        widget._on_thumbs_up(None)

        # Should not show thank you if recording failed
        assert not widget.feedback_submitted

    def test_widget_initialization_with_all_parameters(self):
        """Test widget initialization with all optional parameters."""
        callback = MagicMock()

        widget = EnhancedFeedbackWidget(
            query="Test query",
            original_intent_json='{"analysis_type": "average"}',
            original_code="SELECT AVG(bmi) FROM vitals",
            original_results='{"average": 25.5}',
            on_correction_applied=callback,
        )

        assert widget.query == "Test query"
        assert widget.original_intent_json == '{"analysis_type": "average"}'
        assert widget.original_code == "SELECT AVG(bmi) FROM vitals"
        assert widget.original_results == '{"average": 25.5}'
        assert widget.on_correction_applied == callback

    def test_widget_initialization_with_minimal_parameters(self):
        """Test widget initialization with only required parameters."""
        widget = EnhancedFeedbackWidget(query="Test query")

        assert widget.query == "Test query"
        assert widget.original_intent_json == ""
        assert widget.original_code == ""
        assert widget.original_results == ""
        assert widget.on_correction_applied is None


class TestEnhancedFeedbackWidgetIntegration:
    """Test integration aspects of the enhanced feedback widget."""

    def test_correction_service_integration(self):
        """Test that the widget properly initializes the correction service."""
        widget = EnhancedFeedbackWidget(query="Test query")

        # Should have a correction service instance
        assert hasattr(widget, "correction_service")
        assert widget.correction_service is not None

    @patch("app.utils.enhanced_feedback_widget.CorrectionService")
    def test_callback_invocation(self, mock_service_class):
        """Test that the correction applied callback is invoked."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.apply_correction.return_value = True

        callback = MagicMock()
        widget = EnhancedFeedbackWidget(
            query="Test query", on_correction_applied=callback
        )
        widget.correction_session_id = 456

        # Apply a suggestion
        suggestion = {
            "type": "add_filter",
            "description": "Add filter",
            "action": "Add filter",
        }
        widget._apply_suggestion(suggestion)

        # Verify callback was called
        callback.assert_called_once_with(456, suggestion)
