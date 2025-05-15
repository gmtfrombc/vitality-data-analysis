from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest

import app.db_query as db_query
from app.ai_helper import AIHelper
from app.utils.sandbox import run_snippet


@pytest.mark.smoke
def test_end_to_end_active_patient_count(
    monkeypatch: pytest.MonkeyPatch,
):  # noqa: D103 – smoke test
    query = "How many active patients are in the program?"

    # ------------------------------------------------------------------
    # 1. Stub the LLM call used by *get_query_intent* so the test runs offline
    # ------------------------------------------------------------------
    expected_intent_json: dict[str, Any] = {
        "analysis_type": "count",
        "target_field": "patient_id",
        "filters": [{"field": "active", "value": 1}],
        "conditions": [],
        "parameters": {},
    }

    helper = AIHelper()

    monkeypatch.setattr(
        helper,
        "_ask_llm",
        lambda prompt, _query: json.dumps(expected_intent_json),
    )

    # ------------------------------------------------------------------
    # 2. Stub the DB layer so any SQL executed in the sandbox returns a
    #    predictable DataFrame.  Here we emulate *COUNT(*)* → 5 rows.
    # ------------------------------------------------------------------
    expected_active_count = 5

    def _fake_query_dataframe(
        _sql: str, params: Any | None = None, db_path: str | None = None
    ):  # noqa: ANN401 – stub
        return pd.DataFrame({"result": [expected_active_count]})

    monkeypatch.setattr(db_query, "query_dataframe", _fake_query_dataframe)

    # ------------------------------------------------------------------
    # 3. Pipeline – intent → code → sandbox exec
    # ------------------------------------------------------------------
    intent = helper.get_query_intent(query)
    assert intent.analysis_type == "count"

    code = helper.generate_analysis_code(intent, data_schema={})
    # Basic sanity on generated SQL path
    assert "COUNT(" in code and "FROM" in code

    sandbox_result = run_snippet(code)
    assert sandbox_result == expected_active_count

    # ------------------------------------------------------------------
    # 4. Result interpretation – stub LLM and ensure the function runs.
    # ------------------------------------------------------------------
    monkeypatch.setattr(
        helper,
        "interpret_results",
        lambda _q, _res, visualizations=None: f"There are {_res} active patients in the program.",
    )

    summary = helper.interpret_results(query, sandbox_result)
    assert str(expected_active_count) in summary
