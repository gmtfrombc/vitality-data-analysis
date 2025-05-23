from __future__ import annotations

"""Smoke tests for the refactored data assistant components.

These tests verify that the refactored components (UI, Engine, State, Analysis Helpers)
work together properly in the full pipeline flow.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.data_assistant import DataAnalysisAssistant
from app.state import WorkflowStages


@pytest.mark.smoke
def test_refactored_components_basic_flow():
    """Test that the refactored components work together in a basic query flow."""
    # Create the assistant with mocked components
    with patch("app.data_assistant.WorkflowState") as mock_workflow:
        # Create a mock workflow instance
        workflow_instance = MagicMock()
        mock_workflow.return_value = workflow_instance

        # Create the assistant with the mocked workflow
        assistant = DataAnalysisAssistant(test_mode=True)

        # Directly patch the instance methods
        assistant._process_current_stage = MagicMock()

        # Mock the UI updates to prevent panel rendering issues in tests
        assistant.ui.update_status = MagicMock()
        assistant.ui.start_ai_indicator = MagicMock()
        assistant.ui.stop_ai_indicator = MagicMock()
        assistant.ui.update_stage_indicators = MagicMock()

        # Set up a test query
        test_query = "What is the average BMI of male patients?"
        assistant.query_text = test_query

        # Mock the engine's methods to return predictable results
        mock_intent = MagicMock()
        mock_intent.analysis_type = "average"
        mock_intent.target_field = "bmi"
        mock_intent.filters = ["gender = 'male'"]

        # Mock the engine's process_query method
        assistant.engine.process_query = MagicMock(return_value=mock_intent)
        assistant.engine.intent = mock_intent

        # Mock needs_clarification to always return False to simplify the test
        assistant.clarification_workflow.needs_clarification = MagicMock(
            return_value=False
        )

        # Execute the query processing
        assistant._process_query()

        # Verify the query was processed correctly
        assistant.engine.process_query.assert_called_once_with(test_query)
        workflow_instance.start_query.assert_called_once_with(test_query)
        workflow_instance.mark_intent_parsed.assert_called_once_with(False)
        assistant._process_current_stage.assert_called_once()
        assistant.ui.start_ai_indicator.assert_called_once()

        # Test code generation independently
        # Create a backup of the method
        orig_process_stage = assistant._process_current_stage

        # Setup for code generation test
        assistant.ui.display_generated_code = MagicMock()
        assistant.engine.generate_analysis_code = MagicMock(return_value="test code")
        assistant.engine.generated_code = "test code"

        # Call code generation with process_current_stage temporarily disabled
        assistant._process_current_stage = MagicMock()  # Avoid recursion
        assistant._generate_analysis_code()

        # Restore original method
        assistant._process_current_stage = orig_process_stage

        # Verify code generation worked
        assistant.ui.start_ai_indicator.assert_called()
        assistant.engine.generate_analysis_code.assert_called_once()
        assistant.ui.display_generated_code.assert_called_once_with("test code")
        workflow_instance.mark_code_generated.assert_called_once()

        # Test execution independently
        # Setup for execution test
        assistant.ui.display_execution_results = MagicMock()
        assistant.engine.execute_analysis = MagicMock(return_value=24.7)
        assistant.engine.execution_results = 24.7
        assistant.engine.visualizations = []

        # Call execution with process_current_stage temporarily disabled
        assistant._process_current_stage = MagicMock()  # Avoid recursion
        assistant._execute_analysis()

        # Restore original method
        assistant._process_current_stage = orig_process_stage

        # Verify execution worked
        assistant.ui.start_ai_indicator.assert_called()
        assistant.engine.execute_analysis.assert_called_once()
        assistant.ui.display_execution_results.assert_called_once()
        workflow_instance.mark_execution_complete.assert_called_once()

        # Test results display independently
        # Create our format_results mock without patching module
        mock_format_results = MagicMock(return_value=["Results"])

        # Store the original function
        original_format_results = (
            assistant._format_results if hasattr(assistant, "_format_results") else None
        )

        # Setup for results display test
        assistant.ui.add_refine_option = MagicMock(return_value=["Results", "Refine"])
        assistant.ui.result_container = MagicMock()
        assistant.ui.create_feedback_widget = MagicMock(return_value=MagicMock())
        assistant._feedback_up = MagicMock()
        assistant._feedback_down = MagicMock()
        assistant._feedback_thanks = MagicMock()

        # Replace format_results with our mock
        with patch("app.data_assistant.format_results", mock_format_results):
            # Call display results
            assistant._display_final_results()

        # Verify results display
        assistant.ui.add_refine_option.assert_called_once()
        workflow_instance.mark_results_displayed.assert_called_once()


@pytest.mark.smoke
def test_refactored_components_with_clarification():
    """Test that the refactored components handle clarification correctly."""
    # Create the assistant with mocked workflow
    with patch("app.data_assistant.WorkflowState") as mock_workflow:
        # Create a mock workflow instance
        workflow_instance = MagicMock()
        mock_workflow.return_value = workflow_instance

        # Set up workflow stage properties
        workflow_instance.current_stage = WorkflowStages.CLARIFYING

        # Create the assistant with the mocked workflow
        assistant = DataAnalysisAssistant(test_mode=True)

        # Mock the UI updates to prevent panel rendering issues in tests
        assistant.ui.update_status = MagicMock()
        assistant.ui.start_ai_indicator = MagicMock()
        assistant.ui.stop_ai_indicator = MagicMock()
        assistant.ui.update_stage_indicators = MagicMock()
        assistant.ui.display_clarifying_questions = MagicMock()
        assistant.ui.clarifying_pane = MagicMock()
        assistant.ui.clarifying_pane.visible = True

        # Mock _process_current_stage to avoid recursion issues
        assistant._process_current_stage = MagicMock()

        # Set up a test query
        test_query = "Compare patient weights"
        assistant.query_text = test_query

        # Mock the engine's methods to return ambiguous intent initially
        ambiguous_intent = MagicMock()
        ambiguous_intent.analysis_type = "unknown"
        ambiguous_intent.target_field = "weight"

        # Mock the engine methods
        assistant.engine.process_query = MagicMock(return_value=ambiguous_intent)
        assistant.engine.intent = ambiguous_intent
        # Remove any mock for engine.generate_clarifying_questions
        # assistant.engine.generate_clarifying_questions = MagicMock(
        #     return_value=["Which patient groups do you want to compare?"]
        # )

        # Patch clarification_workflow to always need clarification and return a test question
        assistant.clarification_workflow.needs_clarification = MagicMock(
            return_value=True
        )
        assistant.clarification_workflow.get_clarifying_questions = MagicMock(
            return_value=["Which patient groups do you want to compare?"]
        )

        # Force the workflow to need clarification
        assistant._is_truly_ambiguous_query = MagicMock(return_value=True)

        # Execute query processing
        assistant._process_query()

        # Verify intent parsing with clarification
        assistant.engine.process_query.assert_called_once_with(test_query)
        workflow_instance.start_query.assert_called_once_with(test_query)
        workflow_instance.mark_intent_parsed.assert_called_once_with(True)

        # Test clarification questions display
        assistant._display_clarifying_questions()

        # Verify clarification UI
        assistant.clarification_workflow.get_clarifying_questions.assert_called_once()
        assistant.ui.display_clarifying_questions.assert_called_once()
        assistant.ui.update_status.assert_called_with(
            "Please answer the clarifying questions"
        )
        assistant.ui.stop_ai_indicator.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
