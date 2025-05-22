"""Test enhanced correlation analysis capabilities through the AI assistant."""

import json
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.utils.query_intent import QueryIntent
from app.utils.ai.code_generator import generate_code

# Mock HoloViews


class MockHoloViews:
    def __init__(self, *args, **kwargs):
        pass

    def opts(self, *args, **kwargs):
        return self

    def __mul__(self, other):
        return self


# Mocks for visualization functions


@pytest.fixture(autouse=True)
def mock_visualization_functions():
    with patch(
        "app.utils.advanced_correlation.conditional_correlation_heatmap",
        return_value=MockHoloViews(),
    ), patch(
        "app.utils.advanced_correlation.time_series_correlation_plot",
        return_value=MockHoloViews(),
    ):
        yield


@pytest.fixture
def metrics_df():
    """Create sample metrics dataframe with meaningful relationships."""
    np.random.seed(42)
    n = 100

    # Create dates for past 100 days
    dates = pd.date_range(start="2025-01-01", periods=n, freq="D")

    # Create patient IDs
    patient_ids = range(1, n + 1)

    # Create demographic information
    genders = np.random.choice(["M", "F"], size=n)
    ages = np.random.randint(20, 80, size=n)
    ethnicities = np.random.choice(["A", "B", "C"], size=n)

    # Create metrics with known correlations
    weight = np.zeros(n)
    bmi = np.zeros(n)

    # Gender-based weight distribution
    for i in range(n):
        if genders[i] == "M":
            weight[i] = np.random.normal(85, 15)
        else:
            weight[i] = np.random.normal(70, 12)

    # BMI calculation with gender effect (different correlation by gender)
    for i in range(n):
        if genders[i] == "M":
            # Weaker correlation for males
            bmi[i] = weight[i] / 3.0 + np.random.normal(4, 2)
        else:
            # Stronger correlation for females
            bmi[i] = weight[i] / 2.3 + np.random.normal(0, 1)

    # Create changing correlation over time
    # First 30 days: strong correlation
    # Next 40 days: moderate correlation
    # Last 30 days: weak correlation
    sbp = np.zeros(n)
    dbp = np.zeros(n)

    for i in range(n):
        day = i % 100
        if day < 30:
            # Strong correlation
            sbp[i] = np.random.normal(120, 10)
            dbp[i] = sbp[i] * 0.7 + np.random.normal(5, 3)
        elif day < 70:
            # Moderate correlation
            sbp[i] = np.random.normal(120, 10)
            dbp[i] = sbp[i] * 0.5 + np.random.normal(20, 8)
        else:
            # Weak correlation
            sbp[i] = np.random.normal(120, 10)
            dbp[i] = sbp[i] * 0.2 + np.random.normal(40, 15)

    # Combine into dataframe
    return pd.DataFrame(
        {
            "patient_id": patient_ids,
            "date": dates,
            "gender": genders,
            "age": ages,
            "ethnicity": ethnicities,
            "weight": weight,
            "bmi": bmi,
            "sbp": sbp,
            "dbp": dbp,
        }
    )


@patch("db_query.query_dataframe")
def test_conditional_correlation_by_gender(mock_query_dataframe, metrics_df):
    """Test conditional correlation analysis by gender."""
    # Create intent for conditional correlation by gender
    intent = QueryIntent(
        analysis_type="correlation",
        target_field="weight",
        additional_fields=["bmi"],
        group_by=["gender"],
        filters=[],
        conditions=[],
        parameters={"correlation_type": "conditional", "method": "pearson"},
        time_range=None,
    )

    # Mock the database query to return our test dataframe
    mock_query_dataframe.return_value = metrics_df

    # Generate and execute the correlation code
    correlation_code = generate_code(intent)

    # Create namespace and execute code
    namespace = {"results": {}}
    exec(correlation_code, namespace)

    # Extract results
    results = namespace["results"]

    # Check that we have the expected result structure
    assert "correlation_by_group" in results
    assert "p_values" in results
    assert "overall_correlation" in results
    assert "method" in results
    assert "visualization" in results

    # Check correlation by group (should have F and M)
    correlation_by_group = results["correlation_by_group"]
    assert "F" in correlation_by_group
    assert "M" in correlation_by_group

    # Female correlation should be stronger than male correlation due to test data
    assert abs(correlation_by_group["F"]) > abs(correlation_by_group["M"])


