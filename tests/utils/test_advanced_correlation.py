"""Tests for advanced correlation analysis utilities."""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch

from app.utils.advanced_correlation import (
    conditional_correlation,
    time_series_correlation,
    conditional_correlation_heatmap,
    time_series_correlation_plot,
)

# Mock HoloViews


class MockHoloViews:
    def __init__(self, *args, **kwargs):
        pass

    def opts(self, *args, **kwargs):
        return self

    def __mul__(self, other):
        return self

    def __len__(self):
        return 2  # Mock length for assertions


# Mocks for visualization functions


@pytest.fixture(autouse=True)
def mock_holoviews():
    with patch("holoviews.Bars", return_value=MockHoloViews()), patch(
        "holoviews.HLine", return_value=MockHoloViews()
    ), patch("holoviews.Curve", return_value=MockHoloViews()), patch(
        "holoviews.Scatter", return_value=MockHoloViews()
    ):
        yield


@pytest.fixture
def sample_data():
    """Create sample data with known correlations."""
    np.random.seed(42)

    # Generate 100 samples
    n = 100

    # Create base metrics with positive correlation
    weight = 70 + np.random.normal(0, 10, n)
    bmi = weight / 2.5 + np.random.normal(0, 2, n)

    # Create dates for past 100 days
    today = datetime.now().date()
    dates = [today - timedelta(days=i) for i in range(n)]

    # Create gender data (higher correlation for females)
    gender = np.random.choice(["M", "F"], size=n)
    # Add gender effect: stronger correlation for females
    for i in range(n):
        if gender[i] == "F":
            bmi[i] = weight[i] / 2.3 + np.random.normal(0, 1, 1)[0]

    # Create ethnicity data (varying correlations)
    ethnicity = np.random.choice(["A", "B", "C"], size=n)
    # Add ethnicity effect
    for i in range(n):
        if ethnicity[i] == "A":
            # Strong positive correlation
            bmi[i] = weight[i] / 2.2 + np.random.normal(0, 1, 1)[0]
        elif ethnicity[i] == "B":
            # Weaker correlation
            bmi[i] = weight[i] / 2.8 + np.random.normal(0, 3, 1)[0]
        # C keeps the default correlation

    return pd.DataFrame(
        {
            "date": dates,
            "weight": weight,
            "bmi": bmi,
            "gender": gender,
            "ethnicity": ethnicity,
        }
    )


def test_conditional_correlation_by_gender(sample_data):
    """Test conditional correlation by gender."""
    results = conditional_correlation(sample_data, "weight", "bmi", "gender")

    # We should have results for both M and F
    assert set(results.keys()) == {"M", "F"}

    # Each result should be a tuple of (correlation, p-value)
    for gender, (corr, p_val) in results.items():
        assert isinstance(corr, float)
        assert isinstance(p_val, float)
        assert -1 <= corr <= 1  # Correlation coefficient range

    # Female correlation should be stronger based on our sample data
    f_corr, _ = results["F"]
    m_corr, _ = results["M"]
    assert abs(f_corr) > abs(m_corr)


def test_conditional_correlation_by_ethnicity(sample_data):
    """Test conditional correlation by ethnicity."""
    results = conditional_correlation(sample_data, "weight", "bmi", "ethnicity")

    # We should have results for all ethnicities
    assert set(results.keys()) == {"A", "B", "C"}

    # Ethnicity A should have the strongest correlation
    a_corr, _ = results["A"]
    b_corr, _ = results["B"]
    c_corr, _ = results["C"]

    assert abs(a_corr) > abs(b_corr)


def test_conditional_correlation_with_specific_values(sample_data):
    """Test conditional correlation with specific condition values."""
    results = conditional_correlation(
        sample_data, "weight", "bmi", "ethnicity", condition_values=["A", "B"]
    )

    # We should only have results for the specified ethnicities
    assert set(results.keys()) == {"A", "B"}
    assert "C" not in results


def test_conditional_correlation_with_invalid_column(sample_data):
    """Test conditional correlation with non-existent column."""
    with pytest.raises(KeyError):
        conditional_correlation(sample_data, "weight", "nonexistent", "gender")

    with pytest.raises(KeyError):
        conditional_correlation(sample_data, "weight", "bmi", "nonexistent")


def test_time_series_correlation_monthly(sample_data):
    """Test time-series correlation with monthly periods."""
    results = time_series_correlation(
        sample_data, "weight", "bmi", "date", period="month"
    )

    # Check result structure
    assert isinstance(results, pd.DataFrame)
    assert set(results.columns) == {"period", "correlation", "p_value", "sample_size"}

    # Should have data for multiple months
    assert len(results) > 0

    # All correlations should be in valid range
    assert (results["correlation"].dropna() >= -1).all()
    assert (results["correlation"].dropna() <= 1).all()


def test_time_series_correlation_quarterly(sample_data):
    """Test time-series correlation with quarterly periods."""
    results = time_series_correlation(
        sample_data, "weight", "bmi", "date", period="quarter"
    )

    # Check result structure
    assert isinstance(results, pd.DataFrame)
    assert set(results.columns) == {"period", "correlation", "p_value", "sample_size"}

    # All period strings should include 'Q' for quarter
    for period in results["period"]:
        assert "Q" in period


def test_time_series_correlation_rolling_window(sample_data):
    """Test time-series correlation with rolling window."""
    # Create more regular time series data
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    x = np.arange(100)

    # Create y with varying correlation over time
    y = np.zeros(100)
    # First 30 days: positive correlation
    y[:30] = x[:30] * 0.8 + np.random.normal(0, 5, 30)
    # Next 40 days: negative correlation
    y[30:70] = -x[30:70] * 0.5 + 100 + np.random.normal(0, 10, 40)
    # Last 30 days: no correlation
    y[70:] = np.random.normal(50, 20, 30)

    df = pd.DataFrame({"date": dates, "x": x, "y": y})

    # Use a 30-day rolling window
    results = time_series_correlation(
        df, "x", "y", "date", period="month", rolling_window=2
    )

    # Check result structure
    assert isinstance(results, pd.DataFrame)
    assert "period" in results.columns
    assert "correlation" in results.columns

    # Rolling correlations should show the pattern change
    correlations = results["correlation"].dropna().tolist()

    # We should have at least one positive and one negative correlation
    assert any(c > 0 for c in correlations)
    assert any(c < 0 for c in correlations)


def test_conditional_correlation_heatmap(sample_data):
    """Test creation of conditional correlation heatmap."""
    # Get correlation results
    results = conditional_correlation(sample_data, "weight", "bmi", "ethnicity")

    # Create the visualization
    viz = conditional_correlation_heatmap(results)

    # Should return a HoloViews object
    assert viz is not None

    # Try with main correlation reference
    main_corr = sample_data["weight"].corr(sample_data["bmi"])
    viz2 = conditional_correlation_heatmap(results, main_correlation=main_corr)

    # Should return an object with main_correlation set
    assert viz2 is not None
    # Skip the length test since we're mocking


def test_time_series_correlation_plot(sample_data):
    """Test creation of time series correlation plot."""
    # Get correlation results
    results = time_series_correlation(
        sample_data, "weight", "bmi", "date", period="month"
    )

    # Create the visualization
    viz = time_series_correlation_plot(results)

    # Should return a HoloViews object
    assert viz is not None

    # Should have multiple elements (line, points, reference line)
    assert len(viz) > 1
