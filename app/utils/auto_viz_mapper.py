"""Automatic visualisation mapper.

Given a validated `QueryIntent` and a *tabular* result (DataFrame or Series),
return a sensible default HoloViews/Panel object that visualises the data.
The goal is *deterministic* mapping so the assistant can display a chart
without ad-hoc LLM reasoning.

This is a first-pass heuristic; it will evolve as new intent patterns emerge.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import hvplot.pandas  # noqa: F401 – register accessor
from holoviews.element import Element

from app.utils.plots import histogram, line_plot, scatter_plot
from app.utils.query_intent import QueryIntent

__all__ = ["auto_visualize"]


# ---------------------------------------------------------------------------
# Core mapping function
# ---------------------------------------------------------------------------


def auto_visualize(
    data: Any, intent: QueryIntent, *, height: int = 350, width: int = 550
) -> Optional[Element]:
    """Return an hvplot visualisation or *None* when no obvious mapping exists.

    Parameters
    ----------
    data
        The result object produced by the analysis execution step. Usually a
        `pandas.DataFrame`, `Series`, or scalar.  Other types are ignored.
    intent
        Structured representation of the user's question.
    height, width
        Default plot dimensions passed to hvplot.
    """

    # ---------------------------------------------------------------------
    # 1. Quick exits – unsupported types or empty data
    # ---------------------------------------------------------------------
    if data is None:
        return None
    if isinstance(data, (int, float)):
        # Single scalar – nothing to plot; number card handled elsewhere.
        return None

    # ---------------------------------------------------------------------
    # 2. Handle correlation results specifically
    # ---------------------------------------------------------------------
    if intent.analysis_type == "correlation":
        # If the result is a dict with 'visualization' key, return that
        if isinstance(data, dict) and "visualization" in data:
            return data["visualization"]

        # If we have a DataFrame with two columns that could be our metrics
        if (
            isinstance(data, pd.DataFrame)
            and len(data.columns) >= 2
            and len(intent.additional_fields) >= 1
        ):
            metric_x = intent.target_field
            metric_y = intent.additional_fields[0]

            # Try to find columns by name
            x_col = next(
                (col for col in data.columns if metric_x.lower() in col.lower()), None
            )
            y_col = next(
                (col for col in data.columns if metric_y.lower() in col.lower()), None
            )

            # If we found both columns, generate a scatter plot
            if x_col is not None and y_col is not None:
                return scatter_plot(
                    data,
                    x=x_col,
                    y=y_col,
                    title=f"Correlation: {x_col.title()} vs {y_col.title()}",
                    correlation=True,
                    regression=True,
                )

        # If we have a dict with our metrics as separate keys
        if (
            isinstance(data, dict)
            and len(intent.additional_fields) >= 1
            and intent.target_field in data
            and intent.additional_fields[0] in data
        ):
            # Create a DataFrame from the metrics
            metric_x = intent.target_field
            metric_y = intent.additional_fields[0]

            # Check if the values are scalar or Series/arrays
            if isinstance(data[metric_x], (list, pd.Series)) and isinstance(
                data[metric_y], (list, pd.Series)
            ):
                # Convert to DataFrame
                df = pd.DataFrame({metric_x: data[metric_x], metric_y: data[metric_y]})

                return scatter_plot(
                    df, x=metric_x, y=metric_y, correlation=True, regression=True
                )

    # ---------------------------------------------------------------------
    # 3. Handle top_n analysis results specifically
    # ---------------------------------------------------------------------
    if intent.analysis_type == "top_n":
        # Get the parameter n (default: 5)
        n = intent.parameters.get("n", 5) if isinstance(intent.parameters, dict) else 5

        # If the result is a dict of counts, create a bar chart
        if isinstance(data, dict):
            # Convert dict to Series for plotting
            series = pd.Series(data)

            if not series.empty:
                # Sort series for better visualization (depends on order parameter)
                order = (
                    "asc"
                    if (
                        isinstance(intent.parameters, dict)
                        and intent.parameters.get("order", "desc").lower() == "asc"
                    )
                    else "desc"
                )

                # Create title based on intent
                title = f"{'Top' if order == 'desc' else 'Bottom'} {n} {intent.target_field.title()}"

                # Return bar chart
                return series.hvplot.bar(
                    height=height,
                    width=width,
                    rot=45,
                    title=title,
                    xlabel=intent.target_field.title(),
                    ylabel="Count",
                )

        # Handle DataFrame result with counts (fallback)
        elif isinstance(data, pd.DataFrame) and len(data.columns) == 2:
            # Try to identify count column and label column
            numeric_cols = data.select_dtypes("number").columns
            cat_cols = data.select_dtypes(exclude="number").columns

            if len(numeric_cols) == 1 and len(cat_cols) == 1:
                # Set the categorical column as index and plot the numeric column
                plot_df = data.set_index(cat_cols[0])

                # Create title based on intent
                order = (
                    "asc"
                    if (
                        isinstance(intent.parameters, dict)
                        and intent.parameters.get("order", "desc").lower() == "asc"
                    )
                    else "desc"
                )
                title = f"{'Top' if order == 'desc' else 'Bottom'} {n} {intent.target_field.title()}"

                return plot_df.hvplot.bar(
                    y=numeric_cols[0],
                    height=height,
                    width=width,
                    rot=45,
                    title=title,
                    xlabel=intent.target_field.title(),
                    ylabel="Count",
                )

    # ---------------------------------------------------------------------
    # Original auto visualization code continues below
    # ---------------------------------------------------------------------
    # Ensure we are working with a DataFrame
    if isinstance(data, pd.Series):
        df = data.to_frame(name=data.name or "value")
    elif isinstance(data, pd.DataFrame):
        df = data
    else:
        # Unknown type (dict, list, etc.) – skip visualisation for now.
        return None

    # If DataFrame is empty, skip.
    if df.empty:
        return None

    # ---------------------------------------------------------------------
    # 2. Heuristic mapping based on intent.analysis_type & presence of group_by
    # ---------------------------------------------------------------------
    analysis = intent.analysis_type
    group_cols = intent.group_by or []

    # Distribution → histogram of target_field
    if analysis == "distribution":
        col = intent.target_field
        if col in df.columns:
            return histogram(df, col, title=f"{col.title()} Distribution")
        # fall back to first numeric
        num_cols = df.select_dtypes("number").columns
        if num_cols.any():
            return histogram(df, num_cols[0])

    # ---------------- NEW: percent_change dict → bar chart ----------------
    if analysis == "percent_change" and isinstance(data, (pd.Series, dict)):
        # Convert to Series for uniform handling
        if isinstance(data, dict):
            ser = pd.Series(data)
        else:
            ser = data
        # Sort absolute descending so biggest changes top
        ser = ser.sort_values(ascending=False, key=lambda x: x.abs())
        return ser.hvplot.bar(
            height=height,
            width=width,
            rot=45,
            title="Percent Change by "
            + (intent.group_by[0].title() if intent.group_by else "Group"),
            ylabel="% Change",
        )

    # Trend / change over time → line plot (x=date, y=metric)
    if analysis in {"trend", "change", "average_change", "percent_change"}:
        # Heuristic: pick the first datetime column as x, metric as y.
        datetime_cols = df.select_dtypes("datetime").columns
        y_col = intent.target_field if intent.target_field in df.columns else None
        if datetime_cols.any() and y_col:
            return line_plot(df, x=datetime_cols[0], y=y_col)

    # Aggregations with a single group_by dimension → bar chart
    if group_cols and len(group_cols) == 1 and intent.target_field in df.columns:
        x = group_cols[0]
        y = intent.target_field
        return df.hvplot.bar(
            x=x, y=y, height=height, width=width, title=f"{y.title()} by {x.title()}"
        )

    # Fallback: if exactly two columns and one is categorical, other numeric → bar chart
    if df.shape[1] == 2:
        cat_cols = df.select_dtypes("object").columns
        num_cols = df.select_dtypes("number").columns
        if len(cat_cols) == 1 and len(num_cols) == 1:
            return df.hvplot.bar(
                x=cat_cols[0], y=num_cols[0], height=height, width=width
            )

    # No suitable mapping found
    return None
