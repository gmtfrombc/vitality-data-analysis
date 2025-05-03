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
    df = pd.DataFrame({"weight": [70, 80]})
    with pytest.raises(ValueError):
        plots.histogram(df, "bmi")


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
