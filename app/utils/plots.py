"""Reusable hvplot helper utilities.

These helpers are purposely pure: they accept dataframes/series and return
HoloViews objects without touching databases, LLMs, or global UI state.
"""

from __future__ import annotations

import hvplot.pandas  # noqa: F401 – required to register hvplot accessor
import pandas as pd

__all__ = ["histogram"]


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
