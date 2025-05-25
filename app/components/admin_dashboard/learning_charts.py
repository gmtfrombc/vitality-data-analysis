"""
Learning Charts Component for Admin Dashboard

Provides interactive charts and visualizations for learning system analytics.

Sprint 2.2 Features:
- Pattern effectiveness charts
- Correction success trend charts
- Learning progress indicators
- User feedback visualization
"""

import panel as pn
from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource
from bokeh.palettes import Category10
from typing import Optional
import logging

from app.services.learning_analytics import LearningAnalyticsService

logger = logging.getLogger(__name__)

pn.extension("bokeh")


class LearningChartsPanel:
    """Panel for learning system analytics charts."""

    def __init__(self, analytics_service: Optional[LearningAnalyticsService] = None):
        """Initialize the learning charts panel.

        Args:
            analytics_service: Optional analytics service (for testing)
        """
        self.analytics_service = analytics_service or LearningAnalyticsService()

        # Create UI components
        self._create_components()

    def _create_components(self):
        """Create all UI components."""
        # Time period selector
        self.time_selector = pn.widgets.IntSlider(
            name="Analysis Period (days)", value=30, start=7, end=90, step=7, width=300
        )

        # Chart containers
        self.pattern_effectiveness_chart = pn.pane.Bokeh(
            self._create_pattern_effectiveness_chart(), width=600, height=400
        )

        self.correction_trends_chart = pn.pane.Bokeh(
            self._create_correction_trends_chart(), width=600, height=400
        )

        self.learning_progress_chart = pn.pane.Bokeh(
            self._create_learning_progress_chart(), width=600, height=400
        )

        # Metrics cards
        self.metrics_cards = self._create_metrics_cards()

        # Bind update function to time selector
        self.time_selector.param.watch(self._update_charts, "value")

    def _create_pattern_effectiveness_chart(self):
        """Create pattern effectiveness chart."""
        try:
            # Get pattern effectiveness data
            patterns = self.analytics_service.get_pattern_effectiveness(
                self.time_selector.value
            )

            if not patterns:
                # Create empty chart
                p = figure(
                    title="Pattern Effectiveness",
                    x_axis_label="Pattern ID",
                    y_axis_label="Success Rate",
                    width=580,
                    height=380,
                )
                p.text(
                    [0.5],
                    [0.5],
                    text=["No pattern data available"],
                    text_align="center",
                    text_baseline="middle",
                )
                return p

            # Prepare data
            pattern_ids = [
                p.pattern_id[:10] + "..." if len(p.pattern_id) > 10 else p.pattern_id
                for p in patterns
            ]
            success_rates = [p.success_rate for p in patterns]
            total_apps = [p.total_applications for p in patterns]
            pattern_types = [p.pattern_type for p in patterns]
            trends = [p.trend for p in patterns]

            # Create chart
            p = figure(
                x_range=pattern_ids,
                title="Pattern Effectiveness by Success Rate",
                x_axis_label="Pattern ID",
                y_axis_label="Success Rate",
                width=580,
                height=380,
            )

            # Color by trend
            colors = []
            for trend in trends:
                if trend == "improving":
                    colors.append("green")
                elif trend == "declining":
                    colors.append("red")
                else:
                    colors.append("blue")

            # Create bars
            source = ColumnDataSource(
                data=dict(
                    pattern_ids=pattern_ids,
                    success_rates=success_rates,
                    total_apps=total_apps,
                    pattern_types=pattern_types,
                    trends=trends,
                    colors=colors,
                )
            )

            bars = p.vbar(
                x="pattern_ids",
                top="success_rates",
                width=0.8,
                color="colors",
                source=source,
            )

            # Add hover tool
            hover = HoverTool(
                tooltips=[
                    ("Pattern ID", "@pattern_ids"),
                    ("Success Rate", "@success_rates{0.0%}"),
                    ("Total Applications", "@total_apps"),
                    ("Pattern Type", "@pattern_types"),
                    ("Trend", "@trends"),
                ],
                renderers=[bars],
            )
            p.add_tools(hover)

            # Styling
            p.xgrid.grid_line_color = None
            p.xaxis.major_label_orientation = 45

            return p

        except Exception as e:
            logger.error(f"Error creating pattern effectiveness chart: {e}")
            # Return empty chart on error
            p = figure(title="Pattern Effectiveness", width=580, height=380)
            p.text(
                [0.5],
                [0.5],
                text=[f"Error: {str(e)}"],
                text_align="center",
                text_baseline="middle",
            )
            return p

    def _create_correction_trends_chart(self):
        """Create correction trends chart."""
        try:
            # Get correction analysis data
            analysis = self.analytics_service.get_correction_analysis(
                self.time_selector.value
            )

            # Create chart showing correction types
            if not analysis.common_correction_types:
                p = figure(title="Correction Types Distribution", width=580, height=380)
                p.text(
                    [0.5],
                    [0.5],
                    text=["No correction data available"],
                    text_align="center",
                    text_baseline="middle",
                )
                return p

            # Prepare data for pie chart (using wedges)
            types = [ct["type"] for ct in analysis.common_correction_types]
            counts = [ct["count"] for ct in analysis.common_correction_types]
            percentages = [ct["percentage"] for ct in analysis.common_correction_types]

            # Create horizontal bar chart instead of pie chart for better readability
            p = figure(
                y_range=types,
                title="Most Common Correction Types",
                x_axis_label="Number of Corrections",
                y_axis_label="Correction Type",
                width=580,
                height=380,
            )

            source = ColumnDataSource(
                data=dict(types=types, counts=counts, percentages=percentages)
            )

            # Get colors for the bars
            colors = (
                Category10[max(3, len(types))] if len(types) <= 10 else Category10[10]
            )
            bar_colors = colors[: len(types)]

            bars = p.hbar(
                y="types", right="counts", height=0.8, color=bar_colors, source=source
            )

            # Add hover tool
            hover = HoverTool(
                tooltips=[
                    ("Correction Type", "@types"),
                    ("Count", "@counts"),
                    ("Percentage", "@percentages{0.0}%"),
                ],
                renderers=[bars],
            )
            p.add_tools(hover)

            return p

        except Exception as e:
            logger.error(f"Error creating correction trends chart: {e}")
            p = figure(title="Correction Trends", width=580, height=380)
            p.text(
                [0.5],
                [0.5],
                text=[f"Error: {str(e)}"],
                text_align="center",
                text_baseline="middle",
            )
            return p

    def _create_learning_progress_chart(self):
        """Create learning progress chart."""
        try:
            # Get learning progress data
            progress = self.analytics_service.get_learning_progress(
                self.time_selector.value
            )

            # Create milestone progress chart
            milestones = progress.milestone_progress

            if not milestones:
                p = figure(title="Learning Progress Milestones", width=580, height=380)
                p.text(
                    [0.5],
                    [0.5],
                    text=["No milestone data available"],
                    text_align="center",
                    text_baseline="middle",
                )
                return p

            # Prepare data
            milestone_names = []
            current_values = []
            target_values = []
            progress_percentages = []

            for milestone_id, milestone_data in milestones.items():
                milestone_names.append(milestone_data["description"])
                current_values.append(milestone_data["current"])
                target_values.append(milestone_data["target"])

                # Calculate progress percentage
                if milestone_data["target"] > 0:
                    progress_pct = min(
                        100,
                        (milestone_data["current"] / milestone_data["target"]) * 100,
                    )
                else:
                    progress_pct = 0
                progress_percentages.append(progress_pct)

            # Create horizontal progress bars
            p = figure(
                y_range=milestone_names,
                title="Learning Progress Milestones",
                x_axis_label="Progress (%)",
                y_axis_label="Milestone",
                width=580,
                height=380,
            )

            source = ColumnDataSource(
                data=dict(
                    milestone_names=milestone_names,
                    current_values=current_values,
                    target_values=target_values,
                    progress_percentages=progress_percentages,
                )
            )

            # Background bars (targets)
            p.hbar(
                y="milestone_names",
                right=100,  # Full width
                height=0.6,
                color="lightgray",
                alpha=0.3,
                source=source,
            )

            # Progress bars
            bars = p.hbar(
                y="milestone_names",
                right="progress_percentages",
                height=0.6,
                color="green",
                source=source,
            )

            # Add hover tool
            hover = HoverTool(
                tooltips=[
                    ("Milestone", "@milestone_names"),
                    ("Current", "@current_values"),
                    ("Target", "@target_values"),
                    ("Progress", "@progress_percentages{0.0}%"),
                ],
                renderers=[bars],
            )
            p.add_tools(hover)

            # Set x-axis range
            p.x_range.start = 0
            p.x_range.end = 100

            return p

        except Exception as e:
            logger.error(f"Error creating learning progress chart: {e}")
            p = figure(title="Learning Progress", width=580, height=380)
            p.text(
                [0.5],
                [0.5],
                text=[f"Error: {str(e)}"],
                text_align="center",
                text_baseline="middle",
            )
            return p

    def _create_metrics_cards(self):
        """Create metrics summary cards."""
        try:
            # Get current metrics
            progress = self.analytics_service.get_learning_progress(
                self.time_selector.value
            )
            analysis = self.analytics_service.get_correction_analysis(
                self.time_selector.value
            )

            # Create cards
            cards = pn.Row(
                pn.pane.HTML(
                    f"""
                <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; text-align: center; margin: 5px;">
                    <h3 style="margin: 0; color: #2e7d32;">Learning Rate</h3>
                    <h2 style="margin: 5px 0; color: #1b5e20;">{progress.overall_learning_rate:.1%}</h2>
                    <p style="margin: 0; color: #388e3c;">Overall Success Rate</p>
                </div>
                """,
                    width=180,
                    height=120,
                ),
                pn.pane.HTML(
                    f"""
                <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; text-align: center; margin: 5px;">
                    <h3 style="margin: 0; color: #1976d2;">New Patterns</h3>
                    <h2 style="margin: 5px 0; color: #0d47a1;">{progress.patterns_learned}</h2>
                    <p style="margin: 0; color: #1565c0;">Last {self.time_selector.value} days</p>
                </div>
                """,
                    width=180,
                    height=120,
                ),
                pn.pane.HTML(
                    f"""
                <div style="background: #fff3e0; padding: 15px; border-radius: 8px; text-align: center; margin: 5px;">
                    <h3 style="margin: 0; color: #f57c00;">Corrections</h3>
                    <h2 style="margin: 5px 0; color: #e65100;">{analysis.successful_corrections}</h2>
                    <p style="margin: 0; color: #ff9800;">Successful</p>
                </div>
                """,
                    width=180,
                    height=120,
                ),
                pn.pane.HTML(
                    f"""
                <div style="background: #f3e5f5; padding: 15px; border-radius: 8px; text-align: center; margin: 5px;">
                    <h3 style="margin: 0; color: #7b1fa2;">Learning Velocity</h3>
                    <h2 style="margin: 5px 0; color: #4a148c;">{progress.learning_velocity:.1f}</h2>
                    <p style="margin: 0; color: #8e24aa;">Patterns/day</p>
                </div>
                """,
                    width=180,
                    height=120,
                ),
            )

            return cards

        except Exception as e:
            logger.error(f"Error creating metrics cards: {e}")
            return pn.pane.HTML("<p>Error loading metrics</p>")

    def _update_charts(self, event):
        """Update all charts when time period changes."""
        try:
            # Update charts
            self.pattern_effectiveness_chart.object = (
                self._create_pattern_effectiveness_chart()
            )
            self.correction_trends_chart.object = self._create_correction_trends_chart()
            self.learning_progress_chart.object = self._create_learning_progress_chart()

            # Update metrics cards
            self.metrics_cards[:] = [self._create_metrics_cards()]

        except Exception as e:
            logger.error(f"Error updating charts: {e}")

    def get_panel(self):
        """Get the complete learning charts panel."""
        return pn.Column(
            pn.pane.HTML("<h2>🧠 Learning System Analytics</h2>"),
            self.time_selector,
            self.metrics_cards,
            pn.Row(self.pattern_effectiveness_chart, self.correction_trends_chart),
            self.learning_progress_chart,
            width=1200,
        )
