"""
Analysis Helpers for Data Analysis Assistant

This module contains helper functions for data analysis, plotting, and results formatting.
It separates transformation and visualization logic from the UI and core engine.

The module provides:
1. Formatting functions for different result types (scalar, dictionary, dataframe)
2. Visualization generation functions for various analysis types
3. Unit conversion and data transformation utilities
4. Result aggregation and combination functions
"""

import re
import logging
import pandas as pd
import numpy as np

from app.utils.patient_attributes import Gender, Active

# Configure logging
logger = logging.getLogger("data_assistant.analysis_helpers")

# Constants for patient attribute values
FEMALE = Gender.FEMALE.value
MALE = Gender.MALE.value
ACTIVE = Active.ACTIVE.value
INACTIVE = Active.INACTIVE.value

# ------------------------------------------------------------------
# Optional heavy dependencies – provide lightweight stubs when they
# are unavailable (e.g. blocked by the sandbox import guard).  This
# prevents ImportError from bubbling up and breaking scalar-only
# analyses that have no need for plotting.
# ------------------------------------------------------------------


try:
    import holoviews as hv  # type: ignore
except Exception:  # pragma: no cover – stub when plotting libs disabled
    import types
    import sys

    hv = types.ModuleType("holoviews")
    # Provide minimal dummies for attrs accessed elsewhere
    setattr(hv, "Div", lambda *a, **k: None)
    setattr(hv, "Histogram", lambda *a, **k: None)
    setattr(hv, "Curve", lambda *a, **k: None)
    sys.modules["holoviews"] = hv


try:
    import panel as pn  # type: ignore
except Exception:  # pragma: no cover – stub when plotting libs disabled
    import types
    import sys

    pn = types.ModuleType("panel")
    pn.pane = types.ModuleType("pane")
    setattr(pn.pane, "Markdown", lambda *a, **k: None)
    sys.modules["panel"] = pn


def format_scalar_results(value, metric_type="value"):
    """
    Format scalar results into a human-readable format.

    Takes a single numeric value and formats it with appropriate labels and
    formatting based on the metric type. Handles different number formats
    (integers vs. floats) with appropriate decimal place handling.

    Args:
        value: The scalar value to format (number, typically int or float)
        metric_type: The type of metric (e.g., 'count', 'average', 'sum')

    Returns:
        dict: Formatted result with appropriate labels and formatting
    """
    if isinstance(value, (int, float, np.number)):
        # Format number with commas and up to 2 decimal places
        if isinstance(value, (int, np.integer)):
            formatted_value = f"{value:,}"
        else:
            formatted_value = f"{value:,.2f}"

        # Remove trailing zeros after decimal for cleaner display
        if "." in formatted_value:
            formatted_value = formatted_value.rstrip("0").rstrip(".")

        # Generate appropriate label based on metric type
        label = ""
        if metric_type == "count":
            label = "Count"
        elif metric_type == "average":
            label = "Average"
        elif metric_type == "sum":
            label = "Sum"
        elif metric_type == "median":
            label = "Median"
        elif metric_type == "min":
            label = "Minimum"
        elif metric_type == "max":
            label = "Maximum"
        elif metric_type == "std_dev":
            label = "Standard Deviation"
        elif metric_type == "variance":
            label = "Variance"
        else:
            label = "Value"

        return {
            "type": "scalar",
            "value": formatted_value,
            "raw_value": value,
            "label": label,
        }

    return {
        "type": "scalar",
        "value": str(value),
        "raw_value": value,
        "label": "Result",
    }


