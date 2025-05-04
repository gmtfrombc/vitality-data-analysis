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
import numpy as np

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
            elif intent["analysis_type"] == "std_dev":
                # For standard deviation, create values that will produce the expected std dev (5.2)
                # Using the correct formula for a 2-point dataset: std = |x1-x2|/sqrt(2)
                # So if we want std=5.2, we need |x1-x2| = 5.2*sqrt(2)
                import math

                separation = expected * math.sqrt(2)
                mean = 30  # arbitrary mean
                values = [mean - separation / 2, mean + separation / 2]
            else:  # percent_change
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

        # --- CORRELATION ANALYSIS --- (dict with correlation_coefficient)
        elif (
            intent["analysis_type"] == "correlation"
            and "correlation_coefficient" in expected
        ):
            # Expected structure: {'correlation_coefficient': value}
            # Create a DataFrame with 5 points that have the expected correlation

            # Get the correlation coefficient
            corr = expected["correlation_coefficient"]

            # Target fields for correlation
            metric_x = intent["target_field"]
            metric_y = (
                intent["additional_fields"][0] if intent["additional_fields"] else "bmi"
            )

            # Create x values
            x = np.array([70, 80, 90, 100, 110])

            # Create y values that have the expected correlation with x
            # Using the fact that y = ax + b + noise gives us a correlation depending on
            # the amount of noise
            a = 0.3  # slope
            b = 10  # intercept

            # For perfect correlation
            y_perfect = a * x + b

            # Add noise to achieve the target correlation
            if corr < 1.0:
                # Calculate noise magnitude needed to achieve target correlation
                noise_std = np.std(y_perfect) * np.sqrt((1 - corr**2) / corr**2)
                np.random.seed(42)  # For reproducibility
                noise = np.random.normal(0, noise_std, len(x))
                y = y_perfect + noise
            else:
                y = y_perfect

            # Create dataframe with columns matching the expected query structure
            return pd.DataFrame({metric_x: x, metric_y: y})

        # --- TREND ANALYSIS --- (dict with time series data)
        elif intent["analysis_type"] == "trend" and intent.get("time_range"):
            # Expected structure: {time_key: aggregate_value}
            # Create a dataframe with month and avg_value columns
            df_data = {
                "month": list(expected.keys()),
                "avg_value": list(expected.values()),
            }
            return pd.DataFrame(df_data)

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

    # Special case for correlation tests - we just check that we got a correlation coefficient
    # close to the expected value without requiring an exact match
    if case.get("name") == "bmi_weight_correlation":
        # Check that we didn't get an error
        assert (
            "error" not in results
        ), f"Got error in correlation results: {results.get('error')}"

        # Check that we got a correlation coefficient close to the expected value
        assert (
            "correlation_coefficient" in results
        ), "Missing correlation_coefficient in results"
        expected_corr = case["expected"]["correlation_coefficient"]
        actual_corr = results["correlation_coefficient"]

        # Allow some tolerance for floating point differences
        assert np.isclose(
            actual_corr, expected_corr, atol=0.1
        ), f"Correlation coefficient {actual_corr} not close to expected {expected_corr}"

        # Skip the exact equality check for correlation tests
        return

    # Use numpy.isclose for floating point comparisons
    # This handles percent change and other numeric results that might have small differences
    if isinstance(results, float) and isinstance(case["expected"], (int, float)):
        assert np.isclose(
            results, case["expected"], rtol=1e-5, atol=1e-8
        ), f"Result {results} not close to expected {case['expected']}"
        return

    assert results == case["expected"]
