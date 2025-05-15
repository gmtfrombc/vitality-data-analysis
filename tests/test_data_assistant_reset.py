"""Tests for verifying the reset functionality in DataAnalysisAssistant."""

from unittest.mock import MagicMock

from app.pages.data_assistant import DataAnalysisAssistant


def test_reset_all_basic_functionality():
    """Test the basic reset functionality focusing on clearing data attributes."""
    # Create a minimal instance
    assistant = DataAnalysisAssistant.__new__(DataAnalysisAssistant)

    # Set up data to be reset
    assistant.query_text = "Test query"
    assistant.question_name = "Test name"
    assistant.current_stage = 4  # STAGE_RESULTS
    assistant.clarifying_questions = ["Test question"]
    assistant.data_samples = {"test": "data"}
    assistant.generated_code = "Test code"
    assistant.intermediate_results = 27.26
    assistant.analysis_result = {"test": "result"}

    # Mock required methods to prevent errors
    assistant._update_stage_indicators = MagicMock()
    assistant._update_status = MagicMock()
    assistant._stop_ai_indicator = MagicMock()

    # Mock required UI components
    assistant.query_input = MagicMock()
    assistant.save_question_input = MagicMock()
    assistant.result_pane = MagicMock()
    assistant.code_display = MagicMock()
    assistant.visualization_pane = MagicMock()
    assistant.clarifying_input = MagicMock()
    assistant.clarifying_pane = MagicMock()
    assistant.clarifying_pane.objects = []
    assistant.code_generation_pane = MagicMock()
    assistant.code_generation_pane.objects = []
    assistant.execution_pane = MagicMock()
    assistant.execution_pane.objects = []

    # For the result container, create a simple mock that will track operations
    assistant.result_container = MagicMock()
    assistant.feedback_widget = MagicMock()

    # Call the reset method
    assistant._reset_all()

    # Verify data attributes were reset
    assert assistant.query_text == ""
    assert assistant.question_name == ""
    assert assistant.clarifying_questions == []
    assert assistant.data_samples == {}
    assert assistant.generated_code == ""
    assert assistant.intermediate_results is None
    assert assistant.analysis_result == {}

    # Verify feedback widget visibility was set to False
    assert assistant.feedback_widget.visible is False
