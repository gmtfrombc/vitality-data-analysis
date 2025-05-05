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
        (
            QueryIntent(
                analysis_type="median",
                target_field="bmi",
                filters=[],
                conditions=[],
                parameters={},
            ),
            "median()",
        ),
        (
            QueryIntent(
                analysis_type="distribution",
                target_field="bmi",
                filters=[],
                conditions=[],
                parameters={},
            ),
            "histogram",
        ),
        (
            QueryIntent(
                analysis_type="trend",
                target_field="bmi",
                filters=[],
                conditions=[],
                parameters={},
            ),
            "strftime('%Y-%m'",  # trend SQL includes date bucket
        ),
        (
            QueryIntent(
                analysis_type="variance",
                target_field="bmi",
                filters=[],
                conditions=[],
                parameters={},
            ),
            ".var(",  # pandas var call
        ),
        (
            QueryIntent(
                analysis_type="std_dev",
                target_field="bmi",
                filters=[],
                conditions=[],
                parameters={},
            ),
            ".std(",  # pandas std call
        ),
        (
            QueryIntent(
                analysis_type="percent_change",
                target_field="weight",
                group_by=["gender"],
                filters=[],
                conditions=[],
                parameters={},
            ),
            "percent-change by group",  # comment contains phrase
        ),
        (
            QueryIntent(
                analysis_type="top_n",
                target_field="gender",
                filters=[],
                conditions=[],
                parameters={"n": 3},
            ),
            "value_counts().nlargest(3)",  # indicate top-n logic
        ),
        (
            QueryIntent(
                analysis_type="correlation",
                target_field="weight",
                additional_fields=["bmi"],
                filters=[],
                conditions=[],
                parameters={"method": "pearson"},
            ),
            "scatter_plot",  # should include scatter plot function
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