def format_dict_results(result_dict, analysis_type=None):
    """
    Format dictionary results into a structured format.

    Processes dictionary results from analysis code execution into a standardized
    format with type information. Handles special cases like errors, visualizations,
    and specific analysis types with customized formatting rules.

    Args:
        result_dict: Dictionary of results from code execution
        analysis_type: The type of analysis performed (helps determine formatting)

    Returns:
        dict: Formatted results with type information and structural organization
    """
    # Handle error results
    if "error" in result_dict:
        return {
            "type": "error",
            "message": result_dict["error"],
            "details": result_dict.get("traceback", ""),
        }

    # Handle threshold query results
    if "threshold_info" in result_dict:
        return {
            "type": "threshold",
            "data": result_dict,
        }

    # Handle dictionary with a visualization
    if "visualization" in result_dict:
        visualization = result_dict["visualization"]
        # Remove visualization from the data dictionary to avoid duplication
        data_dict = {k: v for k, v in result_dict.items() if k != "visualization"}

        if not data_dict:
            # If only visualization was in the result, create a minimal result
            data_dict = {"result": "See visualization"}

        return {
            "type": "visualization_with_data",
            "data": data_dict,
            "visualization": visualization,
        }

    # Handle correlation results
    if analysis_type == "correlation" or "correlation_coefficient" in result_dict:
        return {
            "type": "correlation",
            "data": result_dict,
        }

    # Handle distribution results
    if analysis_type == "distribution" or (
        "bin_edges" in result_dict and "counts" in result_dict
    ):
        return {
            "type": "distribution",
            "data": result_dict,
        }

    # Handle change results (e.g., weight loss)
    if analysis_type == "change" or "average_change" in result_dict:
        return {
            "type": "change",
            "data": result_dict,
        }

    # Handle trend results (typically by time period)
    if analysis_type == "trend" or (
        isinstance(next(iter(result_dict.keys()), ""), str)
        and re.match(r"\d{4}-\d{2}", next(iter(result_dict.keys()), ""))
    ):
        return {
            "type": "trend",
            "data": result_dict,
        }

    # Default dictionary handling
    return {
        "type": "dictionary",
        "data": result_dict,
    }


def format_dataframe_results(df):
    """
    Format DataFrame results into a structured format.

    Processes a pandas DataFrame into a standardized format for display,
    including metadata about the DataFrame's structure and a sample of rows.

    Args:
        df: Pandas DataFrame from analysis results

    Returns:
        dict: Formatted results with DataFrame metadata and sample
    """
    return {
        "type": "dataframe",
        "dataframe": df,
        "shape": df.shape,
        "columns": df.columns.tolist(),
        "sample": df.head(10).to_dict(orient="records"),
    }


