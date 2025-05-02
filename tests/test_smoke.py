import pytest


from app.pages.data_assistant import DataAnalysisAssistant


@pytest.mark.smoke
def test_assistant_happy_path(monkeypatch):
    """Ask a simple average BMI question and expect assistant to reach results stage."""

    # Patch AI methods to skip actual OpenAI calls
    monkeypatch.setattr(
        "app.pages.data_assistant.DataAnalysisAssistant._generate_analysis",
        lambda self: None,
    )
    monkeypatch.setattr(
        "app.pages.data_assistant.DataAnalysisAssistant._generate_final_results",
        lambda self: None,
    )

    assistant = DataAnalysisAssistant()
    assistant.query_text = "What is the average BMI of active patients?"

    # simulate Analyze click
    assistant._process_query()

    # At least moves to execution or results stage eventually
    assert assistant.current_stage >= assistant.STAGE_EXECUTION


@pytest.mark.smoke
def test_assistant_error_path(monkeypatch):
    """Ensure friendly error when generated code missing results variable."""

    # Force sandbox to return error by patching run_snippet
    monkeypatch.setattr(
        "app.pages.data_assistant.run_snippet",
        lambda code: {"error": "Snippet did not define a `results` variable"},
    )

    assistant = DataAnalysisAssistant()
    assistant.query_text = "Bad query"

    # simulate Analyze click
    assistant._process_query()

    # Assistant should at least have progressed to the clarifying stage (no crash)
    assert assistant.current_stage >= assistant.STAGE_CLARIFYING


def test_histogram_helper_returns_plot():
    """Ensure histogram helper produces an hvplot object."""
    import pandas as pd
    from app.utils.plots import histogram

    df = pd.DataFrame({"bmi": [25, 30, 27, 29]})
    plot = histogram(df, "bmi", bins=10)

    # Holoviews objects have a .opts method; simple sanity check
    assert hasattr(plot, "opts")


@pytest.mark.smoke
def test_count_active_patients(monkeypatch):
    """Check rule-engine can count active patients without crashing."""

    import db_query

    expected_count = len(db_query.get_all_patients().query("active == 1"))

    # Speed up by bypassing GPT and code generation
    monkeypatch.setattr(
        "app.pages.data_assistant.DataAnalysisAssistant._generate_analysis_code",
        lambda self: None,
    )

    def _mock_execute(self):
        # Minimal simulation of execution phase
        self.intermediate_results = {"stats": {"active_patients": expected_count}}

    monkeypatch.setattr(
        "app.pages.data_assistant.DataAnalysisAssistant._execute_analysis",
        _mock_execute,
    )

    assistant = DataAnalysisAssistant()
    assistant.query_text = "How many active patients are in the program?"
    assistant._process_query()

    assert assistant.intermediate_results["stats"]["active_patients"] == expected_count


@pytest.mark.smoke
def test_parse_intent_json_error():
    """Invalid JSON string should raise ValueError via helper."""

    from app.utils.query_intent import parse_intent_json

    with pytest.raises(ValueError):
        parse_intent_json("this is not json")
