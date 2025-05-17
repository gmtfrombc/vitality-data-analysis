from app.ai_helper import _build_code_from_intent
from app.utils.query_intent import QueryIntent


def test_trend_template_sql():
    """Trend intent should generate monthly bucket SQL with strftime."""

    intent = QueryIntent(
        analysis_type="trend",
        target_field="bmi",
        filters=[],
        conditions=[],
        parameters={},
    )

    code = _build_code_from_intent(intent)
    assert code is not None
    assert "strftime('%Y-%m'" in code
    assert "GROUP BY month" in code