def create_visualization_for_result(result, analysis_type=None, target_field=None):
    """
    Create visualization for results based on result type and analysis type.

    Automatically generates appropriate visualizations based on the result format
    and analysis type. Handles various result formats (scalar, dictionary, DataFrame)
    and analysis types (trend, distribution, comparison, etc.) to create meaningful
    visualizations.

    Args:
        result: Analysis result (could be scalar, dict, DataFrame)
        analysis_type: Type of analysis performed (helps determine viz type)
        target_field: Target field analyzed (helps with labeling)

    Returns:
        holoviews visualization or None if not applicable
    """
    # Skip visualization if already present
    if isinstance(result, dict) and "visualization" in result:
        return result["visualization"]

    # Handle threshold query results
    if isinstance(result, dict) and "threshold_info" in result:
        if (
            "hist_data" in result
            and "bin_edges" in result
            and "threshold_value" in result
        ):
            try:
                # Create a histogram with threshold line
                field = result["threshold_info"].get("field", "value")
                direction = result["threshold_info"].get("direction", "above")
                value = result["threshold_value"]
                title = f"Distribution of {field.upper()} with {direction.title()} {value} Threshold"

                # Create histogram from pre-computed data
                hist = histogram_from_bins(
                    result["bin_edges"], result["hist_data"], title=title
                )

                # Try to add a threshold line if holoviews is available
                try:
                    threshold_line = hv.VLine(value).opts(
                        color="red", line_width=2, line_dash="dashed"
                    )
                    return hist * threshold_line
                except Exception:
                    # If we can't add the line, just return the histogram
                    return hist
            except Exception as e:
                logger.error(f"Error creating threshold visualization: {e}")
                return None

    # Handle dictionary results
    if isinstance(result, dict):
        # Trend visualization (time series)
        if analysis_type == "trend" or (
            len(result) > 0
            and all(
                isinstance(k, str) and re.match(r"\d{4}-\d{2}", k)
                for k in result.keys()
            )
        ):
            # Convert to DataFrame for easier plotting
            df = pd.DataFrame(
                {"period": list(result.keys()), "value": list(result.values())}
            )
            df = df.sort_values("period")

            # Create line chart
            try:
                from holoviews import opts

                line = hv.Curve(df, "period", "value").opts(
                    opts.Curve(
                        width=600,
                        height=400,
                        line_width=2,
                        color="blue",
                        title=f"Trend Analysis for {target_field or 'Values'} Over Time",
                    )
                )
                return line
            except Exception:
                # Fallback to HTML line chart for time series data
                try:
                    from app.utils.plots import html_line_chart

                    title = f"Trend Analysis for {target_field or 'Values'} Over Time"
                    return html_line_chart(
                        df["period"].tolist(), df["value"].tolist(), title=title
                    )
                except Exception:
                    # If that fails, try bar chart as a last resort
                    try:
                        from app.utils.plots import html_bar_chart

                        return html_bar_chart(
                            df["period"].tolist(),
                            df["value"].tolist(),
                            title=f"Trend Analysis for {target_field or 'Values'} Over Time",
                        )
                    except Exception:
                        return hv.Div(
                            f"<div><strong>Trend Analysis for {target_field or 'Values'}</strong><br>Unable to display visualization</div>"
                        )

        # Distribution visualization
        elif analysis_type == "distribution" or "counts" in result:
            if "counts" in result and "bin_edges" in result:
                # Handle histograms with bin data
                return histogram_from_bins(
                    result["bin_edges"],
                    result["counts"],
                    title=f"Distribution of {target_field or 'Values'}",
                )

            # Handle categorical distribution without bin edges
            elif "categories" in result and "values" in result:
                try:
                    from app.utils.plots import bar_chart

                    # Create a dataframe for the bar chart
                    df = pd.DataFrame(
                        {"category": result["categories"], "value": result["values"]}
                    )

                    return bar_chart(
                        df,
                        x="category",
                        y="value",
                        title=f"Distribution of {target_field or 'Values'}",
                    )
                except Exception:
                    try:
                        from app.utils.plots import html_bar_chart

                        return html_bar_chart(
                            result["categories"],
                            result["values"],
                            title=f"Distribution of {target_field or 'Values'}",
                        )
                    except Exception:
                        return hv.Div(
                            f"<div><strong>Distribution of {target_field or 'Values'}</strong><br>Unable to display visualization</div>"
                        )

        # Correlation visualization
        elif analysis_type == "correlation" or "correlation_coefficient" in result:
            # Eventually would create a scatter plot, but for now just return None
            return None

    # Handle scalar results
    elif isinstance(result, (int, float)):
        return create_count_visualization(
            result,
            title=f"{analysis_type.capitalize() if analysis_type else 'Count'}: {target_field or 'Values'}",
        )

    # Handle DataFrame results
    elif isinstance(result, pd.DataFrame):
        if len(result) > 0 and not result.empty:
            # Simplistic approach for now - create a bar chart of the first numeric column
            numeric_cols = result.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                # Convert index to strings for better display
                result_copy = result.copy()
                result_copy.index = result_copy.index.astype(str)

                # Create a simple bar chart of the first numeric column
                first_numeric = numeric_cols[0]
                return bar_chart(
                    result_copy.reset_index(),
                    "index",
                    first_numeric,
                    title=f"{first_numeric} by {result_copy.index.name or 'Category'}",
                )

    # Default case
    return None


def create_count_visualization(count, title="Count"):
    """Create a simple visualization for a count or scalar value."""
    if not isinstance(count, (int, float)):
        return None

    # Round floating point numbers for display
    if isinstance(count, float):
        display_count = round(count, 2)
    else:
        display_count = count

    # Create a simple text box with the count
    import panel as pn

    return pn.pane.Markdown(
        f"## {title}\n\n# {display_count:,}",
        align="center",
        styles={
            "background": "#f0f8ff",
            "padding": "20px",
            "border-radius": "10px",
            "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
            "margin": "10px 0",
            "text-align": "center",
        },
    )


def histogram_from_bins(bin_edges, counts, title="Distribution"):
    """
    Create a histogram from pre-computed bin edges and counts.

    Generates a HoloViews histogram visualization using pre-computed bin edges
    and counts, rather than raw data. Useful for displaying distribution results
    that have already been binned during analysis.

    Args:
        bin_edges (list): Array of bin edge positions (length n+1 for n bins)
        counts (list): Array of counts for each bin (length n)
        title (str): Title for the histogram

    Returns:
        holoviews.Element: Histogram visualization or None if input is invalid
    """
    if len(bin_edges) != len(counts) + 1:
        # Bins edges should be one more than bin counts
        return None

    # Create bin centers for nicer labeling
    bin_centers = [
        (bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(bin_edges) - 1)
    ]

    # Try creating histogram with holoviews
    try:
        from holoviews import opts

        hist = hv.Histogram((bin_centers, counts), label=title)
        hist = hist.opts(
            opts.Histogram(
                width=600,
                height=400,
                fill_color="skyblue",
                line_color="darkblue",
                title=title,
            )
        )
        return hist
    except Exception:
        # Try the HTML fallback if HoloViews fails (likely in sandbox environment)
        try:
            from app.utils.plots import html_histogram

            return html_histogram(bin_edges, counts, title=title)
        except Exception:
            # Final fallback is a basic placeholder element
            return hv.Div(
                f"<div><strong>{title}</strong><br>Unable to display histogram</div>"
            )


