"""
Dashboard UI improvements based on user feedback.
"""

import panel as pn
import param
from typing import Dict, Any, List


class ImprovedDashboardTab(param.Parameterized):
    """Enhanced dashboard with user feedback improvements."""

    def __init__(self, **params):
        super().__init__(**params)
        self.setup_improved_layout()

    def setup_improved_layout(self):
        """Setup improved layout based on user feedback."""

        # Improved status indicator with better visual hierarchy
        self.status_indicator = pn.pane.HTML(
            sizing_mode="stretch_width", margin=(10, 10)
        )

        # Enhanced component cards with better spacing
        self.component_cards = pn.GridBox(
            ncols=3, sizing_mode="stretch_width", margin=(10, 10)
        )

        # Clearer metrics display
        self.metrics_summary = pn.pane.HTML(
            sizing_mode="stretch_width", margin=(10, 10)
        )

        # Improved control panel with better organization
        self.control_panel = self._create_improved_controls()

        # Help and documentation panel
        self.help_panel = self._create_help_panel()

    def _create_improved_controls(self):
        """Create improved control panel with better UX."""

        # Primary actions
        self.health_check_button = pn.widgets.Button(
            name="🔍 Run Health Check",
            button_type="primary",
            sizing_mode="fixed",
            width=180,
            height=40,
        )

        self.refresh_button = pn.widgets.Button(
            name="🔄 Refresh Now",
            button_type="outline",
            sizing_mode="fixed",
            width=140,
            height=40,
        )

        # Settings
        self.auto_refresh_toggle = pn.widgets.Toggle(
            name="Auto-refresh", value=True, sizing_mode="fixed", width=100
        )

        self.refresh_interval = pn.widgets.Select(
            name="Interval",
            options={"1 min": 1, "5 min": 5, "10 min": 10, "30 min": 30},
            value=5,
            sizing_mode="fixed",
            width=100,
        )

        # Status indicators
        self.connection_status = pn.pane.HTML(
            "🟢 Connected", sizing_mode="fixed", width=100
        )

        self.last_updated = pn.pane.HTML(
            "Last updated: Never", sizing_mode="fixed", width=200
        )

        # Organize controls in logical groups
        primary_controls = pn.Row(
            self.health_check_button, self.refresh_button, sizing_mode="fixed"
        )

        settings_controls = pn.Row(
            pn.pane.HTML("<strong>Auto-refresh:</strong>", width=80),
            self.auto_refresh_toggle,
            self.refresh_interval,
            sizing_mode="fixed",
        )

        status_info = pn.Row(
            self.connection_status, self.last_updated, sizing_mode="stretch_width"
        )

        return pn.Column(
            primary_controls,
            settings_controls,
            status_info,
            sizing_mode="stretch_width",
            margin=(10, 10),
        )

    def _create_help_panel(self):
        """Create help panel with quick tips."""

        help_content = """
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px;'>
            <h4 style='margin-top: 0; color: #495057;'>💡 Quick Tips</h4>
            <ul style='margin-bottom: 0; color: #6c757d;'>
                <li><strong>Green status</strong> = System healthy and operating normally</li>
                <li><strong>Yellow status</strong> = Minor issues detected, monitoring recommended</li>
                <li><strong>Red status</strong> = Critical issues require immediate attention</li>
                <li><strong>Health Check</strong> = Runs comprehensive system diagnostics</li>
                <li><strong>Auto-refresh</strong> = Automatically updates data at set intervals</li>
            </ul>
        </div>
        """

        return pn.pane.HTML(help_content, sizing_mode="stretch_width")

    def create_improved_status_indicator(self, health_status: Dict[str, Any]) -> str:
        """Create improved status indicator with better visual design."""

        status = health_status.get("overall_status", "unknown")

        # Enhanced status mapping
        status_config = {
            "healthy": {
                "color": "#28a745",
                "bg_color": "#d4edda",
                "border_color": "#c3e6cb",
                "icon": "✅",
                "title": "System Healthy",
                "description": "All systems operating normally",
            },
            "warning": {
                "color": "#ffc107",
                "bg_color": "#fff3cd",
                "border_color": "#ffeaa7",
                "icon": "⚠️",
                "title": "System Warning",
                "description": "Minor issues detected - monitoring recommended",
            },
            "critical": {
                "color": "#dc3545",
                "bg_color": "#f8d7da",
                "border_color": "#f5c6cb",
                "icon": "❌",
                "title": "System Critical",
                "description": "Critical issues require immediate attention",
            },
        }

        config = status_config.get(status, status_config["critical"])

        return f"""
        <div style='
            background: linear-gradient(135deg, {config["bg_color"]} 0%, {config["bg_color"]}dd 100%);
            border: 2px solid {config["border_color"]};
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin: 15px 0;
        '>
            <div style='font-size: 56px; margin-bottom: 15px; line-height: 1;'>
                {config["icon"]}
            </div>
            <div style='
                font-size: 28px;
                font-weight: bold;
                color: {config["color"]};
                margin-bottom: 8px;
            '>
                {config["title"]}
            </div>
            <div style='
                font-size: 16px;
                color: #6c757d;
                margin-bottom: 15px;
            '>
                {config["description"]}
            </div>
            <div style='
                font-size: 14px;
                color: #868e96;
                border-top: 1px solid {config["border_color"]};
                padding-top: 10px;
                margin-top: 15px;
            '>
                Last checked: {health_status.get("last_updated", "Unknown")}
            </div>
        </div>
        """

    def create_improved_component_card(self, name: str, data: Dict[str, Any]) -> str:
        """Create improved component card with better information hierarchy."""

        display_name = name.replace("_", " ").title()
        status = data.get("status", "unknown")
        icon = data.get("icon", "❓")

        # Status-based styling
        if status in ["connected", "active", "excellent", "good"]:
            border_color = "#28a745"
            bg_color = "#f8fff9"
        elif status in ["warning", "fair"]:
            border_color = "#ffc107"
            bg_color = "#fffdf5"
        else:
            border_color = "#dc3545"
            bg_color = "#fff8f8"

        # Component-specific details
        details = []
        if name == "database":
            response_time = data.get("response_time_ms", 0)
            details.append(f"Response: {response_time}ms")
        elif name == "pattern_learning":
            patterns = data.get("active_patterns", 0)
            details.append(f"Active patterns: {patterns}")
        elif name == "cache":
            hit_rate = data.get("hit_rate", 0)
            details.append(f"Hit rate: {hit_rate:.1%}")

        details_html = ""
        if details:
            details_html = f"""
            <div style='
                font-size: 12px;
                color: #6c757d;
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px solid #e9ecef;
            '>
                {' • '.join(details)}
            </div>
            """

        return f"""
        <div style='
            border: 2px solid {border_color};
            border-radius: 10px;
            padding: 20px;
            margin: 8px;
            background: {bg_color};
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: transform 0.2s ease;
        '>
            <div style='font-size: 40px; margin-bottom: 12px; line-height: 1;'>
                {icon}
            </div>
            <div style='
                font-weight: bold;
                font-size: 18px;
                color: #495057;
                margin-bottom: 6px;
            '>
                {display_name}
            </div>
            <div style='
                font-size: 14px;
                color: {border_color};
                font-weight: 500;
                text-transform: capitalize;
            '>
                {status}
            </div>
            {details_html}
        </div>
        """

    def create_improved_metrics_summary(self, metrics: Dict[str, Any]) -> str:
        """Create improved metrics summary with better visual hierarchy."""

        error_rate = metrics.get("error_rate", 0)
        response_time = metrics.get("response_time_ms", 0)
        uptime_hours = metrics.get("uptime_hours", 0)

        # Color coding for metrics
        error_color = (
            "#28a745"
            if error_rate < 0.05
            else "#ffc107" if error_rate < 0.1 else "#dc3545"
        )
        response_color = (
            "#28a745"
            if response_time < 1000
            else "#ffc107" if response_time < 3000 else "#dc3545"
        )
        uptime_color = (
            "#28a745"
            if uptime_hours > 23
            else "#ffc107" if uptime_hours > 12 else "#dc3545"
        )

        return f"""
        <div style='
            background: #ffffff;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        '>
            <h4 style='margin-top: 0; margin-bottom: 20px; color: #495057; text-align: center;'>
                📊 Performance Metrics
            </h4>
            <div style='display: flex; justify-content: space-around; text-align: center;'>
                <div style='flex: 1; padding: 0 10px;'>
                    <div style='font-size: 24px; font-weight: bold; color: {error_color};'>
                        {error_rate:.1%}
                    </div>
                    <div style='font-size: 14px; color: #6c757d; margin-top: 5px;'>
                        Error Rate
                    </div>
                </div>
                <div style='flex: 1; padding: 0 10px; border-left: 1px solid #e9ecef; border-right: 1px solid #e9ecef;'>
                    <div style='font-size: 24px; font-weight: bold; color: {response_color};'>
                        {response_time:.0f}ms
                    </div>
                    <div style='font-size: 14px; color: #6c757d; margin-top: 5px;'>
                        Response Time
                    </div>
                </div>
                <div style='flex: 1; padding: 0 10px;'>
                    <div style='font-size: 24px; font-weight: bold; color: {uptime_color};'>
                        {uptime_hours:.1f}h
                    </div>
                    <div style='font-size: 14px; color: #6c757d; margin-top: 5px;'>
                        Uptime
                    </div>
                </div>
            </div>
        </div>
        """

    def create_alert_panel(self, alerts: List[Dict[str, Any]]) -> str:
        """Create alert panel with improved styling."""

        if not alerts:
            return """
            <div style='
                background: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
                text-align: center;
                color: #155724;
            '>
                ✅ No active alerts - all systems operating normally
            </div>
            """

        alert_html = """
        <div style='
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        '>
            <h4 style='margin-top: 0; margin-bottom: 15px; color: #856404;'>
                ⚠️ Active Alerts ({})
            </h4>
        """.format(
            len(alerts)
        )

        for alert in alerts:
            threshold_type = alert.get("threshold_type", "warning")
            icon = "🔴" if threshold_type == "critical" else "🟡"

            alert_html += f"""
            <div style='
                background: white;
                border-left: 4px solid #ffc107;
                padding: 10px;
                margin: 8px 0;
                border-radius: 4px;
            '>
                <div style='font-weight: bold; color: #856404;'>
                    {icon} {alert['metric_name'].replace('_', ' ').title()}
                </div>
                <div style='font-size: 14px; color: #6c757d; margin-top: 4px;'>
                    {alert['message']}
                </div>
            </div>
            """

        alert_html += "</div>"
        return alert_html
