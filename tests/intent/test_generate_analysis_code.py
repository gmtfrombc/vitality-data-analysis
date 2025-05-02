"""Tests for AIHelper.generate_analysis_code() covering the new SQL templates."""

import pytest

from app.ai_helper import AIHelper
from app.utils.query_intent import QueryIntent


@pytest.fixture(scope="module")
def helper() -> AIHelper:  # noqa: D401 - fixture
    """Return a fresh *AIHelper* instance for code-generation tests."""
    return AIHelper()


@pytest.mark.parametrize(
    "intent, expected_fragment",
    [
        (
            QueryIntent(
                analysis_type="average",
                target_field="bmi",
                filters=[],
                conditions=[],
                parameters={},
            ),
            "AVG(bmi)",
        ),
        (
            QueryIntent(
                analysis_type="count",
                target_field="bmi",
                filters=[],
                conditions=[],
                parameters={},
            ),
            "COUNT(*)",
        ),
    ],
)
def test_sql_aggregate_templates(
    helper: AIHelper, intent: QueryIntent, expected_fragment: str
):  # noqa: D103 - test
    code = helper.generate_analysis_code(intent, data_schema="")

    # Ensure the SQL aggregate fragment we expect is in the generated snippet
    assert expected_fragment in code
    # Basic sanity: generated snippet should include SELECT and FROM clauses
    assert "SELECT" in code and "FROM" in code