def line_chart(df, x, y, title="Line Chart", x_label=None, y_label=None):
    """
    Create a line chart from a dataframe with x and y columns.

    Generates a HoloViews line chart visualization from a pandas DataFrame,
    with customizable labels and title. Automatically sorts the data by the
    x-axis values to ensure proper line rendering.

    Args:
        df (pandas.DataFrame): DataFrame containing the data to plot
        x (str): Column name for x-axis values
        y (str): Column name for y-axis values
        title (str): Title for the chart
        x_label (str, optional): Custom label for x-axis
        y_label (str, optional): Custom label for y-axis

    Returns:
        holoviews.Element: Line chart visualization
    """
    from holoviews import opts

    # Ensure sorted by x for proper lines
    df = df.sort_values(by=x)

    # Set labels
    if not x_label:
        x_label = x
    if not y_label:
        y_label = y

    # Create line chart
    line = hv.Curve(df, x, y).opts(
        opts.Curve(
            width=600,
            height=400,
            line_width=2,
            color="blue",
            xlabel=x_label,
            ylabel=y_label,
            title=title,
        )
    )
    return line


def combine_visualizations(visualizations, layout="grid"):
    """
    Combine multiple visualizations into a single layout.

    Takes a list of visualizations (HoloViews elements or Panel objects) and
    combines them into a single layout for display. Supports grid (2-column)
    or vertical (1-column) layouts, and handles mixed visualization types.

    Args:
        visualizations (list): List of visualization objects to combine
        layout (str): Layout type, either "grid" or "vertical"

    Returns:
        holoviews.Layout or panel.Column: Combined visualization layout,
            or None if no valid visualizations are provided
    """
    if not visualizations:
        return None

    # If only one visualization, just return it
    if len(visualizations) == 1:
        return visualizations[0]

    # Filter out None values
    valid_vizs = [v for v in visualizations if v is not None]
    if not valid_vizs:
        return None

    # For holoviews objects
    hv_vizs = [v for v in valid_vizs if isinstance(v, (hv.Element, hv.Layout))]
    if len(hv_vizs) == len(valid_vizs):
        # All visualizations are holoviews objects
        if layout == "grid":
            return hv.Layout(hv_vizs).cols(2)
        else:
            return hv.Layout(hv_vizs).cols(1)

    # Mix of holoviews and Panel objects
    return pn.Column(*valid_vizs)


def to_lbs(series):
    """
    Convert weight values from kg to lbs where needed.

    Intelligently detects whether a series of weight values is likely to be
    in kilograms (median value below 100) and converts to pounds if needed.
    This helps standardize weight units for analysis and display.

    Args:
        series (pandas.Series): Series of weight values

    Returns:
        pandas.Series: Weight values in pounds
    """
    if isinstance(series, pd.Series):
        if series.empty:
            return series

        try:
            median_val = series.median()
            if pd.isna(median_val):
                return series
            if median_val < 100:  # Very unlikely for adult body-weight in lbs
                return series * 2.20462
            return series
        except Exception as e:
            logger.warning(f"Error in to_lbs conversion: {e}")
            return series

    return series


