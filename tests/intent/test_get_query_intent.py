"""
Tests for AIHelper.get_query_intent().

The real OpenAI call is monkey-patched so tests run offline & deterministically.
"""

import json
from typing import Dict, List

import pytest

from app.ai_helper import AIHelper
from app.utils.query_intent import QueryIntent


@pytest.fixture()
def ai_helper_stub(monkeypatch) -> AIHelper:  # noqa: D401 - fixture
    """Return an *AIHelper* instance whose LLM call is stubbed.

    The private ``_ask_llm`` method is monkey-patched to return the *expected* JSON
    for each test case so that the logic inside *get_query_intent* can be tested
    without a network connection or OpenAI key.
    """

    helper = AIHelper()

    # Storage for the next response the stub should inject
    _next_response: Dict[str, str] | None = None

    def _fake_llm(prompt: str, query: str) -> str:  # noqa: D401 - inner stub
        nonlocal _next_response
        if _next_response is None:
            raise RuntimeError("Stubbed _ask_llm called without queued response")
        reply = _next_response["json"]
        _next_response = None  # consumed
        return reply

    monkeypatch.setattr(helper, "_ask_llm", _fake_llm)

    # Helper to queue the next LLM response for a given expected JSON dict.
    def _queue(json_dict: Dict[str, str]):  # noqa: D401 - nested helper
        nonlocal _next_response
        _next_response = {"json": json.dumps(json_dict)}

    # Attach queue helper for test code convenience.
    helper._queue_response = _queue  # type: ignore[attr-defined]

    return helper


# ---------------------------------------------------------------------------
# Parametrised scenarios -----------------------------------------------------
# ---------------------------------------------------------------------------

test_cases: List[Dict[str, str]] = [
    {
        "query": "How many female patients have a BMI over 30?",
        "expected": {
            "analysis_type": "count",
            "target_field": "bmi",
            "filters": [{"field": "gender", "value": "F"}],
            "conditions": [{"field": "bmi", "operator": ">", "value": 30}],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "What is the average weight of active patients?",
        "expected": {
            "analysis_type": "average",
            "target_field": "weight",
            "filters": [{"field": "active", "value": 1}],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "Show the BMI distribution across all patients",
        "expected": {
            "analysis_type": "distribution",
            "target_field": "bmi",
            "filters": [],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "What is the average weight and BMI for active patients under 60?",
        "expected": {
            "analysis_type": "average",
            "target_field": "weight",
            "filters": [{"field": "active", "value": 1}],
            "conditions": [{"field": "age", "operator": "<", "value": 60}],
            "parameters": {},
            "additional_fields": ["bmi"],
            "group_by": [],
        },
    },
    {
        "query": "Show patient count per ethnicity",
        "expected": {
            "analysis_type": "count",
            "target_field": "patient_id",
            "filters": [],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": ["ethnicity"],
        },
    },
    {
        "query": "Average weight by gender for patients with BMI > 25",
        "expected": {
            "analysis_type": "average",
            "target_field": "weight",
            "filters": [],
            "conditions": [{"field": "bmi", "operator": ">", "value": 25}],
            "parameters": {},
            "additional_fields": [],
            "group_by": ["gender"],
        },
    },
    {
        "query": "How many patients have systolic blood pressure over 140?",
        "expected": {
            "analysis_type": "count",
            "target_field": "sbp",
            "filters": [],
            "conditions": [{"field": "sbp", "operator": ">", "value": 140}],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "Average blood sugar for active patients",
        "expected": {
            "analysis_type": "average",
            "target_field": "score_value",
            "filters": [{"field": "active", "value": 1}],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
]


@pytest.mark.parametrize("case", test_cases)
def test_get_query_intent(ai_helper_stub: AIHelper, case):  # noqa: D103 - test
    # Queue the stubbed JSON response so *get_query_intent* consumes it.
    # type: ignore[attr-defined]
    ai_helper_stub._queue_response(case["expected"])

    # Act
    intent = ai_helper_stub.get_query_intent(case["query"])

    # Assert – returned object should be a validated *QueryIntent*
    assert isinstance(intent, QueryIntent)
    # Convert to plain dict (pydantic >2) for simple comparison
    intent_dict = json.loads(intent.model_dump_json())

    # Remove optional None fields inserted by pydantic
    for f in intent_dict["filters"]:
        if "range" in f and f["range"] is None:
            f.pop("range")
        if "date_range" in f and f["date_range"] is None:
            f.pop("date_range")

    # Remove time_range if None (new field added for date range filtering)
    if "time_range" in intent_dict and intent_dict["time_range"] is None:
        intent_dict.pop("time_range")

    assert intent_dict == case["expected"]
