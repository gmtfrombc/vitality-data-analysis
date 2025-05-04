"""Reusable hvplot helper utilities.

These helpers are purposely pure: they accept dataframes/series and return
HoloViews objects without touching databases, LLMs, or global UI state.
"""

from __future__ import annotations

import hvplot.pandas  # noqa: F401 – required to register hvplot accessor
import pandas as pd

__all__ = [
    "histogram",
    "pie_chart",
    "line_plot",
    "scatter_plot",
]


def histogram(
    df: pd.DataFrame, column: str, *, bins: int = 20, title: str | None = None
):
    """Return a simple histogram plot for *column* of *df* using hvplot.

    Parameters
    ----------
    df : pandas.DataFrame
        Source data.
    column : str
        Column name to plot.
    bins : int, default 20
        Number of histogram bins.
    title : str, optional
        Plot title. If omitted, uses "{column} Distribution".
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in dataframe")

    _title = title or f"{column.title()} Distribution"

    try:
        # Try using hvplot.hist first
        return df[column].hvplot.hist(
            bins=bins, alpha=0.7, height=300, width=500, title=_title
        )
    except (ImportError, AttributeError) as e:
        # Fall back to direct HoloViews implementation if hvplot fails
        import holoviews as hv
        import numpy as np

        # Get the data and compute histogram
        data = df[column].dropna().values
        hist, edges = np.histogram(data, bins=bins)

        # Create HoloViews Histogram
        return hv.Histogram((edges, hist), kdims=[column], label=_title)


def pie_chart(
    counts: pd.Series | pd.DataFrame,
    *,
    value_col: str | None = None,
    label_col: str | None = None,
    title: str | None = None,
    height: int = 350,
    width: int = 350,
):
    """Return an hvplot pie chart from *counts*.

    `counts` may be either:
    • A *Series* where the index holds category names and values hold counts.
    • A *DataFrame* with two columns (label & value) – pass their names via
      *label_col* and *value_col*.
    """

    if isinstance(counts, pd.Series):
        df = counts.reset_index()
        df.columns = ["label", "value"]
        label_col_use = "label"
        value_col_use = "value"
    else:
        if value_col is None or label_col is None:
            raise ValueError(
                "Must supply value_col and label_col when counts is a DataFrame"
            )
        df = counts.rename(columns={label_col: "label", value_col: "value"})
        label_col_use = "label"
        value_col_use = "value"

    _title = title or "Distribution"
    try:
        return df.hvplot(
            kind="pie",
            x=label_col_use,
            y=value_col_use,
            title=_title,
            height=height,
            width=width,
            legend="right",
        )
    except NotImplementedError:
        # Older hvplot versions may not support 'pie'. Fallback to bar.
        return df.hvplot.bar(
            x=label_col_use,
            y=value_col_use,
            title=_title + " (bar)",
            height=height,
            width=width,
            legend="right",
        )


def line_plot(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    width: int = 600,
    height: int = 350,
    line_width: float = 2.0,
    grid: bool = True,
):
    """Return a simple line plot using hvplot with common defaults."""

    if x not in df.columns or y not in df.columns:
        raise ValueError(f"Columns '{x}' and/or '{y}' not found in dataframe")

    _title = title or f"{y.title()} Over Time"
    _xlabel = xlabel or x.title()
    _ylabel = ylabel or y.title()

    return df.hvplot(
        x=x,
        y=y,
        title=_title,
        xlabel=_xlabel,
        ylabel=_ylabel,
        width=width,
        height=height,
        grid=grid,
        line_width=line_width,
    )


def scatter_plot(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    width: int = 600,
    height: int = 400,
    grid: bool = True,
    correlation: bool = True,
    color: str = "blue",
    alpha: float = 0.6,
    size: int = 50,
    regression: bool = True,
):
    """Create a scatter plot with optional correlation statistics and regression line.

    Parameters
    ----------
    df : pandas.DataFrame
        Source data containing both metrics.
    x : str
        Column name for x-axis.
    y : str
        Column name for y-axis.
    title : str, optional
        Plot title. If omitted, uses "Correlation: {x} vs {y}".
    xlabel, ylabel : str, optional
        Axis labels. If omitted, uses column names.
    width, height : int
        Plot dimensions.
    grid : bool, default True
        Whether to show grid lines.
    correlation : bool, default True
        Whether to display correlation coefficient on the plot.
    color : str, default "blue"
        Scatter point color.
    alpha : float, default 0.6
        Opacity of scatter points (0-1).
    size : int, default 50
        Scatter point size.
    regression : bool, default True
        Whether to show regression line.

    Returns
    -------
    holoviews.Element
        HoloViews scatter plot with optional regression line.
    """
    if x not in df.columns or y not in df.columns:
        raise ValueError(f"Columns '{x}' and/or '{y}' not found in dataframe")

    # Clean data - remove rows with NaN in either column
    clean_df = df.dropna(subset=[x, y])

    if len(clean_df) < 2:
        raise ValueError(
            f"Need at least 2 valid data points for correlation analysis, got {len(clean_df)}"
        )

    # Calculate correlation coefficient using numpy
    # Import numpy inside the function to avoid namespace issues

    corr_coef = np.corrcoef(clean_df[x], clean_df[y])[0, 1]
    corr_text = f"Correlation: {corr_coef:.3f}"

    _title = title or f"Correlation: {x.title()} vs {y.title()}"
    if correlation:
        _title = f"{_title}\n{corr_text}"

    _xlabel = xlabel or x.title()
    _ylabel = ylabel or y.title()

    scatter = clean_df.hvplot.scatter(
        x=x,
        y=y,
        title=_title,
        xlabel=_xlabel,
        ylabel=_ylabel,
        width=width,
        height=height,
        grid=grid,
        color=color,
        alpha=alpha,
        size=size,
    )

    if regression and len(clean_df) > 2:
        # Add regression line
        # Import modules inside the function scope to avoid namespace conflicts
        import numpy as np
        from scipy import stats

        slope, intercept, _, _, _ = stats.linregress(clean_df[x], clean_df[y])
        x_range = np.linspace(clean_df[x].min(), clean_df[x].max(), 100)
        y_range = intercept + slope * x_range

        regression_df = pd.DataFrame({x: x_range, y: y_range})
        regression_line = regression_df.hvplot.line(
            x=x,
            y=y,
            color="red",
            line_width=2,
            label=f"y = {slope:.3f}x + {intercept:.3f}",
        )

        return scatter * regression_line

    return scatter
