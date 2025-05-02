"""Golden-query harness executing full pipeline with stubs.

YAML entries (tests/golden/qa.yaml) define:
    • query (natural language)
    • intent (stubbed QueryIntent JSON)
    • expected (scalar or dict) – what the snippet should return

The harness stubs both LLM and DB layers, so tests run offline deterministically.
"""

from __future__ import annotations
from app.utils.sandbox import run_snippet
from app.ai_helper import AIHelper
import db_query
import pytest
import yaml
import pandas as pd

# Standard library imports -------------------------------------------
import sys
from pathlib import Path
import json

# -------------------------------------------------------------------
# Ensure project root on sys.path BEFORE importing project modules
# -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Third-party imports ------------------------------------------------

# Project imports (after path fix)

# -------------------------------------------------------------------
# Additional imports if needed
# -------------------------------------------------------------------

_GOLDEN_PATH = Path(__file__).parent / "qa.yaml"


def _load_cases():  # noqa: D401
    with _GOLDEN_PATH.open("r") as fp:
        return yaml.safe_load(fp)


def _make_fake_df(case):  # noqa: D401
    """Return a DataFrame that will satisfy the generated SQL path for *case*."""
    expected = case["expected"]
    intent = case["intent"]

    # 1. Simple scalar via COUNT/AVG/SUM queries -> single-row result column
    if isinstance(expected, (int, float)):
        if intent["analysis_type"] in {"count", "average", "sum", "min", "max"}:
            return pd.DataFrame({"result": [expected]})

        metric_col = intent["target_field"]
        # For median / variance / std_dev / percent_change: craft numeric series
        if intent["analysis_type"] in {
            "median",
            "variance",
            "std_dev",
            "percent_change",
        }:
            if intent["analysis_type"] == "median":
                values = [28, expected, 32]  # median = expected
            elif intent["analysis_type"] == "variance":
                # create series with variance = expected (sample variance)
                mean = 0
                import math

                # two points variance -> undefined, so use three symmetric points
                offset = math.sqrt(expected)
                values = [mean - offset, mean, mean + offset]
            else:  # std_dev or percent_change
                values = [10, 10 * (1 + expected / 100)]
            return pd.DataFrame({metric_col: values})

    # 2. Dict expected (top_n / group_by) -> column + counts
    if isinstance(expected, dict):
        metric_col = intent["target_field"]
        rows = []
        for key, cnt in expected.items():
            rows.extend([key] * cnt)
        return pd.DataFrame({metric_col: rows})

    raise ValueError("Unsupported expected type in golden case")


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
    results = run_snippet(code)

    assert results == case["expected"]
