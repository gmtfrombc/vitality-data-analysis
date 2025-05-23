"""Tests for verifying the reset functionality in DataAnalysisAssistant."""

from unittest.mock import MagicMock, patch
from app.data_assistant import DataAnalysisAssistant
from app.state import WorkflowStages


@patch("app.data_assistant.UIComponents")
@patch("app.data_assistant.AnalysisEngine")
def test_reset_all_basic_functionality(mock_engine, mock_ui):
    """Test the basic reset functionality focusing on clearing data attributes."""
    # Create a properly initialized instance with mocked components
    assistant = DataAnalysisAssistant()

    # Set up data to be reset
    assistant.query_text = "Test query"
    assistant.question_name = "Test name"
    assistant.workflow.current_stage = WorkflowStages.RESULTS
    assistant.generated_code = "Test code"
    assistant.intermediate_results = {"test": 27.26}
    assistant.analysis_result = {"test": "result"}

    # Mock clarifying questions and data samples
    assistant.engine.get_clarifying_questions = MagicMock(
        return_value=["Test question"]
    )
    assistant.data_samples = {"test": "data"}

    # Mock UI components
    assistant.ui.save_question_input = MagicMock()
    assistant.ui.query_input = MagicMock()
    assistant.ui.visualization_pane = MagicMock()
    assistant.ui.update_stage_indicators = MagicMock()
    assistant.ui.update_status = MagicMock()

    # Mock feedback widget
    assistant.feedback_widget = MagicMock()
    assistant.feedback_widget.visible = True

    # Call the reset method
    assistant._reset_all()

    # Verify data attributes were reset
    assert assistant.query_text == ""
    assert assistant.question_name == ""
    assert assistant.workflow.current_stage == WorkflowStages.INITIAL
    assert assistant.generated_code == ""
    assert assistant.intermediate_results is None
    assert assistant.analysis_result == {}

    # Verify feedback widget visibility was set to False
    assert assistant.feedback_widget.visible is False

    # Verify UI components were updated
    assistant.ui.update_stage_indicators.assert_called_once()
    assistant.ui.save_question_input.value = ""
