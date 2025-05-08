"""Dashboard for Assistant Evaluation Framework.

Part of *WS-6 Continuous Feedback & Evaluation* work stream.

This component provides visualizations and insights from the Assistant Evaluation Framework,
allowing stakeholders to track performance metrics over time and identify improvement areas.
"""

import panel as pn
import param
import pandas as pd
import holoviews as hv
from typing import Optional

from app.utils.evaluation_framework import (
    compute_all_metrics,
    load_metrics_history,
    SATISFACTION_METRICS,
    RESPONSE_METRICS,
    INTENT_METRICS,
    QUERY_PATTERN_METRICS,
    VISUALIZATION_METRICS,
)

# Initialize rendering backend for HoloViews plots
hv.extension("bokeh")


class EvaluationDashboard(param.Parameterized):
    """Dashboard for visualizing assistant evaluation metrics."""

    # Parameters
    time_period = param.Selector(
        default="30",
        objects=["7", "30", "90"],
        doc="Time period for metrics display (days)",
    )

    refresh_triggered = param.Boolean(default=False)

    def __init__(self, **params):
        """Initialize the dashboard."""
        super().__init__(**params)

        # Create UI components
        self._create_components()

    def _create_components(self):
        """Create all UI components for the dashboard."""
        # Header
        self.header = pn.pane.Markdown(
            "# Assistant Evaluation Dashboard", sizing_mode="stretch_width"
        )

        # Controls
        self.period_select = pn.widgets.RadioButtonGroup(
            options=["Last 7 days", "Last 30 days", "Last 90 days"],
            value="Last 30 days",
        )
        self.period_select.param.watch(self._on_period_change, "value")

        self.refresh_button = pn.widgets.Button(
            name="Refresh Data", button_type="primary", width=120
        )
        self.refresh_button.on_click(self._on_refresh)

        # Metrics cards
        self.satisfaction_card = pn.Card(
            title="User Satisfaction", sizing_mode="stretch_width"
        )

        self.response_card = pn.Card(
            title="Response Quality", sizing_mode="stretch_width"
        )

        self.intent_card = pn.Card(
            title="Intent Classification", sizing_mode="stretch_width"
        )

        self.query_patterns_card = pn.Card(
            title="Query Patterns", sizing_mode="stretch_width"
        )

        self.visualization_card = pn.Card(
            title="Visualization Effectiveness", sizing_mode="stretch_width"
        )

        # Initial data load
        self._load_data()

    def _on_period_change(self, event):
        """Handle period change events."""
        mapping = {"Last 7 days": "7", "Last 30 days": "30", "Last 90 days": "90"}
        self.time_period = mapping.get(event.new, "30")
        self._load_data()

    def _on_refresh(self, event):
        """Handle refresh button click."""
        self.refresh_triggered = not self.refresh_triggered
        self._load_data()

    def _load_data(self):
        """Load and prepare data for visualization."""
        days = int(self.time_period)

        # Get latest metrics
        self.current_metrics = compute_all_metrics(days=days)

        # Load historical data for trends
        self.metrics_history = {
            SATISFACTION_METRICS: load_metrics_history(
                SATISFACTION_METRICS, days=max(90, days)
            ),
            RESPONSE_METRICS: load_metrics_history(
                RESPONSE_METRICS, days=max(90, days)
            ),
            INTENT_METRICS: load_metrics_history(INTENT_METRICS, days=max(90, days)),
            VISUALIZATION_METRICS: load_metrics_history(
                VISUALIZATION_METRICS, days=max(90, days)
            ),
        }

        # Update visualization components
        self._update_visualizations()

    def _update_visualizations(self):
        """Update all visualization components with current data."""
        self._update_satisfaction_card()
        self._update_response_card()
        self._update_intent_card()
        self._update_query_patterns_card()
        self._update_visualization_card()

    def _update_satisfaction_card(self):
        """Update satisfaction metrics visualization."""
        metrics = self.current_metrics[SATISFACTION_METRICS]

        # Create KPI indicators
        satisfaction_rate = f"{metrics['satisfaction_rate'] * 100:.1f}%"
        feedback_count = f"{metrics['feedback_count']}"

        satisfaction_indicator = pn.indicators.Number(
            name="Satisfaction Rate",
            value=metrics["satisfaction_rate"] * 100,
            format="{value:.1f}%",
            colors=[(0, "red"), (70, "orange"), (90, "green")],
            sizing_mode="stretch_width",
        )

        feedback_indicator = pn.indicators.Number(
            name="Total Feedback",
            value=metrics["feedback_count"],
            format="{value}",
            sizing_mode="stretch_width",
        )

        # Create trend chart if we have history
        trend_chart = self._create_metric_trend(
            self.metrics_history[SATISFACTION_METRICS],
            "satisfaction_rate",
            "Satisfaction Rate Over Time",
            formatter=lambda x: f"{x*100:.1f}%",
        )

        # Update card contents
        self.satisfaction_card.object = pn.Column(
            pn.Row(satisfaction_indicator, feedback_indicator),
            pn.layout.Divider(),
            (
                trend_chart
                if trend_chart
                else pn.pane.Markdown("*No historical data available*")
            ),
            sizing_mode="stretch_width",
        )

    def _update_response_card(self):
        """Update response metrics visualization."""
        metrics = self.current_metrics[RESPONSE_METRICS]

        # Create KPI indicators
        response_time = pn.indicators.Number(
            name="Avg Response Time",
            value=metrics["avg_response_time_ms"],
            format="{value:.0f} ms",
            sizing_mode="stretch_width",
        )

        query_count = pn.indicators.Number(
            name="Total Queries",
            value=metrics["query_count"],
            format="{value}",
            sizing_mode="stretch_width",
        )

        # Create trend chart
        trend_chart = self._create_metric_trend(
            self.metrics_history[RESPONSE_METRICS],
            "avg_response_time_ms",
            "Response Time Trend",
            formatter=lambda x: f"{x:.0f} ms",
        )

        # Update card contents
        self.response_card.object = pn.Column(
            pn.Row(response_time, query_count),
            pn.layout.Divider(),
            (
                trend_chart
                if trend_chart
                else pn.pane.Markdown("*No historical data available*")
            ),
            sizing_mode="stretch_width",
        )

    def _update_intent_card(self):
        """Update intent classification visualization."""
        metrics = self.current_metrics[INTENT_METRICS]

        # Create KPI indicators
        clarification_rate = pn.indicators.Number(
            name="Clarification Rate",
            value=metrics["clarification_rate"] * 100,
            format="{value:.1f}%",
            sizing_mode="stretch_width",
        )

        multi_metric_rate = pn.indicators.Number(
            name="Multi-Metric Rate",
            value=metrics["multi_metric_rate"] * 100,
            format="{value:.1f}%",
            sizing_mode="stretch_width",
        )

        # Create intent distribution chart
        intent_dist = metrics.get("intent_distribution", {})
        if intent_dist:
            data = pd.DataFrame(
                {
                    "Intent": list(intent_dist.keys()),
                    "Count": list(intent_dist.values()),
                }
            ).sort_values("Count", ascending=False)

            intent_chart = hv.Bars(data, "Intent", "Count")
            intent_chart = intent_chart.opts(
                title="Intent Distribution",
                width=400,
                height=300,
                xrotation=45,
                color="skyblue",
            )
        else:
            intent_chart = pn.pane.Markdown("*No intent distribution data available*")

        # Update card contents
        self.intent_card.object = pn.Column(
            pn.Row(clarification_rate, multi_metric_rate),
            pn.layout.Divider(),
            intent_chart,
            sizing_mode="stretch_width",
        )

    def _update_query_patterns_card(self):
        """Update query patterns visualization."""
        metrics = self.current_metrics[QUERY_PATTERN_METRICS]

        # Create KPI indicators
        query_length = pn.indicators.Number(
            name="Avg Query Length",
            value=metrics["query_length_avg"],
            format="{value:.1f} chars",
            sizing_mode="stretch_width",
        )

        query_complexity = pn.indicators.Number(
            name="Query Complexity",
            value=metrics["query_complexity"],
            format="{value:.2f}",
            sizing_mode="stretch_width",
        )

        # Create keyword chart
        keywords = metrics.get("common_keywords", {})
        if keywords:
            data = (
                pd.DataFrame(
                    {"Keyword": list(keywords.keys()), "Count": list(keywords.values())}
                )
                .sort_values("Count", ascending=False)
                .head(10)
            )

            keyword_chart = hv.Bars(data, "Keyword", "Count")
            keyword_chart = keyword_chart.opts(
                title="Top 10 Keywords in Queries",
                width=400,
                height=300,
                xrotation=45,
                color="lightgreen",
            )
        else:
            keyword_chart = pn.pane.Markdown("*No keyword data available*")

        # Update card contents
        self.query_patterns_card.object = pn.Column(
            pn.Row(query_length, query_complexity),
            pn.layout.Divider(),
            keyword_chart,
            sizing_mode="stretch_width",
        )

    def _update_visualization_card(self):
        """Update visualization effectiveness metrics."""
        metrics = self.current_metrics[VISUALIZATION_METRICS]

        # Create KPI indicators
        vis_rate = pn.indicators.Number(
            name="Visualization Rate",
            value=metrics["visualization_rate"] * 100,
            format="{value:.1f}%",
            sizing_mode="stretch_width",
        )

        vis_satisfaction = pn.indicators.Number(
            name="Visualization Satisfaction",
            value=metrics["visualized_satisfaction"] * 100,
            format="{value:.1f}%",
            colors=[(0, "red"), (70, "orange"), (90, "green")],
            sizing_mode="stretch_width",
        )

        # Create trend chart
        trend_chart = self._create_metric_trend(
            self.metrics_history[VISUALIZATION_METRICS],
            "visualization_rate",
            "Visualization Rate Trend",
            formatter=lambda x: f"{x*100:.1f}%",
        )

        # Update card contents
        self.visualization_card.object = pn.Column(
            pn.Row(vis_rate, vis_satisfaction),
            pn.layout.Divider(),
            (
                trend_chart
                if trend_chart
                else pn.pane.Markdown("*No historical data available*")
            ),
            sizing_mode="stretch_width",
        )

    def _create_metric_trend(
        self,
        history_df: pd.DataFrame,
        metric_name: str,
        title: str,
        formatter=lambda x: f"{x}",
    ) -> Optional[pn.viewable.Viewable]:
        """Create a trend chart for a metric if history data is available."""
        if history_df.empty:
            return None

        # Filter for this specific metric
        df = history_df[history_df["metric_name"] == metric_name].copy()

        if df.empty:
            return None

        # Sort by time
        df = df.sort_values("period_end")

        # Create curve
        curve = hv.Curve(
            data=(df["period_end"], df["metric_value"]), kdims=["Date"], vdims=["Value"]
        )

        curve = curve.opts(
            title=title, width=500, height=250, tools=["hover"], color="blue"
        )

        return curve

    def view(self) -> pn.viewable.Viewable:
        """Return the complete dashboard view."""
        controls = pn.Row(
            pn.pane.Markdown("### Time Period:"),
            self.period_select,
            self.refresh_button,
            sizing_mode="stretch_width",
        )

        # Layout cards in grid
        grid = pn.GridSpec(height=900, width=1000)

        # Row 1 (satisfaction and response)
        grid[0, 0:3] = self.satisfaction_card
        grid[0, 3:6] = self.response_card

        # Row 2 (intent and query patterns)
        grid[1, 0:3] = self.intent_card
        grid[1, 3:6] = self.query_patterns_card

        # Row 3 (visualization effectiveness)
        grid[2, 1:5] = self.visualization_card

        return pn.Column(
            self.header,
            controls,
            pn.layout.Divider(),
            grid,
            sizing_mode="stretch_width",
        )


def evaluation_dashboard() -> pn.viewable.Viewable:
    """Create and return the assistant evaluation dashboard.

    Returns
    -------
    panel.viewable.Viewable
        The dashboard component
    """
    dashboard = EvaluationDashboard()
    return dashboard.view()
