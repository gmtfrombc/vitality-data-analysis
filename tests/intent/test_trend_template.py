from app.utils.ai.code_generator import generate_code
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

    code = generate_code(intent)
    assert code is not None
    assert "strftime('%Y-%m'" in code
    assert "GROUP BY period" in code
