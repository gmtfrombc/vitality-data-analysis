from app.utils.ai.code_generator import generate_code
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

    code = generate_code(intent)
    assert code is not None
    assert "AVG(bmi)" in code
    assert "SELECT" in code


def test_activity_status_alias(monkeypatch):
    """Filter on activity_status should be translated to 'active' and 1/0."""

    intent = QueryIntent(
        analysis_type="count",
        target_field="bmi",  # irrelevant for alias test
        filters=[{"field": "activity_status", "value": "active"}],
        conditions=[],
        parameters={},
    )

    code = generate_code(intent)
    assert code is not None
    assert "active" in code
    assert "= 1" in code
