from __future__ import annotations

"""Happy-path integration test verifying the average-weight pipeline.

This extends the smoke suite so that we now cover:
1. Natural-language query → intent JSON (stubbed LLM)
2. Deterministic code generation (AVG aggregate path)
3. Sandbox execution yielding the expected scalar result.

The real OpenAI and SQLite calls are monkey-patched so the test runs offline
and deterministically.
"""

import json
import pandas as pd
import pytest

import db_query
from app.ai_helper import AIHelper
from app.utils.sandbox import run_snippet


@pytest.mark.smoke
def test_end_to_end_average_weight(
    monkeypatch: pytest.MonkeyPatch,
):  # noqa: D103 – smoke test
    query = "What is the average weight of patients?"

    # ------------------------------------------------------------------
    # 1. Stub the LLM call used by *get_query_intent*
    # ------------------------------------------------------------------
    expected_intent_json = {
        "analysis_type": "average",
        "target_field": "weight",
        "filters": [],
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
    #    predictable DataFrame with a single AVG result.
    # ------------------------------------------------------------------
    expected_average_weight = 76.5

    def _fake_query_dataframe(
        _sql: str, params=None, db_path=None
    ):  # noqa: ANN001 – stub
        return pd.DataFrame({"result": [expected_average_weight]})

    monkeypatch.setattr(db_query, "query_dataframe", _fake_query_dataframe)

    # ------------------------------------------------------------------
    # 3. Pipeline – intent → code → sandbox exec
    # ------------------------------------------------------------------
    intent = helper.get_query_intent(query)
    assert intent.analysis_type == "average"

    code = helper.generate_analysis_code(intent, data_schema={})
    # Sanity check that AVG aggregate path was chosen
    assert "AVG(" in code and "FROM" in code

    sandbox_result = run_snippet(code)
    assert sandbox_result == pytest.approx(expected_average_weight)
