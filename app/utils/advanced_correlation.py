"""
Advanced correlation analysis utilities.

This module provides specialized functions for analyzing correlations
between different metrics in patient data.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Literal
import logging
import holoviews as hv
from scipy import stats

logger = logging.getLogger(__name__)

# Constants for correlation types
PEARSON = "pearson"
SPEARMAN = "spearman"
KENDALL = "kendall"
VALID_CORR_METHODS = [PEARSON, SPEARMAN, KENDALL]


def calculate_correlation_matrix(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    method: str = PEARSON,
) -> pd.DataFrame:
    """
    Calculate correlation matrix for selected columns.

    Args:
        df: DataFrame containing the data
        columns: List of column names to include in correlation matrix
                 If None, all numeric columns are used
        method: Correlation method (pearson, spearman, or kendall)

    Returns:
        DataFrame containing the correlation matrix
    """
    if method not in VALID_CORR_METHODS:
        logger.warning(
            f"Invalid correlation method: {method}. Using {PEARSON} instead."
        )
        method = PEARSON

    if columns is None:
        # Use all numeric columns
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        columns = numeric_cols
    else:
        # Ensure all specified columns exist and are numeric
        missing_cols = [col for col in columns if col not in df.columns]
        if missing_cols:
            logger.warning(f"Columns not found in DataFrame: {missing_cols}")
            columns = [col for col in columns if col in df.columns]

        non_numeric = [
            col
            for col in columns
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col])
        ]
        if non_numeric:
            logger.warning(
                f"Non-numeric columns will be excluded from correlation: {non_numeric}"
            )
            columns = [
                col
                for col in columns
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col])
            ]

    if not columns:
        logger.error("No valid columns for correlation calculation")
        return pd.DataFrame()

    return df[columns].corr(method=method)


def calculate_conditional_correlation(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    condition_col: str,
    condition_values: Optional[List] = None,
    method: str = PEARSON,
) -> Dict[str, float]:
    """
    Calculate correlation between two variables for different values of a condition.

    Args:
        df: DataFrame containing the data
        x_col: First variable column name
        y_col: Second variable column name
        condition_col: Column name to condition on
        condition_values: List of values to calculate correlations for
                          If None, all unique values are used
        method: Correlation method (pearson, spearman, or kendall)

    Returns:
        Dictionary mapping condition values to correlation coefficients
    """
    if method not in VALID_CORR_METHODS:
        logger.warning(
            f"Invalid correlation method: {method}. Using {PEARSON} instead."
        )
        method = PEARSON

    # Validate columns exist
    for col in [x_col, y_col, condition_col]:
        if col not in df.columns:
            logger.error(f"Column not found: {col}")
            return {}

    # Validate numeric columns
    for col in [x_col, y_col]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.error(f"Column must be numeric: {col}")
            return {}

    # Get unique values for the condition
    if condition_values is None:
        condition_values = df[condition_col].unique()

    correlations = {}
    for value in condition_values:
        subset = df[df[condition_col] == value]
        if len(subset) < 3:
            # Need at least 3 points for meaningful correlation
            logger.info(
                f"Insufficient data points for {condition_col}={value}. Skipping."
            )
            correlations[str(value)] = None
            continue

        if subset[x_col].nunique() < 2 or subset[y_col].nunique() < 2:
            # Need variation in both variables
            logger.info(
                f"Insufficient variation for {condition_col}={value}. Skipping."
            )
            correlations[str(value)] = None
            continue

        # Calculate correlation
        corr = subset[[x_col, y_col]].corr(method=method).iloc[0, 1]
        correlations[str(value)] = corr

    return correlations


def calculate_rolling_correlation(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    date_col: str,
    window_size: int = 30,
    min_periods: int = 5,
    method: str = PEARSON,
) -> pd.DataFrame:
    """
    Calculate rolling correlation between two variables over time.

    Args:
        df: DataFrame containing the data
        x_col: First variable column name
        y_col: Second variable column name
        date_col: Column containing date values
        window_size: Size of the rolling window in days
        min_periods: Minimum number of observations in window required
        method: Correlation method (pearson, spearman, or kendall)

    Returns:
        DataFrame with dates and corresponding correlation values
    """
    if method not in VALID_CORR_METHODS:
        logger.warning(
            f"Invalid correlation method: {method}. Using {PEARSON} instead."
        )
        method = PEARSON

    # Validate columns exist
    for col in [x_col, y_col, date_col]:
        if col not in df.columns:
            logger.error(f"Column not found: {col}")
            return pd.DataFrame()

    # Validate numeric columns
    for col in [x_col, y_col]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.error(f"Column must be numeric: {col}")
            return pd.DataFrame()

    # Ensure date column is datetime type
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        try:
            df = df.copy()
            df[date_col] = pd.to_datetime(df[date_col])
        except Exception as e:
            logger.error(f"Failed to convert {date_col} to datetime: {e}")
            return pd.DataFrame()

    # Sort by date
    df = df.sort_values(by=date_col)

    # Set up result DataFrame
    result = pd.DataFrame()
    result[date_col] = df[date_col]

    # Define a function to calculate correlation for each window
    def rolling_corr(window):
        if len(window) < min_periods:
            return np.nan
        if window[x_col].nunique() < 2 or window[y_col].nunique() < 2:
            return np.nan
        return window[[x_col, y_col]].corr(method=method).iloc[0, 1]

    # Apply the rolling correlation
    rolling_result = (
        df.set_index(date_col)
        .rolling(f"{window_size}D", min_periods=min_periods)
        .apply(rolling_corr)
    )

    # Add the correlation to the result
    result["correlation"] = rolling_result.reset_index(drop=True)

    return result


def find_strongest_correlations(
    df: pd.DataFrame,
    target_col: str,
    exclude_cols: Optional[List[str]] = None,
    top_n: int = 5,
    method: str = PEARSON,
    min_abs_corr: float = 0.3,
) -> pd.DataFrame:
    """
    Find the variables most strongly correlated with a target variable.

    Args:
        df: DataFrame containing the data
        target_col: Target column to find correlations with
        exclude_cols: Columns to exclude from analysis
        top_n: Number of top correlations to return
        method: Correlation method (pearson, spearman, or kendall)
        min_abs_corr: Minimum absolute correlation to include

    Returns:
        DataFrame with columns and their correlation with the target
    """
    if method not in VALID_CORR_METHODS:
        logger.warning(
            f"Invalid correlation method: {method}. Using {PEARSON} instead."
        )
        method = PEARSON

    # Validate target column exists
    if target_col not in df.columns:
        logger.error(f"Target column not found: {target_col}")
        return pd.DataFrame()

    # Validate target column is numeric
    if not pd.api.types.is_numeric_dtype(df[target_col]):
        logger.error(f"Target column must be numeric: {target_col}")
        return pd.DataFrame()

    # Get numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    # Apply exclusions
    if exclude_cols is None:
        exclude_cols = []

    # Always exclude the target column itself
    if target_col not in exclude_cols:
        exclude_cols.append(target_col)

    candidates = [col for col in numeric_cols if col not in exclude_cols]

    if not candidates:
        logger.warning("No candidate columns for correlation analysis")
        return pd.DataFrame()

    # Calculate correlations
    corr_series = df[candidates + [target_col]].corr(method=method)[target_col]
    corr_series = corr_series.drop(target_col)

    # Filter by minimum correlation
    corr_series = corr_series[corr_series.abs() >= min_abs_corr]

    # Sort by absolute value and take top_n
    sorted_corr = corr_series.abs().sort_values(ascending=False).head(top_n)

    # Create result DataFrame
    result = pd.DataFrame(
        {
            "column": sorted_corr.index,
            "correlation": [corr_series[col] for col in sorted_corr.index],
        }
    )

    return result


def calculate_correlation_significance(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    method: str = PEARSON,
    alpha: float = 0.05,
) -> Tuple[float, float, bool]:
    """
    Calculate correlation and its statistical significance.

    Args:
        df: DataFrame containing the data
        x_col: First variable column name
        y_col: Second variable column name
        method: Correlation method (pearson or spearman)
        alpha: Significance level

    Returns:
        Tuple containing (correlation coefficient, p-value, is_significant)
    """
    from scipy import stats

    if method not in [PEARSON, SPEARMAN]:
        logger.warning(
            f"Method {method} not supported for significance testing. Using {PEARSON}."
        )
        method = PEARSON

    # Validate columns exist and are numeric
    for col in [x_col, y_col]:
        if col not in df.columns:
            logger.error(f"Column not found: {col}")
            return (np.nan, np.nan, False)
        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.error(f"Column must be numeric: {col}")
            return (np.nan, np.nan, False)

    # Drop missing values
    valid_data = df[[x_col, y_col]].dropna()

    if len(valid_data) < 3:
        logger.warning("Insufficient data for correlation analysis")
        return (np.nan, np.nan, False)

    # Calculate correlation and p-value
    if method == PEARSON:
        corr, p_value = stats.pearsonr(valid_data[x_col], valid_data[y_col])
    else:  # SPEARMAN
        corr, p_value = stats.spearmanr(valid_data[x_col], valid_data[y_col])

    # Determine significance
    is_significant = p_value < alpha

    return (corr, p_value, is_significant)


def partial_correlation(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    control_cols: List[str],
) -> float:
    """
    Calculate partial correlation between x and y while controlling for other variables.

    Args:
        df: DataFrame containing the data
        x_col: First variable column name
        y_col: Second variable column name
        control_cols: List of column names to control for

    Returns:
        Partial correlation coefficient
    """
    from scipy import stats

    # Validate columns exist and are numeric
    all_cols = [x_col, y_col] + control_cols
    for col in all_cols:
        if col not in df.columns:
            logger.error(f"Column not found: {col}")
            return np.nan
        if not pd.api.types.is_numeric_dtype(df[col]):
            logger.error(f"Column must be numeric: {col}")
            return np.nan

    # Drop missing values
    valid_data = df[all_cols].dropna()

    if len(valid_data) < len(all_cols) + 2:
        logger.warning("Insufficient data for partial correlation analysis")
        return np.nan

    # Calculate residuals for x after controlling for control_cols
    x = valid_data[x_col].values
    x_controls = valid_data[control_cols].values
    x_resid = stats.linregress(x_controls, x).resid

    # Calculate residuals for y after controlling for control_cols
    y = valid_data[y_col].values
    y_controls = valid_data[control_cols].values
    y_resid = stats.linregress(y_controls, y).resid

    # Calculate correlation between residuals
    partial_corr = stats.pearsonr(x_resid, y_resid)[0]

    return partial_corr


# The functions below are taken from the archive for test compatibility


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
    for col in [metric_x, metric_y, condition_field]:
        if col not in df.columns:
            raise KeyError(f"Column not found: {col}")

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
    for col in [metric_x, metric_y, date_column]:
        if col not in df.columns:
            raise KeyError(f"Column not found: {col}")

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
    correlations: Dict[str, Tuple[float, float]],
    main_correlation: float = None,
    title: str = "Conditional Correlation Analysis",
    significance_threshold: float = 0.05,
    width: int = 650,
    height: int = 400,
):
    """Create a heatmap visualization of conditional correlations.

    Parameters
    ----------
    correlations : Dict[str, Tuple[float, float]]
        Dictionary mapping condition values to (correlation, p-value) tuples.
    main_correlation : float, optional
        Overall correlation coefficient to show as reference.
    title : str, default "Conditional Correlation Analysis"
        Plot title.
    significance_threshold : float, default 0.05
        P-value threshold for statistical significance.
    width, height : int
        Plot dimensions.

    Returns
    -------
    holoviews.Element
        HoloViews visualization object.
    """
    # Create a DataFrame from the correlations
    data = []
    for condition, (corr, p_val) in correlations.items():
        if pd.isna(corr) or pd.isna(p_val):
            continue
        data.append(
            {
                "condition": condition,
                "correlation": corr,
                "p_value": p_val,
                "significant": p_val < significance_threshold,
            }
        )

    if not data:
        return hv.Div("No valid correlation data to visualize")

    df = pd.DataFrame(data)

    # Sort by correlation strength (absolute value)
    df = df.sort_values("correlation", key=abs, ascending=False)

    # Create the bar chart
    bars = hv.Bars(
        df, kdims=["condition"], vdims=["correlation", "p_value", "significant"]
    ).opts(
        width=width,
        height=height,
        title=title,
        color="correlation",
        colorbar=True,
        cmap="RdBu_r",
        clim=(-1, 1),
        xlabel="",
        ylabel="Correlation Coefficient",
        tools=["hover"],
        xrotation=45,
    )

    # Add reference line for main correlation if provided
    if main_correlation is not None:
        reference_line = hv.HLine(main_correlation).opts(
            color="black", line_dash="dashed", line_width=1.5
        )
        return bars * reference_line

    return bars


def time_series_correlation_plot(
    df: pd.DataFrame,
    title: str = "Correlation Over Time",
    significance_threshold: float = 0.05,
    width: int = 750,
    height: int = 400,
):
    """Create a line plot of correlations over time periods.

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
        HoloViews visualization object.
    """
    # Check required columns
    required_cols = ["period", "correlation", "p_value"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return hv.Div(f"Missing required columns: {', '.join(missing_cols)}")

    if df.empty:
        return hv.Div("No data to visualize")

    # Add significance indicator
    df = df.copy()
    df["significant"] = df["p_value"] < significance_threshold

    # Create line plot for all points
    line = hv.Curve(df, kdims=["period"], vdims=["correlation"]).opts(
        width=width,
        height=height,
        title=title,
        xlabel="Period",
        ylabel="Correlation Coefficient",
        line_width=2,
    )

    # Create scatter plots - different styles for significant vs. non-significant
    significant_points = df[df["significant"]].copy()
    non_significant_points = df[~df["significant"]].copy()

    # Create points for significant correlations
    sig_scatter = hv.Scatter(
        significant_points,
        kdims=["period"],
        vdims=["correlation", "p_value", "sample_size", "significant"],
    ).opts(
        color="darkblue",
        size=8,
        marker="circle",
        tools=["hover"],
    )

    # Create points for non-significant correlations
    nonsig_scatter = hv.Scatter(
        non_significant_points,
        kdims=["period"],
        vdims=["correlation", "p_value", "sample_size", "significant"],
    ).opts(
        color="lightgray",
        size=6,
        marker="circle",
        tools=["hover"],
    )

    # Add reference line at zero
    zero_line = hv.HLine(0).opts(
        color="black",
        line_dash="dotted",
        line_width=1,
    )

    # Combine all elements
    plot = line * sig_scatter * nonsig_scatter * zero_line

    return plot.opts(
        legend_position="top_right",
        show_grid=True,
    )
