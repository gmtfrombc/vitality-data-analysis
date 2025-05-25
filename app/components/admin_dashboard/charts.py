"""
Chart components for the admin monitoring dashboard.

This module provides Bokeh-based interactive charts for displaying
historical trends and time-series data.
"""

import panel as pn
import param
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import HoverTool, DatetimeTickFormatter
from bokeh.palettes import Category10
from typing import Dict, List

from app.services.metrics_collector import MetricsCollector


class TimeSeriesChart(param.Parameterized):
    """Interactive time-series chart for metrics visualization."""

    # Parameters for reactive updates
    time_range = param.ObjectSelector(
        default="24h",
        objects=["24h", "7d", "30d", "90d"],
        doc="Time range for chart data",
    )

    selected_metrics = param.List(
        default=["response_time_ms", "error_rate"], doc="List of metrics to display"
    )

    def __init__(self, **params):
        super().__init__(**params)
        self.metrics_collector = MetricsCollector()
        self.chart_pane = pn.pane.Bokeh(sizing_mode="stretch_width", height=400)
        self._setup_chart()

        # Watch for parameter changes
        self.param.watch(self._update_chart, ["time_range", "selected_metrics"])

    def _setup_chart(self):
        """Set up the initial chart."""
        self._update_chart()

    def _update_chart(self, *events):
        """Update chart with current data."""
        try:
            # Get time range in hours
            hours = self._parse_time_range(self.time_range)

            # Get historical data
            data = self.metrics_collector.get_historical_data(
                metric_names=self.selected_metrics, hours=hours
            )

            # Create chart
            chart = self._create_bokeh_chart(data, hours)
            self.chart_pane.object = chart

        except Exception as e:
            # Show error in chart
            error_chart = self._create_error_chart(str(e))
            self.chart_pane.object = error_chart

    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to hours."""
        if time_range == "24h":
            return 24
        elif time_range == "7d":
            return 24 * 7
        elif time_range == "30d":
            return 24 * 30
        elif time_range == "90d":
            return 24 * 90
        else:
            return 24

    def _create_bokeh_chart(self, data: Dict[str, List[Dict]], hours: int) -> figure:
        """Create Bokeh chart from data."""
        # Create figure
        p = figure(
            title=f"Performance Metrics - Last {self.time_range}",
            x_axis_type="datetime",
            width=800,
            height=400,
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        # Color palette for multiple metrics
        colors = Category10[max(3, len(self.selected_metrics))]

        # Add line for each metric
        for i, metric_name in enumerate(self.selected_metrics):
            if metric_name in data and data[metric_name]:
                metric_data = data[metric_name]

                # Convert to pandas for easier handling
                df = pd.DataFrame(metric_data)
                df["timestamp"] = pd.to_datetime(df["timestamp"])

                # Add line to chart
                line = p.line(
                    x="timestamp",
                    y="value",
                    source=df,
                    legend_label=self._format_metric_name(metric_name),
                    line_width=2,
                    color=colors[i % len(colors)],
                )

                # Add circle markers
                p.circle(
                    x="timestamp",
                    y="value",
                    source=df,
                    size=4,
                    color=colors[i % len(colors)],
                    alpha=0.6,
                )

                # Add hover tool for this line
                hover = HoverTool(
                    tooltips=[
                        ("Metric", metric_name),
                        ("Time", "@timestamp{%F %T}"),
                        ("Value", "@value{0.00}"),
                        ("Unit", f"{metric_data[0].get('unit', '')}"),
                    ],
                    formatters={"@timestamp": "datetime"},
                    renderers=[line],
                )
                p.add_tools(hover)

        # Customize chart appearance
        p.title.text_font_size = "16pt"
        p.legend.location = "top_left"
        p.legend.click_policy = "hide"

        # Format x-axis
        p.xaxis.formatter = DatetimeTickFormatter(
            hours="%H:%M", days="%m/%d", months="%m/%Y"
        )

        # Set y-axis label
        p.yaxis.axis_label = "Value"

        return p

    def _format_metric_name(self, metric_name: str) -> str:
        """Format metric name for display."""
        name_map = {
            "response_time_ms": "Response Time (ms)",
            "error_rate": "Error Rate (%)",
            "cache_hit_rate": "Cache Hit Rate (%)",
            "pattern_lookup_ms": "Pattern Lookup (ms)",
            "active_patterns": "Active Patterns",
            "pattern_accuracy": "Pattern Accuracy (%)",
        }
        return name_map.get(metric_name, metric_name.replace("_", " ").title())

    def _create_error_chart(self, error_message: str) -> figure:
        """Create error chart when data loading fails."""
        p = figure(title="Chart Error", width=800, height=400, tools="")

        # Add error text
        p.text(
            x=[0.5],
            y=[0.5],
            text=[f"Error loading chart data: {error_message}"],
            text_align="center",
            text_baseline="middle",
        )

        # Remove axes
        p.xaxis.visible = False
        p.yaxis.visible = False
        p.grid.visible = False

        return p

    def get_panel(self):
        """Get Panel layout for the chart."""
        # Time range selector
        time_selector = pn.widgets.RadioButtonGroup(
            name="Time Range",
            options=["24h", "7d", "30d", "90d"],
            value=self.time_range,
            button_type="primary",
        )
        time_selector.link(self, value="time_range")

        # Metric selector
        metric_options = [
            "response_time_ms",
            "error_rate",
            "cache_hit_rate",
            "pattern_lookup_ms",
            "active_patterns",
            "pattern_accuracy",
        ]

        metric_selector = pn.widgets.CheckBoxGroup(
            name="Metrics to Display",
            options=metric_options,
            value=self.selected_metrics,
        )
        metric_selector.link(self, value="selected_metrics")

        # Refresh button
        refresh_button = pn.widgets.Button(
            name="🔄 Refresh Chart", button_type="primary", width=120
        )
        refresh_button.on_click(lambda event: self._update_chart())

        # Controls panel
        controls = pn.Row(time_selector, refresh_button, sizing_mode="stretch_width")

        metrics_panel = pn.Column(metric_selector, width=200)

        # Main layout
        return pn.Column(
            "## 📈 Historical Trends",
            controls,
            pn.Row(self.chart_pane, metrics_panel, sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
        )


class PerformanceChartsPanel(param.Parameterized):
    """Panel containing multiple performance charts."""

    def __init__(self, **params):
        super().__init__(**params)
        self.setup_charts()

    def setup_charts(self):
        """Set up multiple chart panels."""
        # Response time and error rate chart
        self.performance_chart = TimeSeriesChart(
            selected_metrics=["response_time_ms", "error_rate"],
            name="Performance Metrics",
        )

        # Cache and pattern metrics chart
        self.cache_chart = TimeSeriesChart(
            selected_metrics=["cache_hit_rate", "pattern_lookup_ms"],
            name="Cache & Pattern Metrics",
        )

        # Learning system metrics chart
        self.learning_chart = TimeSeriesChart(
            selected_metrics=["active_patterns", "pattern_accuracy"],
            name="Learning System Metrics",
        )

    def get_panel(self):
        """Get complete charts panel."""
        return pn.Column(
            self.performance_chart.get_panel(),
            pn.Spacer(height=20),
            self.cache_chart.get_panel(),
            pn.Spacer(height=20),
            self.learning_chart.get_panel(),
            sizing_mode="stretch_width",
        )
