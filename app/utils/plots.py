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
    return df[column].hvplot.hist(
        bins=bins, alpha=0.7, height=300, width=500, title=_title
    )


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
