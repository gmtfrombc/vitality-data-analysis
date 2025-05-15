"""Advanced correlation analysis utilities.

This module extends the basic correlation analysis with:
1. Conditional correlations (correlations within specific subgroups)
2. Time-series correlations (correlations over time periods)
3. Enhanced visualization options
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

import holoviews as hv

from app.utils.metrics import assert_columns


def conditional_correlation(
    df: pd.DataFrame,
    metric_x: str,
    metric_y: str,
    condition_field: str,
    condition_values: Optional[List[str]] = None,
    method: Literal["pearson", "spearman", "kendall"] = "pearson",
) -> Dict[str, Tuple[float, float]]:
    """Calculate correlation coefficients between two metrics for each value of a categorical variable.

    Parameters
    ----------
    df : pandas.DataFrame
        Source data containing both metrics and the condition field.
    metric_x : str
        First metric column name.
    metric_y : str
        Second metric column name to correlate with first metric.
    condition_field : str
        Categorical column to split data by (e.g., 'gender', 'ethnicity').
    condition_values : List[str], optional
        Specific values of condition_field to analyze. If None, all values are used.
    method : {"pearson", "spearman", "kendall"}, default "pearson"
        Correlation method to use.

    Returns
    -------
    Dict[str, Tuple[float, float]]
        Dictionary mapping each condition value to a tuple of (correlation coefficient, p-value).
    """
    # Check if columns exist
    assert_columns(df, metric_x, metric_y, condition_field)

    # Get clean data (drop rows with NaN in relevant columns)
    clean_df = df.dropna(subset=[metric_x, metric_y, condition_field])

    if len(clean_df) < 2:
        raise ValueError("Insufficient data after removing missing values")

    # Get unique values in condition field if not specified
    if condition_values is None:
        condition_values = clean_df[condition_field].unique().tolist()

    # Calculate correlation for each condition value
    results = {}
    for value in condition_values:
        # Filter data for this condition value
        subset = clean_df[clean_df[condition_field] == value]

        # Skip if insufficient data
        if len(subset) < 3:
            results[value] = (float("nan"), float("nan"))
            continue

        # Calculate correlation based on method
        if method == "pearson":
            r, p = stats.pearsonr(subset[metric_x], subset[metric_y])
        elif method == "spearman":
            r, p = stats.spearmanr(subset[metric_x], subset[metric_y])
        elif method == "kendall":
            r, p = stats.kendalltau(subset[metric_x], subset[metric_y])
        else:
            raise ValueError(f"Unsupported correlation method: {method}")

        results[value] = (float(r), float(p))

    return results


def time_series_correlation(
    df: pd.DataFrame,
    metric_x: str,
    metric_y: str,
    date_column: str = "date",
    period: Literal["month", "quarter", "year"] = "month",
    rolling_window: Optional[int] = None,
    method: Literal["pearson", "spearman", "kendall"] = "pearson",
) -> pd.DataFrame:
    """Calculate correlations between two metrics over time periods.

    Parameters
    ----------
    df : pandas.DataFrame
        Source data containing both metrics and the date column.
    metric_x : str
        First metric column name.
    metric_y : str
        Second metric column name to correlate with first metric.
    date_column : str, default "date"
        Column containing date information.
    period : {"month", "quarter", "year"}, default "month"
        Time period to group data by.
    rolling_window : int, optional
        If provided, calculate rolling correlations over this many periods.
    method : {"pearson", "spearman", "kendall"}, default "pearson"
        Correlation method to use.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns: period, correlation, p_value, sample_size
    """
    # Check if columns exist
    assert_columns(df, metric_x, metric_y, date_column)

    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_dtype(df[date_column]):
        df = df.copy()
        df[date_column] = pd.to_datetime(df[date_column])

    # Get clean data (drop rows with NaN in relevant columns)
    clean_df = df.dropna(subset=[metric_x, metric_y, date_column])

    if len(clean_df) < 3:
        raise ValueError("Insufficient data after removing missing values")

    # Create period column based on specified period
    clean_df = clean_df.copy()
    if period == "month":
        clean_df["period"] = clean_df[date_column].dt.strftime("%Y-%m")
    elif period == "quarter":
        clean_df["period"] = clean_df[date_column].dt.to_period("Q").astype(str)
    elif period == "year":
        clean_df["period"] = clean_df[date_column].dt.year.astype(str)
    else:
        raise ValueError(f"Unsupported period: {period}")

    # If rolling window is specified, calculate rolling correlations
    if rolling_window is not None:
        return _calculate_rolling_correlations(
            clean_df, metric_x, metric_y, "period", rolling_window, method
        )

    # Group by period and calculate correlations
    periods = sorted(clean_df["period"].unique())
    results = []

    for p in periods:
        period_df = clean_df[clean_df["period"] == p]

        # Skip periods with insufficient data
        if len(period_df) < 3:
            results.append(
                {
                    "period": p,
                    "correlation": float("nan"),
                    "p_value": float("nan"),
                    "sample_size": len(period_df),
                }
            )
            continue

        # Calculate correlation
        if method == "pearson":
            r, p_val = stats.pearsonr(period_df[metric_x], period_df[metric_y])
        elif method == "spearman":
            r, p_val = stats.spearmanr(period_df[metric_x], period_df[metric_y])
        elif method == "kendall":
            r, p_val = stats.kendalltau(period_df[metric_x], period_df[metric_y])
        else:
            raise ValueError(f"Unsupported correlation method: {method}")

        results.append(
            {
                "period": p,
                "correlation": float(r),
                "p_value": float(p_val),
                "sample_size": len(period_df),
            }
        )

    return pd.DataFrame(results)


def _calculate_rolling_correlations(
    df: pd.DataFrame,
    metric_x: str,
    metric_y: str,
    period_col: str,
    window: int,
    method: str,
) -> pd.DataFrame:
    """Helper function to calculate rolling correlations over time periods."""
    periods = sorted(df[period_col].unique())

    if len(periods) < window:
        raise ValueError(f"Insufficient periods for rolling window of {window}")

    results = []

    for i in range(len(periods) - window + 1):
        window_periods = periods[i : i + window]
        window_df = df[df[period_col].isin(window_periods)]

        # Skip windows with insufficient data
        if len(window_df) < 3:
            results.append(
                {
                    "period": f"{window_periods[0]} to {window_periods[-1]}",
                    "correlation": float("nan"),
                    "p_value": float("nan"),
                    "sample_size": len(window_df),
                }
            )
            continue

        # Calculate correlation
        if method == "pearson":
            r, p_val = stats.pearsonr(window_df[metric_x], window_df[metric_y])
        elif method == "spearman":
            r, p_val = stats.spearmanr(window_df[metric_x], window_df[metric_y])
        elif method == "kendall":
            r, p_val = stats.kendalltau(window_df[metric_x], window_df[metric_y])
        else:
            raise ValueError(f"Unsupported correlation method: {method}")

        results.append(
            {
                "period": f"{window_periods[0]} to {window_periods[-1]}",
                "correlation": float(r),
                "p_value": float(p_val),
                "sample_size": len(window_df),
            }
        )

    return pd.DataFrame(results)


def conditional_correlation_heatmap(
    results: Dict[str, Tuple[float, float]],
    main_correlation: float = None,
    title: str = "Conditional Correlation Analysis",
    significance_threshold: float = 0.05,
    width: int = 650,
    height: int = 400,
):
    """Create a visual representation of conditional correlations.

    Parameters
    ----------
    results : Dict[str, Tuple[float, float]]
        Dictionary mapping condition values to (correlation, p-value) tuples.
    main_correlation : float, optional
        Overall correlation coefficient for comparison.
    title : str, default "Conditional Correlation Analysis"
        Plot title.
    significance_threshold : float, default 0.05
        P-value threshold for statistical significance.
    width, height : int
        Plot dimensions.

    Returns
    -------
    holoviews.Element
        HoloViews visualization of conditional correlations.
    """
    # Prepare data for plotting
    conditions = []
    correlations = []
    p_values = []
    is_significant = []

    for condition, (corr, p_val) in results.items():
        if not np.isnan(corr):
            conditions.append(str(condition))
            correlations.append(corr)
            p_values.append(p_val)
            is_significant.append(p_val < significance_threshold)

    # Create DataFrame for plotting
    plot_df = pd.DataFrame(
        {
            "condition": conditions,
            "correlation": correlations,
            "p_value": p_values,
            "significant": is_significant,
        }
    )

    # Sort by absolute correlation value
    plot_df = plot_df.sort_values("correlation", key=abs, ascending=False)

    # Create color map based on statistical significance
    colors = ["#4c78a8" if sig else "#cccccc" for sig in plot_df["significant"]]

    # Create the bar chart
    bars = hv.Bars(plot_df, kdims=["condition"], vdims=["correlation"]).opts(
        color=colors,
        width=width,
        height=height,
        title=title,
        tools=["hover"],
        xrotation=45,
        ylabel="Correlation Coefficient",
    )

    # Add horizontal line for main correlation if provided
    if main_correlation is not None:
        hline = hv.HLine(main_correlation).opts(
            color="red", line_width=2, line_dash="dashed"
        )
        return bars * hline

    return bars


def time_series_correlation_plot(
    df: pd.DataFrame,
    title: str = "Correlation Over Time",
    significance_threshold: float = 0.05,
    width: int = 750,
    height: int = 400,
):
    """Create a visual representation of correlations over time.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with columns: period, correlation, p_value, sample_size.
    title : str, default "Correlation Over Time"
        Plot title.
    significance_threshold : float, default 0.05
        P-value threshold for statistical significance.
    width, height : int
        Plot dimensions.

    Returns
    -------
    holoviews.Element
        HoloViews visualization of correlations over time.
    """
    # Add column for significance
    df = df.copy()
    df["significant"] = df["p_value"] < significance_threshold

    # Create separate DataFrames for significant and non-significant points
    sig_df = df[df["significant"]]
    nonsig_df = df[~df["significant"]]

    # Create main line plot
    line = hv.Curve(df, kdims=["period"], vdims=["correlation"]).opts(
        width=width,
        height=height,
        title=title,
        tools=["hover"],
        line_width=2,
        xrotation=45,
        ylabel="Correlation Coefficient",
    )

    # Add markers for significant and non-significant points
    sig_points = hv.Scatter(sig_df, kdims=["period"], vdims=["correlation"]).opts(
        color="green",
        size=8,
        marker="circle",
    )

    nonsig_points = hv.Scatter(nonsig_df, kdims=["period"], vdims=["correlation"]).opts(
        color="gray",
        size=8,
        marker="circle",
    )

    # Add reference line at zero
    zero_line = hv.HLine(0).opts(color="black", line_dash="dotted")

    # Combine plots
    return line * sig_points * nonsig_points * zero_line