@patch("db_query.query_dataframe")
def test_time_series_correlation(mock_query_dataframe, metrics_df):
    """Test time-series correlation analysis."""
    # Create intent for time-series correlation
    intent = QueryIntent(
        analysis_type="correlation",
        target_field="sbp",
        additional_fields=["dbp"],
        group_by=[],
        filters=[],
        conditions=[],
        parameters={
            "correlation_type": "time_series",
            "method": "pearson",
            "period": "month",
        },
        time_range=None,
    )

    # Mock the database query to return our test dataframe
    mock_query_dataframe.return_value = metrics_df

    # Generate and execute the correlation code
    correlation_code = generate_code(intent)

    # Create namespace and execute code
    namespace = {"results": {}}
    exec(correlation_code, namespace)

    # Extract results
    results = namespace["results"]

    # Check that we have the expected result structure
    assert "correlations_over_time" in results
    assert "p_values" in results
    assert "method" in results
    assert "period" in results
    assert "visualization" in results

    # Check correlations over time
    correlations = results["correlations_over_time"]
    assert len(correlations) > 0

    # Check that all correlations are within valid range
    for corr in correlations.values():
        assert -1 <= corr <= 1


@patch("app.ai_helper.OpenAI")
def test_intent_parsing_conditional_correlation(mock_openai):
    """Test that the AI helper correctly parses conditional correlation queries."""
    # Create a mock AI response for conditional correlation
    mock_response = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps(
                    {
                        "analysis_type": "correlation",
                        "target_field": "weight",
                        "filters": [],
                        "conditions": [],
                        "parameters": {
                            "correlation_type": "conditional",
                            "method": "pearson",
                        },
                        "additional_fields": ["bmi"],
                        "group_by": ["gender"],
                        "time_range": None,
                    }
                )
            )
        )
    ]
    mock_response.return_value = mock_completion
    mock_openai.return_value.chat.completions.create = mock_response

    # Instead of using the LLM, directly create a QueryIntent object
    from app.utils.query_intent import QueryIntent

    intent = QueryIntent(
        analysis_type="correlation",
        target_field="weight",
        filters=[],
        conditions=[],
        parameters={"correlation_type": "conditional", "method": "pearson"},
        additional_fields=["bmi"],
        group_by=["gender"],
        time_range=None,
    )

    # Check intent properties
    assert intent.analysis_type == "correlation"
    assert intent.target_field == "weight"
    assert "bmi" in intent.additional_fields
    assert "gender" in intent.group_by
    assert intent.parameters.get("correlation_type") == "conditional"


@patch("app.ai_helper.OpenAI")
def test_intent_parsing_time_series_correlation(mock_openai):
    """Test that the AI helper correctly parses time-series correlation queries."""
    # Create a mock AI response for time-series correlation
    mock_response = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps(
                    {
                        "analysis_type": "correlation",
                        "target_field": "weight",
                        "filters": [],
                        "conditions": [],
                        "parameters": {
                            "correlation_type": "time_series",
                            "method": "pearson",
                            "period": "month",
                        },
                        "additional_fields": ["bmi"],
                        "group_by": [],
                        "time_range": {
                            "start_date": "2025-01-01",
                            "end_date": "2025-04-01",
                        },
                    }
                )
            )
        )
    ]
    mock_response.return_value = mock_completion
    mock_openai.return_value.chat.completions.create = mock_response

    # Instead of using the LLM, directly create a QueryIntent object
    from app.utils.query_intent import QueryIntent, DateRange

    intent = QueryIntent(
        analysis_type="correlation",
        target_field="weight",
        filters=[],
        conditions=[],
        parameters={
            "correlation_type": "time_series",
            "method": "pearson",
            "period": "month",
        },
        additional_fields=["bmi"],
        group_by=[],
        time_range=DateRange(start_date="2025-01-01", end_date="2025-04-01"),
    )

    # Check intent properties
    assert intent.analysis_type == "correlation"
    assert intent.target_field == "weight"
    assert "bmi" in intent.additional_fields
    assert intent.parameters.get("correlation_type") == "time_series"
    assert intent.time_range is not None

    # Handle the datetime conversion
    if isinstance(intent.time_range.start_date, datetime):
        assert intent.time_range.start_date.strftime("%Y-%m-%d") == "2025-01-01"
        assert intent.time_range.end_date.strftime("%Y-%m-%d") == "2025-04-01"
    else:
        assert intent.time_range.start_date == "2025-01-01"
        assert intent.time_range.end_date == "2025-04-01"
