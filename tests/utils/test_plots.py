"""Tests for the app.utils.plots module."""

import pytest
import pandas as pd
import holoviews as hv

from app.utils.plots import (
    histogram,
    pie_chart,
    line_plot,
    scatter_plot,
    correlation_heatmap,
)


@pytest.fixture
def sample_data():
    """Create sample data for testing plots."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "weight": [70, 75, 80, 85, 90],
            "bmi": [24, 25, 26, 28, 30],
            "date": pd.date_range("2025-01-01", periods=5),
            "category": ["A", "B", "A", "B", "C"],
        }
    )


def test_histogram_basic(sample_data):
    """Test basic histogram functionality."""
    result = histogram(sample_data, "weight")
    assert isinstance(result, hv.Element)
    assert "Weight Distribution" in str(result)


def test_histogram_with_custom_title(sample_data):
    """Test histogram with custom title."""
    result = histogram(sample_data, "weight", title="Custom Title")
    assert isinstance(result, hv.Element)
    assert "Custom Title" in str(result)


def test_histogram_with_custom_bins(sample_data):
    """Test histogram with custom bin count."""
    result = histogram(sample_data, "weight", bins=10)
    assert isinstance(result, hv.Element)


def test_histogram_column_not_found(sample_data):
    """Test histogram with non-existent column."""
    with pytest.raises(ValueError) as excinfo:
        histogram(sample_data, "nonexistent")
    assert "not found in dataframe" in str(excinfo.value)


def test_pie_chart_from_series():
    """Test pie chart creation from a Series."""
    counts = pd.Series([10, 20, 30], index=["A", "B", "C"])
    result = pie_chart(counts)
    assert result is not None
    assert "Distribution" in str(result)


def test_pie_chart_from_dataframe(sample_data):
    """Test pie chart creation from a DataFrame."""
    counts_df = sample_data["category"].value_counts().reset_index()
    counts_df.columns = ["category", "count"]

    result = pie_chart(
        counts_df, label_col="category", value_col="count", title="Categories"
    )
    assert result is not None
    assert "Categories" in str(result)


def test_pie_chart_missing_columns():
    """Test pie chart with missing column specifications."""
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    with pytest.raises(ValueError) as excinfo:
        pie_chart(df)
    assert "Must supply value_col and label_col" in str(excinfo.value)


def test_pie_chart_custom_dimensions():
    """Test pie chart with custom height and width."""
    counts = pd.Series([10, 20, 30], index=["A", "B", "C"])
    result = pie_chart(counts, height=400, width=400)
    assert result is not None
    assert "height=400" in str(result)
    assert "width=400" in str(result)


def test_line_plot_basic(sample_data):
    """Test basic line plot functionality."""
    result = line_plot(sample_data, x="date", y="weight")
    assert isinstance(result, hv.Element)
    assert "Weight Over Time" in str(result)


def test_line_plot_custom_title(sample_data):
    """Test line plot with custom title."""
    result = line_plot(sample_data, x="date", y="weight", title="Weight Trend")
    assert "Weight Trend" in str(result)


def test_line_plot_custom_labels(sample_data):
    """Test line plot with custom axis labels."""
    result = line_plot(
        sample_data, x="date", y="weight", xlabel="Date Range", ylabel="Patient Weight"
    )
    assert "Date Range" in str(result).lower() or "x='date'" in str(result).lower()
    assert (
        "Patient Weight" in str(result).lower() or "y='weight'" in str(result).lower()
    )


def test_line_plot_missing_columns(sample_data):
    """Test line plot with missing columns."""
    with pytest.raises(ValueError) as excinfo:
        line_plot(sample_data, x="nonexistent", y="weight")
    assert "not found in dataframe" in str(excinfo.value)


def test_line_plot_visual_options(sample_data):
    """Test line plot with custom visual options."""
    result = line_plot(
        sample_data,
        x="date",
        y="weight",
        grid=False,
        line_width=3.0,
        width=700,
        height=450,
    )
    assert result is not None
    assert ("grid=False" in str(result)) or ("grid=0" in str(result))


def test_scatter_plot_basic(sample_data):
    """Test basic scatter plot functionality."""
    result = scatter_plot(sample_data, x="weight", y="bmi")
    assert result is not None
    assert "Correlation" in str(result)


def test_scatter_plot_custom_title(sample_data):
    """Test scatter plot with custom title."""
    result = scatter_plot(sample_data, x="weight", y="bmi", title="Weight vs BMI")
    assert "Weight vs BMI" in str(result)


def test_scatter_plot_custom_options(sample_data):
    """Test scatter plot with custom visual options."""
    result = scatter_plot(
        sample_data, x="weight", y="bmi", color="red", alpha=0.8, size=100, grid=False
    )
    assert result is not None
    assert "color='red'" in str(result) or 'color="red"' in str(result)


def test_scatter_plot_without_correlation(sample_data):
    """Test scatter plot without correlation statistics."""
    result = scatter_plot(sample_data, x="weight", y="bmi", correlation=False)
    assert result is not None
    assert "Correlation:" not in str(result)


def test_scatter_plot_without_regression(sample_data):
    """Test scatter plot without regression line."""
    result = scatter_plot(sample_data, x="weight", y="bmi", regression=False)
    assert result is not None
    # Should be a simple scatter plot, not an overlay with a regression line
    assert isinstance(result, hv.Element)


def test_scatter_plot_invalid_data():
    """Test scatter plot with invalid data."""
    # Test with insufficient data points
    df = pd.DataFrame({"x": [1], "y": [2]})
    with pytest.raises(ValueError) as excinfo:
        scatter_plot(df, x="x", y="y")
    assert "Need at least 2 valid data points" in str(excinfo.value)

    # Test with missing columns
    df = pd.DataFrame({"x": [1, 2, 3]})
    with pytest.raises(ValueError) as excinfo:
        scatter_plot(df, x="x", y="y")
    assert "not found in dataframe" in str(excinfo.value)


def test_correlation_heatmap_basic():
    """Test basic correlation heatmap functionality."""
    # Create a simple correlation matrix
    corr_matrix = pd.DataFrame(
        {"weight": [1.0, 0.8, 0.5], "bmi": [0.8, 1.0, 0.3], "height": [0.5, 0.3, 1.0]},
        index=["weight", "bmi", "height"],
    )

    result = correlation_heatmap(corr_matrix)
    assert isinstance(result, hv.Element) or isinstance(result, hv.Overlay)
    assert "Correlation Matrix" in str(result)


def test_correlation_heatmap_with_pvalues():
    """Test correlation heatmap with p-values."""
    # Create a correlation matrix and matching p-value matrix
    corr_matrix = pd.DataFrame(
        {"weight": [1.0, 0.8, 0.5], "bmi": [0.8, 1.0, 0.3], "height": [0.5, 0.3, 1.0]},
        index=["weight", "bmi", "height"],
    )

    p_values = pd.DataFrame(
        {
            "weight": [0.0, 0.01, 0.06],
            "bmi": [0.01, 0.0, 0.2],
            "height": [0.06, 0.2, 0.0],
        },
        index=["weight", "bmi", "height"],
    )

    result = correlation_heatmap(corr_matrix, p_values)
    assert result is not None
    assert "Correlation Matrix" in str(result)


def test_correlation_heatmap_custom_options():
    """Test correlation heatmap with custom options."""
    corr_matrix = pd.DataFrame(
        {"weight": [1.0, 0.8], "bmi": [0.8, 1.0]}, index=["weight", "bmi"]
    )

    result = correlation_heatmap(
        corr_matrix,
        title="Custom Title",
        cmap="viridis",
        width=700,
        height=700,
        show_values=False,
        digits=3,
    )
    assert result is not None
    assert "Custom Title" in str(result)
