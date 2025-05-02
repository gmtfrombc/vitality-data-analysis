from app.ai_helper import _build_code_from_intent
from app.utils.query_intent import QueryIntent


def test_average_bmi_template():
    """Average BMI intent should generate code calling .mean()."""

    intent = QueryIntent(
        analysis_type="average",
        target_field="bmi",
        filters=[],
        conditions=[],
        parameters={},
    )

    code = _build_code_from_intent(intent)
    assert code is not None
    assert "avg_value" in code
    assert "results =" in code


def test_activity_status_alias(monkeypatch):
    """Filter on activity_status should be translated to 'active' and 1/0."""

    intent = QueryIntent(
        analysis_type="count",
        target_field="bmi",  # irrelevant for alias test
        filters=[{"field": "activity_status", "value": "active"}],
        conditions=[],
        parameters={},
    )

    code = _build_code_from_intent(intent)
    assert code is not None
    assert "'active'" in code
    assert "== 1" in code
