from app.utils.ai_helper import AIHelper
import os
import pytest


VALID_JSON = '{"analysis_type": "count", "target_field": "bmi", "filters": [], "conditions": [], "parameters": {}}'

INVALID_JSON = "this is not json"


def test_intent_success_first_try(monkeypatch):
    """_ask_llm returns valid JSON on first attempt → helper returns QueryIntent."""

    helper = AIHelper()

    monkeypatch.setattr(helper, "_ask_llm", lambda prompt, query: VALID_JSON)

    intent = helper.get_query_intent("How many active patients?")
    # Should be a dict-like if fallback but QueryIntent when parse succeeds
    from app.utils.query_intent import QueryIntent

    assert isinstance(intent, QueryIntent)
    assert intent.analysis_type == "count"


def test_intent_retry_then_success(monkeypatch):
    """First reply bad JSON, second good → helper succeeds on attempt 2."""

    helper = AIHelper()

    calls = {"n": 0}

    def fake_ask(prompt, query):
        calls["n"] += 1
        return INVALID_JSON if calls["n"] == 1 else VALID_JSON

    monkeypatch.setattr(helper, "_ask_llm", fake_ask)

    intent = helper.get_query_intent("average bmi")
    from app.utils.query_intent import QueryIntent

    assert isinstance(intent, QueryIntent)
    assert calls["n"] == 2


def test_intent_all_fail(monkeypatch):
    """Both attempts bad JSON → should raise IntentParseError."""
    from app.errors import IntentParseError

    helper = AIHelper()
    monkeypatch.setattr(helper, "_ask_llm", lambda p, q: INVALID_JSON)
    with pytest.raises(IntentParseError):
        helper.get_query_intent("whatever")


def test_low_confidence_triggers_clarification(monkeypatch):
    """_process_current_stage should stop at CLARIFYING when intent unknown."""

    # Skip test if we're in offline mode to avoid conflicts with offline shortcuts
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Skipping clarification test in offline mode")

    from app.data_assistant import DataAnalysisAssistant
    from app.state import WorkflowStages

    assistant = DataAnalysisAssistant(test_mode=True)

    # Force unknown intent
    monkeypatch.setattr(
        assistant.engine,
        "process_query",
        lambda q: {"analysis_type": "unknown"},
    )

    # Patch clarification_workflow to always need clarification
    assistant.clarification_workflow.needs_clarification = (
        lambda intent, query_text: True
    )
    assistant.clarification_workflow.get_clarifying_questions = (
        lambda intent, query_text: ["Which date range?"]
    )
    # monkeypatch.setattr(
    #     assistant.engine,
    #     "generate_clarifying_questions",
    #     lambda: ["Which date range?"],
    # )

    assistant.query_text = "Some vague question"

    # Set workflow to initial and then process query
    assistant.workflow.reset()
    assistant._process_query()

    # Check that we're in clarifying stage
    assert assistant.workflow.current_stage == WorkflowStages.CLARIFYING
    # Ensure clarifying questions are displayed
    assert assistant.ui.clarifying_pane.visible


def test_low_confidence_generic_target(monkeypatch):
    from app.data_assistant import DataAnalysisAssistant
    from app.utils.query_intent import QueryIntent
    from app.state import WorkflowStages

    assistant = DataAnalysisAssistant(test_mode=True)

    # Craft generic intent object
    intent_obj = QueryIntent(
        analysis_type="change",
        target_field="score_value",
        filters=[],
        conditions=[],
        parameters={},
    )

    monkeypatch.setattr(assistant.engine, "process_query", lambda q: intent_obj)

    # Patch clarification_workflow get_clarifying_questions to return a test question
    monkeypatch.setattr(
        assistant.clarification_workflow,
        "get_clarifying_questions",
        lambda intent, query_text: ["Which metric?"],
    )
    # monkeypatch.setattr(
    #     assistant.engine, "generate_clarifying_questions", lambda: ["Which metric?"]
    # )

    # Mock needs_clarification to always return True
    monkeypatch.setattr(
        assistant.clarification_workflow,
        "needs_clarification",
        lambda intent, query_text: True,
    )

    assistant.query_text = "Patient better?"

    # Set workflow to initial and then process query
    assistant.workflow.reset()
    assistant._process_query()

    # Check we're in clarifying stage
    assert assistant.workflow.current_stage == WorkflowStages.CLARIFYING
