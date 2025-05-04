import pandas as pd
import holoviews as hv

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
            "date": pd.date_range("2025-01-01", periods=6, freq="ME"),
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


# New tests to improve coverage


def test_auto_visualize_none_data():
    """Test that None data returns None."""
    intent = _intent()
    result = auto_visualize(None, intent)
    assert result is None


def test_auto_visualize_scalar_data():
    """Test that scalar data returns None."""
    intent = _intent()
    result = auto_visualize(42, intent)
    assert result is None

    # Also test float scalar
    result = auto_visualize(3.14, intent)
    assert result is None


def test_auto_visualize_series_input():
    """Test that Series input is handled correctly."""
    series = pd.Series([25, 30, 27, 28, 31, 29], name="bmi")
    intent = _intent()
    viz = auto_visualize(series, intent)
    assert viz is not None, "Expected a plot from Series input"
    assert "bmi" in str(viz), "Expected 'bmi' in plot title or labels"


def test_auto_visualize_empty_dataframe():
    """Test that empty DataFrame returns None."""
    df = pd.DataFrame(columns=["bmi", "weight"])
    intent = _intent()
    result = auto_visualize(df, intent)
    assert result is None


def test_correlation_with_visualization_key():
    """Test correlation analysis with dict containing visualization key."""
    # Create a visualization to include in the dict
    df = pd.DataFrame({"x": [1, 2, 3], "y": [3, 4, 5]})
    plot = hv.Scatter(df)

    # Create a dict with a visualization key
    data = {"correlation": 0.95, "method": "pearson", "visualization": plot}

    intent = _intent(
        analysis_type="correlation", target_field="x", additional_fields=["y"]
    )

    result = auto_visualize(data, intent)
    assert result is not None
    assert result is plot, "Expected the visualization from the dict"


def test_correlation_with_dataframe_columns():
    """Test correlation analysis with DataFrame columns."""
    df = pd.DataFrame({"weight": [70, 75, 80, 85, 90], "bmi": [24, 25, 26, 28, 30]})

    intent = _intent(
        analysis_type="correlation", target_field="weight", additional_fields=["bmi"]
    )

    result = auto_visualize(df, intent)
    assert result is not None
    assert isinstance(result, hv.Overlay), f"Expected hv.Overlay, got {type(result)}"


def test_correlation_with_dict_metrics():
    """Test correlation analysis with dict containing metrics as keys."""
    data = {"weight": [70, 75, 80, 85, 90], "bmi": [24, 25, 26, 28, 30]}

    intent = _intent(
        analysis_type="correlation", target_field="weight", additional_fields=["bmi"]
    )

    result = auto_visualize(data, intent)
    assert result is not None
    assert isinstance(result, hv.Overlay), f"Expected hv.Overlay, got {type(result)}"


def test_distribution_fallback_to_numeric():
    """Test distribution analysis fallback to first numeric column."""
    df = pd.DataFrame(
        {
            "patient_id": [1, 2, 3, 4, 5],
            "weight": [70, 75, 80, 85, 90],
            "bmi": [24, 25, 26, 28, 30],
        }
    )

    # Intent with target_field that doesn't exist in DataFrame
    intent = _intent(analysis_type="distribution", target_field="nonexistent_field")

    result = auto_visualize(df, intent)
    assert result is not None, "Expected fallback to first numeric column"


def test_change_analysis():
    """Test change/trend analysis with datetime and metric columns."""
    df = pd.DataFrame(
        {"date": pd.date_range("2025-01-01", periods=5), "score": [80, 82, 85, 83, 88]}
    )

    intent = _intent(analysis_type="change", target_field="score")

    result = auto_visualize(df, intent)
    assert result is not None
    assert isinstance(result, hv.Element)
    assert result.kdims[0].name == "date"
    assert result.vdims[0].name == "score"


def test_fallback_with_categorical_and_numeric():
    """Test fallback case with one categorical and one numeric column."""
    df = pd.DataFrame(
        {"gender": ["F", "M", "F", "M", "F"], "count": [10, 15, 12, 18, 9]}
    )

    # Use a non-matching intent type
    intent = _intent(analysis_type="count", target_field="patient_id")

    result = auto_visualize(df, intent)
    assert result is not None
    assert isinstance(result, hv.Element)
    assert result.__class__.__name__.lower().endswith("bars")


def test_unsupported_data_type():
    """Test that unsupported data types return None."""
    intent = _intent()

    # Test with list
    result = auto_visualize([1, 2, 3, 4, 5], intent)
    assert result is None

    # Test with dict that doesn't match any heuristic
    result = auto_visualize({"key1": "value1", "key2": "value2"}, intent)
    assert result is None


def test_no_suitable_visualization():
    """Test a case where no suitable visualization is found."""
    # DataFrame with mixed data but no valid visualization matches
    df = pd.DataFrame({"id": [1, 2, 3], "category": ["A", "B", "C"]})

    # Use intent that won't match any visualization heuristic
    intent = _intent(
        analysis_type="distribution",  # Valid type
        target_field="non_existent_field",  # Field not in data
    )

    # Monkeypatch the df so no numeric columns are detected
    # This will cause the fallback to fail
    df._old_select_dtypes = df.select_dtypes
    df.select_dtypes = lambda *args, **kwargs: pd.DataFrame()

    result = auto_visualize(df, intent)
    assert result is None
