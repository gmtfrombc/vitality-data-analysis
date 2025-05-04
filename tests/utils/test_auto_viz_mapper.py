import pandas as pd

from app.utils.auto_viz_mapper import auto_visualize
from app.utils.query_intent import QueryIntent


def _intent(**kwargs):
    """Helper to build a minimal QueryIntent with overrides."""
    base = {
        "analysis_type": "distribution",
        "target_field": "bmi",
    }
    base.update(kwargs)
    return QueryIntent.model_validate(base)  # type: ignore[arg-type]


def test_histogram_mapping_returns_plot():
    df = pd.DataFrame({"bmi": [25, 30, 27, 28, 31, 29]})
    viz = auto_visualize(df, _intent())
    assert viz is not None, "Expected a histogram plot for distribution analysis"


def test_line_plot_for_trend():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=6, freq="M"),
            "weight": [80, 79, 78, 77, 76, 75],
        }
    )
    intent = _intent(analysis_type="trend", target_field="weight")
    viz = auto_visualize(df, intent)
    assert viz is not None and viz.kdims[0].name == "date"


def test_bar_chart_for_groupby():
    df = pd.DataFrame({"gender": ["F", "M", "F"], "avg_bmi": [29.1, 30.2, 28.7]})
    intent = _intent(
        analysis_type="average", target_field="avg_bmi", group_by=["gender"]
    )
    viz = auto_visualize(df, intent)
    assert viz is not None and viz.__class__.__name__.lower().endswith("bars")