def format_threshold_results(results, intent=None, show_narrative=True):
    """
    Format threshold query results for display.

    Specialized formatting for threshold queries that includes visualizations and
    statistics about the threshold comparison.

    Args:
        results: Threshold query results
        intent: Query intent that produced the results
        show_narrative: Whether to include narrative descriptions

    Returns:
        list: List of Panel components for display
    """
    formatted_results = []

    if not results:
        return formatted_results

    # Extract threshold information
    threshold_info = results.get("threshold_info", {})
    if not threshold_info:
        return formatted_results

    field = threshold_info.get("field", "value")
    direction = threshold_info.get("direction", "above")
    value = threshold_info.get("value", 0)

    # Get counts
    matching_count = results.get("matching_count", 0)
    if isinstance(matching_count, (pd.Series, np.ndarray)):
        matching_count = matching_count.iloc[0] if len(matching_count) > 0 else 0

    total_count = results.get("total_count", 0)
    percentage = results.get("percentage", 0)
    if percentage == 0 and total_count > 0:
        percentage = (matching_count / total_count) * 100

    # Add active patient information
    patient_status_text = ""

    # Check if we have active status information
    include_inactive = False
    active_only = False

    # Check intent or engine parameters
    if (
        intent is not None
        and hasattr(intent, "engine")
        and hasattr(intent.engine, "parameters")
    ):
        include_inactive = intent.engine.parameters.get("include_inactive", False)
        if not include_inactive:
            active_only = True

    # Also check the results dictionary, as some execution might set this directly
    if "include_inactive" in results:
        include_inactive = results.get("include_inactive", False)
        if not include_inactive:
            active_only = True

    if active_only:
        patient_status_text = " active"
    elif include_inactive:
        patient_status_text = " (including inactive)"

    # Create title and narrative
    title = f"Patients with {field} {direction.title()} {value}"

    if show_narrative:
        narrative = f"### {title}\n\nThere are **{matching_count:,}**{patient_status_text} patients with {field} {direction} {value}"
        if total_count > 0:
            narrative += f", representing **{percentage:.1f}%** of all patients"
        narrative += ".\n\n"
        formatted_results.append(pn.pane.Markdown(narrative))
    else:
        formatted_results.append(pn.pane.Markdown(f"### {title}"))
        stats = f"**Count:** {matching_count:,}{patient_status_text} patients\n"
        if total_count > 0:
            stats += f"**Percentage:** {percentage:.1f}%\n"
        formatted_results.append(pn.pane.Markdown(stats))

    # Add visualization if available
    viz = None
    if "hist_data" in results and "bin_edges" in results:
        try:
            # Create histogram visualization
            viz_title = f"Distribution of {field} with Threshold at {value}"
            viz = create_visualization_for_result(
                results, analysis_type="threshold", target_field=field
            )
            if viz is not None:
                formatted_results.append(viz)
        except Exception as e:
            logger.error(f"Error creating threshold visualization: {e}")

    # Add data table with key metrics
    metrics = {
        "Field": field,
        "Threshold": f"{direction.title()} {value}",
        "Matching Count": matching_count,
        "Total Count": total_count,
        "Percentage": f"{percentage:.1f}%",
    }

    # Add patient status information to metrics if available
    if active_only:
        metrics["Patient Status"] = "Active Only"
    elif include_inactive:
        metrics["Patient Status"] = "All Patients (Active & Inactive)"

    metrics_df = pd.DataFrame([metrics])
    formatted_results.append(
        pn.widgets.Tabulator(
            metrics_df,
            pagination="local",
            page_size=5,
            sizing_mode="stretch_width",
            theme="default",
        )
    )

    return formatted_results


