# New tricky queries test

import json
from typing import Dict, List

import pytest

from app.ai_helper import AIHelper
from app.utils.query_intent import QueryIntent


@pytest.fixture()
def ai_helper_stub(monkeypatch) -> AIHelper:  # noqa: D401 - fixture
    """Return an AIHelper whose LLM call is stubbed for offline testing."""

    helper = AIHelper()

    _next_response: Dict[str, str] | None = None

    def _fake_llm(prompt: str, query: str) -> str:  # noqa: D401
        nonlocal _next_response
        if _next_response is None:
            raise RuntimeError("Stub called without queued response")
        reply = _next_response["json"]
        _next_response = None
        return reply

    monkeypatch.setattr(helper, "_ask_llm", _fake_llm)

    def _queue(json_dict: Dict[str, str]):  # noqa: D401
        nonlocal _next_response
        _next_response = {"json": json.dumps(json_dict)}

    helper._queue_response = _queue  # type: ignore[attr-defined]
    return helper


TRICKY_CASES: List[Dict[str, str]] = [
    {
        "query": "Total patients with HbA1c above 7",
        "expected": {
            "analysis_type": "count",
            "target_field": "score_value",
            "filters": [{"field": "score_type", "value": "A1C"}],
            "conditions": [{"field": "score_value", "operator": ">", "value": 7}],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "Compare BMI between men and women",
        "expected": {
            "analysis_type": "comparison",
            "target_field": "bmi",
            "filters": [],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": ["gender"],
        },
    },
    {
        "query": "List top 5 ages",
        "expected": {
            "analysis_type": "top_n",
            "target_field": "age",
            "filters": [],
            "conditions": [],
            "parameters": {"n": 5},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "Percent change in weight for active patients",
        "expected": {
            "analysis_type": "percent_change",
            "target_field": "weight",
            "filters": [{"field": "active", "value": 1}],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "Std dev of diastolic BP",
        "expected": {
            "analysis_type": "std_dev",
            "target_field": "dbp",
            "filters": [],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "Median body weight",
        "expected": {
            "analysis_type": "median",
            "target_field": "weight",
            "filters": [],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "Variance in glucose",
        "expected": {
            "analysis_type": "variance",
            "target_field": "score_value",
            "filters": [{"field": "score_type", "value": "GLUCOSE"}],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "Trend of BMI for last 6 months",
        "expected": {
            "analysis_type": "trend",
            "target_field": "bmi",
            "filters": [],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "How many patients are inactive",
        "expected": {
            "analysis_type": "count",
            "target_field": "patient_id",
            "filters": [{"field": "active", "value": 0}],
            "conditions": [],
            "parameters": {},
            "additional_fields": [],
            "group_by": [],
        },
    },
    {
        "query": "Top 3 ethnicities by patient count",
        "expected": {
            "analysis_type": "top_n",
            "target_field": "ethnicity",
            "filters": [],
            "conditions": [],
            "parameters": {"n": 3},
            "additional_fields": [],
            "group_by": [],
        },
    },
]


@pytest.mark.parametrize("case", TRICKY_CASES)
def test_tricky_queries(ai_helper_stub: AIHelper, case):  # noqa: D103
    # type: ignore[attr-defined]
    ai_helper_stub._queue_response(case["expected"])
    intent = ai_helper_stub.get_query_intent(case["query"])
    assert isinstance(intent, QueryIntent)
    intent_dict = json.loads(intent.model_dump_json())

    for f in intent_dict["filters"]:
        if "range" in f and f["range"] is None:
            f.pop("range")
        if "date_range" in f and f["date_range"] is None:
            f.pop("date_range")
    if "time_range" in intent_dict and intent_dict["time_range"] is None:
        intent_dict.pop("time_range")

    assert intent_dict == case["expected"]
