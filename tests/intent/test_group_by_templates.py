"""Tests for GROUP BY support in _build_code_from_intent()."""

from app.ai_helper import AIHelper
from app.utils.query_intent import QueryIntent


def test_group_by_count_gender():  # noqa: D103 – unit test
    helper = AIHelper()

    intent = QueryIntent(
        analysis_type="count",
        target_field="patient_id",
        filters=[],
        conditions=[],
        parameters={"group_by": "gender"},
    )

    code = helper.generate_analysis_code(intent, data_schema={})

    assert "GROUP BY gender" in code
    assert "COUNT(*)" in code
