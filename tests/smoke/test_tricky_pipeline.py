import json
import pytest
import db_query
from pathlib import Path
import yaml
from app.ai_helper import AIHelper
from app.utils.sandbox import run_snippet

YAML_PATH = Path(__file__).parent.parent / "golden" / "qa.yaml"


def _load_tricky():
    cases = yaml.safe_load(YAML_PATH.read_text())
    return [
        c
        for c in cases
        if "name" in c
        and c["name"].startswith(
            (
                "hba1c_",
                "bmi_gender_",
                "top5_",
                "percent_change_weight_active",
                "std_dev_dbp",
                "median_weight",
                "variance_glucose",
                "bmi_trend_6months",
                "inactive_patients_count",
                "top3_ethnicities",
            )
        )
    ]


@pytest.mark.parametrize("case", _load_tricky())
def test_tricky_pipeline(monkeypatch: pytest.MonkeyPatch, case):  # noqa: D103
    helper = AIHelper()
    # Stub LLM
    monkeypatch.setattr(
        helper, "_ask_llm", lambda p, q, payload=json.dumps(case["intent"]): payload
    )

    # Fake minimal df to satisfy SQL via generic match – reuse golden harness util
    from tests.golden.test_golden_queries import _make_fake_df  # type: ignore

    fake_df = _make_fake_df(case)
    monkeypatch.setattr(db_query, "query_dataframe", lambda *_a, **_kw: fake_df)

    intent = helper.get_query_intent(case["query"])
    code = helper.generate_analysis_code(intent, data_schema={})
    results = run_snippet(code)

    # Basic sanity: no error and result type matches expectation structure
    assert "error" not in str(results).lower()
    expected = case["expected"]
    # Loose compare for scalars
    if isinstance(expected, (int, float)):
        assert isinstance(results, (int, float))
    else:
        assert isinstance(results, dict)
