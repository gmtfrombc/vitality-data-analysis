"""
Main Admin Dashboard Tab

This module provides the main dashboard tab that integrates into the existing
Panel application, providing health status monitoring and system overview.
"""

import panel as pn
import param
from typing import Dict, Any

from app.services.dashboard_service import DashboardService


class AdminDashboardTab(param.Parameterized):
    """Main admin dashboard tab for Panel application."""

    # Reactive parameters for real-time updates
    health_status = param.Dict(default={})
    last_refresh = param.String(default="Never")
    auto_refresh_enabled = param.Boolean(default=True)

    def __init__(self, **params):
        super().__init__(**params)
        self.dashboard_service = DashboardService()
        self._setup_layout()
        self._refresh_data()

    def _setup_layout(self):
        """Set up the dashboard layout."""
        # Overall status indicator
        self.status_indicator = pn.pane.HTML(
            "<div style='text-align: center; font-size: 24px; padding: 20px;'>"
            "🔄 Loading system status..."
            "</div>",
            sizing_mode="stretch_width",
        )

        # Component status cards
        self.component_cards = pn.Row(sizing_mode="stretch_width")

        # Metrics summary
        self.metrics_summary = pn.pane.HTML(
            "<div style='padding: 10px;'>Loading metrics...</div>",
            sizing_mode="stretch_width",
        )

        # Control buttons
        self.refresh_button = pn.widgets.Button(
            name="🔄 Refresh Now", button_type="primary", sizing_mode="fixed", width=150
        )
        self.refresh_button.on_click(self._manual_refresh)

        # Auto-refresh toggle
        self.auto_refresh_toggle = pn.widgets.Checkbox(
            name="Auto-refresh (5 min)", value=True, sizing_mode="fixed"
        )

        # Last updated indicator
        self.last_updated = pn.pane.HTML("Last updated: Never", sizing_mode="fixed")

        # Control panel
        self.controls = pn.Row(
            self.refresh_button,
            self.auto_refresh_toggle,
            self.last_updated,
            sizing_mode="stretch_width",
        )

    def _refresh_data(self):
        """Refresh dashboard data from service."""
        try:
            health_status = self.dashboard_service.get_health_status()
            self._update_status_indicator(health_status)
            self._update_component_cards(health_status)
            self._update_metrics_summary(health_status)
            self._update_last_updated(health_status.last_updated)

        except Exception as e:
            self._show_error(f"Failed to refresh data: {e}")

    def _update_status_indicator(self, health_status):
        """Update the main status indicator."""
        status = health_status.overall_status

        if status == "healthy":
            color = "#28a745"  # Green
            icon = "✅"
            message = "System Healthy"
        elif status == "warning":
            color = "#ffc107"  # Yellow
            icon = "⚠️"
            message = "System Warning"
        else:  # critical
            color = "#dc3545"  # Red
            icon = "❌"
            message = "System Critical"

        html = f"""
        <div style='text-align: center; padding: 30px; background-color: {color}20; 
                    border: 2px solid {color}; border-radius: 10px; margin: 10px;'>
            <div style='font-size: 48px; margin-bottom: 10px;'>{icon}</div>
            <div style='font-size: 24px; font-weight: bold; color: {color};'>{message}</div>
            <div style='font-size: 14px; margin-top: 10px; color: #666;'>
                Overall system status
            </div>
        </div>
        """

        self.status_indicator.object = html

    def _update_component_cards(self, health_status):
        """Update component status cards."""
        cards = []

        for component_name, component_data in health_status.components.items():
            card_html = self._create_component_card(component_name, component_data)
            cards.append(pn.pane.HTML(card_html, sizing_mode="stretch_width"))

        self.component_cards.objects = cards

    def _create_component_card(self, name: str, data: Dict[str, Any]) -> str:
        """Create HTML for a component status card."""
        display_name = name.replace("_", " ").title()
        icon = data.get("icon", "❓")
        status = data.get("status", "unknown")

        # Additional info based on component
        extra_info = ""
        if name == "database":
            response_time = data.get("response_time_ms", 0)
            extra_info = f"Response: {response_time}ms"
        elif name == "pattern_learning":
            patterns = data.get("active_patterns", 0)
            extra_info = f"Active patterns: {patterns}"
        elif name == "cache":
            hit_rate = data.get("hit_rate", 0)
            extra_info = f"Hit rate: {hit_rate:.1%}"

        return f"""
        <div style='border: 1px solid #ddd; border-radius: 8px; padding: 15px; 
                    margin: 5px; background-color: #f8f9fa;'>
            <div style='text-align: center; font-size: 32px; margin-bottom: 10px;'>{icon}</div>
            <div style='text-align: center; font-weight: bold; font-size: 16px;'>{display_name}</div>
            <div style='text-align: center; color: #666; font-size: 14px;'>{status}</div>
            {f'<div style="text-align: center; color: #888; font-size: 12px; margin-top: 5px;">{extra_info}</div>' if extra_info else ''}
        </div>
        """

    def _update_metrics_summary(self, health_status):
        """Update metrics summary display."""
        metrics = health_status.metrics
        error_rate = metrics.get("error_rate", 0)
        response_time = metrics.get("response_time_ms", 0)
        uptime = metrics.get("uptime_hours", 0)

        html = f"""
        <div style='padding: 15px; background-color: #f8f9fa; border-radius: 8px; margin: 10px;'>
            <h4 style='margin-top: 0;'>System Metrics</h4>
            <div style='display: flex; justify-content: space-around; text-align: center;'>
                <div>
                    <div style='font-size: 24px; font-weight: bold; color: {"#dc3545" if error_rate > 0.1 else "#28a745"};'>
                        {error_rate:.1%}
                    </div>
                    <div style='font-size: 12px; color: #666;'>Error Rate</div>
                </div>
                <div>
                    <div style='font-size: 24px; font-weight: bold; color: {"#dc3545" if response_time > 150 else "#28a745"};'>
                        {response_time:.0f}ms
                    </div>
                    <div style='font-size: 12px; color: #666;'>Response Time</div>
                </div>
                <div>
                    <div style='font-size: 24px; font-weight: bold; color: #007bff;'>
                        {uptime:.0f}h
                    </div>
                    <div style='font-size: 12px; color: #666;'>Uptime</div>
                </div>
            </div>
        </div>
        """

        self.metrics_summary.object = html

    def _update_last_updated(self, timestamp: str):
        """Update last updated timestamp."""
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            self.last_updated.object = f"Last updated: {formatted_time}"
        except (ValueError, TypeError):
            self.last_updated.object = f"Last updated: {timestamp}"

    def _manual_refresh(self, event=None):
        """Handle manual refresh button click."""
        self._refresh_data()

    def _show_error(self, message: str):
        """Show error message in dashboard."""
        self.status_indicator.object = f"""
        <div style='text-align: center; padding: 30px; background-color: #dc354520; 
                    border: 2px solid #dc3545; border-radius: 10px; margin: 10px;'>
            <div style='font-size: 48px; margin-bottom: 10px;'>❌</div>
            <div style='font-size: 18px; font-weight: bold; color: #dc3545;'>Dashboard Error</div>
            <div style='font-size: 14px; margin-top: 10px; color: #666;'>{message}</div>
        </div>
        """

    def get_panel(self):
        """Get the Panel layout for the dashboard."""
        return pn.Column(
            "# 🖥️ Admin Monitoring Dashboard",
            self.status_indicator,
            self.component_cards,
            self.metrics_summary,
            self.controls,
            sizing_mode="stretch_width",
        )