def format_results(results, intent=None, show_narrative=True):
    """
    Format results for display based on type and intent.

    Main function for converting analysis results into Panel components for
    display. Handles different result types (scalar, dictionary, DataFrame)
    and formats them according to the analysis intent and display preferences.

    Args:
        results: Analysis results from code execution (any type)
        intent (QueryIntent, optional): The query intent that produced the results
        show_narrative (bool): Whether to include narrative descriptions

    Returns:
        list: List of Panel components ready for display in the UI
    """

    formatted_results = []

    # Get active/inactive status information
    include_inactive = False
    active_only = False
    patient_status_text = ""

    # Check intent or engine parameters
    if (
        intent is not None
        and hasattr(intent, "engine")
        and hasattr(intent.engine, "parameters")
    ):
        include_inactive = intent.engine.parameters.get("include_inactive", False)
        if not include_inactive:
            active_only = True
            patient_status_text = " for active patients"
        elif include_inactive:
            patient_status_text = " for all patients (active and inactive)"

    # Also check if the result dictionary contains active status information
    if isinstance(results, dict):
        if "include_inactive" in results:
            include_inactive = results.get("include_inactive", False)
            if not include_inactive:
                active_only = True
                patient_status_text = " for active patients"
            else:
                patient_status_text = " for all patients (active and inactive)"

    # Add narrative summary if available and enabled
    if show_narrative and intent is not None and hasattr(intent, "analysis_type"):
        try:
            # We would need access to the engine interpret_results method
            pass
        except Exception as e:
            logger.error(f"Error generating narrative: {e}")

    # Format results based on type
    if results is None:
        formatted_results.append(pn.pane.Markdown("No results available"))
    elif isinstance(results, (int, float)):
        # Check if this is a threshold query result but returned as scalar
        if (
            hasattr(intent, "engine")
            and hasattr(intent.engine, "threshold_info")
            and intent.engine.threshold_info
        ):
            # Wrap the scalar in a dictionary with threshold info
            wrapped_results = {
                "scalar": results,
                "threshold_info": intent.engine.threshold_info,
                "matching_count": results,  # Assuming the scalar is the count
                "total_count": 0,  # We don't know the total, will be updated if available
            }
            threshold_formatted = format_threshold_results(
                wrapped_results, intent, show_narrative
            )
            if threshold_formatted:
                return threshold_formatted

        # Format standard scalar result
        metric_type = (
            intent.analysis_type
            if intent and hasattr(intent, "analysis_type")
            else "value"
        )
        formatted = format_scalar_results(results, metric_type)

        # Add patient status to the label if available
        label = formatted["label"]
        if patient_status_text:
            if "active" not in label.lower():
                label += patient_status_text

        formatted_results.append(
            pn.pane.Markdown(f"### {label}\n\n**{formatted['value']}**")
        )
    elif isinstance(results, dict):
        # Check for threshold query results first
        if "threshold_info" in results:
            threshold_formatted = format_threshold_results(
                results, intent, show_narrative
            )
            if threshold_formatted:
                return threshold_formatted

        # Look for scalar field which might indicate a wrapped scalar result
        if "scalar" in results and isinstance(results["scalar"], (int, float)):
            # Check if we also have threshold info
            if "threshold_info" in results:
                threshold_formatted = format_threshold_results(
                    results, intent, show_narrative
                )
                if threshold_formatted:
                    return threshold_formatted

        # Format other dictionary result
        if "error" in results:
            formatted_results.append(
                pn.pane.Alert(
                    f"Error: {results['error']}",
                    alert_type="danger",
                    sizing_mode="stretch_width",
                )
            )

            if "traceback" in results:
                formatted_results.append(
                    pn.widgets.CodeEditor(
                        value=results["traceback"],
                        language="python",
                        sizing_mode="stretch_width",
                        theme="chrome",
                        readonly=True,
                        height=300,
                    )
                )
        else:
            # Process different result types
            analysis_type = (
                intent.analysis_type
                if intent and hasattr(intent, "analysis_type")
                else None
            )
            formatted = format_dict_results(results, analysis_type)

            if formatted["type"] == "visualization_with_data":
                # Add visualization
                viz = formatted["visualization"]
                if viz is not None:
                    formatted_results.append(viz)

                # Add data table
                data_dict = formatted["data"]
                if data_dict:
                    # Add patient status to the result data if available
                    if patient_status_text and "Patient Status" not in data_dict:
                        status_value = (
                            "Active Only"
                            if active_only
                            else "All Patients (Active & Inactive)"
                        )
                        data_dict["Patient Status"] = status_value

                    formatted_results.append(
                        pn.widgets.Tabulator(
                            pd.DataFrame([data_dict]),
                            pagination="local",
                            page_size=5,
                            sizing_mode="stretch_width",
                            theme="default",
                        )
                    )
            else:
                # Add patient status to the result data if available
                if (
                    patient_status_text
                    and isinstance(results, dict)
                    and "Patient Status" not in results
                ):
                    results_copy = results.copy()
                    status_value = (
                        "Active Only"
                        if active_only
                        else "All Patients (Active & Inactive)"
                    )
                    results_copy["Patient Status"] = status_value
                else:
                    results_copy = results

                # Format other dictionary types
                formatted_results.append(
                    pn.widgets.Tabulator(
                        pd.DataFrame([results_copy]),
                        pagination="local",
                        page_size=5,
                        sizing_mode="stretch_width",
                        theme="default",
                    )
                )
    elif hasattr(results, "to_dict"):  # DataFrame-like
        # Format DataFrame result
        formatted = format_dataframe_results(results)

        # Add header with patient status if available
        if patient_status_text:
            formatted_results.append(
                pn.pane.Markdown(f"### Results{patient_status_text}")
            )

        formatted_results.append(
            pn.widgets.Tabulator(
                results,
                pagination="local",
                page_size=10,
                sizing_mode="stretch_width",
                theme="default",
            )
        )
    else:
        # Default display
        label = "Result"
        if patient_status_text:
            label += patient_status_text
        formatted_results.append(pn.pane.Markdown(f"**{label}:** {results}"))

    return formatted_results
