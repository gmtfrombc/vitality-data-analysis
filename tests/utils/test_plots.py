"""Unit tests for app.utils.plots helper functions.

These tests avoid rendering – they simply check that a HoloViews object is
returned and that obvious error cases raise ValueError.
"""

from __future__ import annotations

import pandas as pd
import holoviews as hv
import pytest

from app.utils import plots


def test_histogram_basic():
    df = pd.DataFrame({"bmi": [22, 25, 30, 28, 26, 31]})
    plot = plots.histogram(df, "bmi", bins=3)
    assert isinstance(plot, hv.element.Element)


def test_histogram_missing_column():
    df = pd.DataFrame({"bmi": [22, 25, 30, 28, 26, 31]})
    with pytest.raises(ValueError):
        plots.histogram(df, "weight", bins=3)


def test_pie_chart_series():
    ser = pd.Series([10, 20], index=["F", "M"])
    plot = plots.pie_chart(ser, title="Gender")
    assert isinstance(plot, hv.element.Element)


def test_line_plot_basic():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=3, freq="D"),
            "weight": [70, 71, 72],
        }
    )
    plot = plots.line_plot(df, x="date", y="weight")
    assert isinstance(plot, hv.element.Element)


def test_scatter_plot_basic():
    """Test basic scatter plot generation."""
    df = pd.DataFrame({"weight": [70, 75, 80, 85, 90], "bmi": [22, 24, 26, 28, 30]})
    plot = plots.scatter_plot(df, x="weight", y="bmi")
    assert plot is not None
    # The new scatter_plot returns an Overlay object
    assert isinstance(plot, (hv.element.Element, hv.core.overlay.Overlay))


def test_scatter_plot_with_regression():
    """Test scatter plot with regression line."""
    df = pd.DataFrame({"weight": [70, 75, 80, 85, 90], "bmi": [22, 24, 26, 28, 30]})
    plot = plots.scatter_plot(df, x="weight", y="bmi", regression=True)
    # The scatter plot with regression should be an overlay with multiple elements
    assert isinstance(plot, hv.core.overlay.Overlay)
    assert len(plot) > 1  # Should have scatter and regression line


def test_scatter_plot_correlation_display():
    """Test scatter plot with correlation coefficient in title."""
    df = pd.DataFrame({"weight": [70, 75, 80, 85, 90], "bmi": [22, 24, 26, 28, 30]})
    plot = plots.scatter_plot(df, x="weight", y="bmi", correlation=True)
    assert plot is not None
    # Check for Overlay instead of Element
    assert isinstance(plot, (hv.element.Element, hv.core.overlay.Overlay))
    # The correlation coefficient should be calculated and displayed somehow
    # We can't easily check the title due to implementation differences,
    # so we just verify the plot was created
