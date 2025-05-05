from app.ai_helper import AIHelper
import os


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
    """Both attempts bad JSON → fallback dict with error key."""

    helper = AIHelper()

    monkeypatch.setattr(helper, "_ask_llm", lambda p, q: INVALID_JSON)

    intent = helper.get_query_intent("whatever")

    assert isinstance(intent, dict)
    assert intent["analysis_type"] == "unknown"
    assert "error" in intent["parameters"]


def test_low_confidence_triggers_clarification(monkeypatch):
    """_process_current_stage should stop at STAGE_CLARIFYING when intent unknown."""

    # Skip test if we're in offline mode to avoid conflicts with offline shortcuts
    if not os.getenv("OPENAI_API_KEY"):
        import pytest

        pytest.skip("Skipping clarification test in offline mode")

    from app.pages.data_assistant import DataAnalysisAssistant

    assistant = DataAnalysisAssistant()

    # Force unknown intent
    monkeypatch.setattr(
        "app.ai_helper.ai.get_query_intent",
        lambda q: {"analysis_type": "unknown"},
    )

    monkeypatch.setattr(
        "app.ai_helper.ai.generate_clarifying_questions",
        lambda q: ["Which date range?"],
    )

    assistant.query_text = "Some vague question"
    assistant._process_current_stage()

    assert assistant.current_stage == assistant.STAGE_CLARIFYING
    # Ensure clarifying text displayed (property added for tests to access)
    assert "clarify" in assistant.clarifying_text.lower()


def test_low_confidence_generic_target(monkeypatch):
    from app.pages.data_assistant import DataAnalysisAssistant
    from app.utils.query_intent import QueryIntent

    assistant = DataAnalysisAssistant()

    # Craft generic intent object
    intent_obj = QueryIntent(
        analysis_type="change",
        target_field="score_value",
        filters=[],
        conditions=[],
        parameters={},
    )

    monkeypatch.setattr("app.ai_helper.ai.get_query_intent", lambda q: intent_obj)
    monkeypatch.setattr(
        "app.ai_helper.ai.generate_clarifying_questions", lambda q: ["Which metric?"]
    )

    assistant.query_text = "Patient better?"
    assistant._process_current_stage()

    assert assistant.current_stage == assistant.STAGE_CLARIFYING
