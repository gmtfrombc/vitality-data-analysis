"""Golden-query harness executing full pipeline with stubs.

YAML entries (tests/golden/qa.yaml) define:
    • query (natural language)
    • intent (stubbed QueryIntent JSON)
    • expected (scalar or dict) – what the snippet should return

The harness stubs both LLM and DB layers, so tests run offline deterministically.
"""

from __future__ import annotations

# Standard library imports ----------------------------------------------------
from pathlib import Path
import json

# Third-party imports ---------------------------------------------------------
import pytest
import yaml
import pandas as pd

# Project imports -------------------------------------------------------------
import db_query
from app.ai_helper import AIHelper
from app.utils.sandbox import run_snippet

# -------------------------------------------------------------------
# YAML harness helpers
# -------------------------------------------------------------------
_GOLDEN_PATH = Path(__file__).parent / "qa.yaml"

# Define ALIASES needed by _make_fake_df
ALIASES = {
    "test_date": "date",
    "score": "score_value",
    "scorevalue": "score_value",
    "phq9_score": "score_value",
    "phq_score": "score_value",
    "sex": "gender",
    "patient": "patient_id",
    "assessment_type": "assessment_type",
    "score_type": "assessment_type",
    "activity_status": "active",
    "status": "active",
}


def _load_cases():  # noqa: D401
    with _GOLDEN_PATH.open("r") as fp:
        return yaml.safe_load(fp)


def _make_fake_df(case):  # noqa: D401
    """Return a DataFrame that will satisfy the generated SQL path for *case*."""
    expected = case["expected"]
    intent = case["intent"]

    # 1. Handle SCALAR expected results (covers simple aggregates, boolean counts, etc.)
    if isinstance(expected, (int, float)):
        metric_col = intent["target_field"]
        # Simple aggregate or boolean count -> needs a 'result' column
        if intent["analysis_type"] in {"count", "average", "sum", "min", "max"}:
            return pd.DataFrame({"result": [expected]})
        # Other scalar types (median, variance, etc.) -> needs metric column
        elif intent["analysis_type"] in {
            "median",
            "variance",
            "std_dev",
            "percent_change",
        }:
            # (Existing logic for crafting series for these remains the same)
            if intent["analysis_type"] == "median":
                values = [28, expected, 32]  # median = expected
            elif intent["analysis_type"] == "variance":
                mean = 0
                import math

                offset = math.sqrt(expected)
                values = [mean - offset, mean, mean + offset]
            else:  # std_dev or percent_change
                values = [10, 10 * (1 + expected / 100)]
            return pd.DataFrame({metric_col: values})
        else:
            # Fallback for unknown scalar analysis types if any
            return pd.DataFrame({"result": [expected]})

    # 2. Handle DICT expected results (covers group_by, multi-metric, top_n)
    elif isinstance(expected, dict):
        # --- PRIORITY CHECK: GROUP BY --- (intent has group_by list)
        group_by_col = intent.get("group_by")
        if group_by_col and isinstance(group_by_col, list) and len(group_by_col) > 0:
            group_by_field = ALIASES.get(group_by_col[0].lower(), group_by_col[0])
            # Expected structure: {group_key: aggregate_value}
            df_data = {
                group_by_field: list(expected.keys()),
                "result": list(expected.values()),
            }
            return pd.DataFrame(df_data)

        # --- NEXT CHECK: MULTI-METRIC AGGREGATE --- (multiple scalar values in dict)
        elif intent["analysis_type"] in {"average", "sum", "min", "max"} and all(
            isinstance(v, (int, float)) for v in expected.values()
        ):
            # Expected structure: {metric1: value1, metric2: value2}
            return pd.DataFrame({k: [v] for k, v in expected.items()})

        # --- FALLBACK CHECK: TOP_N --- (dict represents value counts)
        elif intent["analysis_type"] == "top_n":
            # Expected structure: {category_value: count}
            metric_col = intent["target_field"]
            rows = []
            for key, cnt in expected.items():
                rows.extend([key] * cnt)
            return pd.DataFrame({metric_col: rows})
        else:
            # Fallback if dict structure doesn't match known patterns
            raise ValueError(
                f"Unsupported DICT expected type/structure for intent: {intent}"
            )

    # --- CATCH ALL --- (if expected is neither scalar nor dict)
    raise ValueError(f"Unsupported expected type in golden case: {type(expected)}")


@pytest.mark.parametrize("case", _load_cases())
def test_golden_query(monkeypatch: pytest.MonkeyPatch, case):  # noqa: D103 – parm test
    helper = AIHelper()

    # 1. Stub LLM for intent
    monkeypatch.setattr(
        helper,
        "_ask_llm",
        lambda prompt, _query, _payload=json.dumps(case["intent"]): _payload,
    )

    # 2. Stub DB query
    fake_df = _make_fake_df(case)
    monkeypatch.setattr(db_query, "query_dataframe", lambda *_a, **_kw: fake_df)

    # 3. Pipeline
    intent = helper.get_query_intent(case["query"])
    code = helper.generate_analysis_code(intent, data_schema={})

    # Debug prints ----
    print(f"\n--- Case: {case.get('name', 'N/A')} ---")
    print(f"Intent Group By: {intent.group_by}")
    print(f"Fake DF:\n{fake_df}")
    print(f"Generated Code:\n{code}")
    # End Debug ------

    results = run_snippet(code)

    assert results == case["expected"]
