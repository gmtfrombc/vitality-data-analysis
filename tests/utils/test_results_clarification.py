"""Tests for the active patient clarification in result display."""

import pytest
from app.pages.data_assistant import DataAnalysisAssistant
from app.utils.query_intent import QueryIntent, Filter


def test_active_filter_detection_in_scalar_results():
    """Test that active filter is detected and mentioned in scalar result summaries."""
    assistant = DataAnalysisAssistant()

    # Create a mock intent with active filter
    intent = QueryIntent(
        analysis_type="average",
        target_field="bmi",
        filters=[Filter(field="gender", value="F"), Filter(field="active", value=1)],
        conditions=[],
        parameters={},
        additional_fields=[],
        group_by=[],
    )

    # Set up the test scenario
    assistant.query_text = "What is the average BMI of female patients?"
    assistant.query_intent = intent
    assistant.intermediate_results = 27.26  # Mock scalar BMI result

    # Generate the final results
    assistant._generate_final_results()

    # Verify active patients is mentioned in the summary
    assert "active" in assistant.analysis_result["summary"].lower()
    assert "for active patients" in assistant.analysis_result["summary"].lower()


def test_active_filter_not_mentioned_when_not_applied():
    """Test that active filter clarification isn't added when not applied."""
    assistant = DataAnalysisAssistant()

    # Create a mock intent without active filter
    intent = QueryIntent(
        analysis_type="average",
        target_field="bmi",
        filters=[
            Filter(field="gender", value="F"),
        ],
        conditions=[],
        parameters={},
        additional_fields=[],
        group_by=[],
    )

    # Set up the test scenario
    assistant.query_text = "What is the average BMI of female patients?"
    assistant.query_intent = intent
    assistant.intermediate_results = 27.89  # Mock scalar BMI result

    # Generate the final results
    assistant._generate_final_results()

    # Verify active patients is NOT mentioned in the summary
    assert "active" not in assistant.analysis_result["summary"].lower()


def test_active_filter_detection_in_dictionary_results():
    """Test that active filter is detected and mentioned in complex dictionary results."""
    assistant = DataAnalysisAssistant()

    # Import pandas for creating a proper DataFrame
    import pandas as pd

    # Create mock intermediate results with active_patients key
    mock_results = {
        "stats": {"avg_bmi": 27.26, "unique_patients": 8},
        # Signal that active filtering occurred
        "active_patients": ["p001", "p002", "p003"],
        "bmi_data": pd.DataFrame(),  # Empty DataFrame instead of empty list
    }

    # Set up the test scenario
    assistant.query_text = "What is the BMI distribution of female patients?"
    assistant.query_intent = None  # No intent needed for this test
    assistant.intermediate_results = mock_results
    # Force fallback to simple text summary
    assistant._show_narrative_checkbox = None

    # Generate the final results
    assistant._generate_final_results()

    # Check if the summary includes active patients note
    assert "active" in assistant.analysis_result["summary"].lower()


def test_ai_interpretation_with_active_filter():
    """Test that AI interpretations get active status appended when needed."""
    # Skip this test if we're in offline/test mode without OpenAI key
    import os

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Skipping AI interpretation test in offline mode")

    assistant = DataAnalysisAssistant()

    # Create a mock intent with active filter
    intent = QueryIntent(
        analysis_type="average",
        target_field="bmi",
        filters=[Filter(field="gender", value="F"), Filter(field="active", value=1)],
        conditions=[],
        parameters={},
        additional_fields=[],
        group_by=[],
    )

    # Mock AI interpretation that doesn't mention active status
    def mock_interpret_results(query, results, visualizations):
        return "The average BMI for female patients is 27.26."

    # Set up the test scenario with monkeypatched AI interpretation
    assistant.query_text = "What is the average BMI of female patients?"
    assistant.query_intent = intent
    assistant.intermediate_results = {"mock": "data"}

    # Patch the AI interpretation temporarily
    original_interpret = getattr(assistant, "ai.interpret_results", None)
    try:
        # Monkeypatch the interpretation
        import types

        assistant.ai = types.SimpleNamespace()
        assistant.ai.interpret_results = mock_interpret_results

        # Generate the final results
        assistant._generate_final_results()

        # Verify active patients is mentioned in the summary
        assert "active" in assistant.analysis_result["summary"].lower()
        assert "for active patients" in assistant.analysis_result["summary"].lower()
    finally:
        # Restore original if it existed
        if original_interpret:
            assistant.ai.interpret_results = original_interpret
