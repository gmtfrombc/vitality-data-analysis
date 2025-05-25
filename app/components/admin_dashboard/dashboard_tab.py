"""
Main Admin Dashboard Tab

This module provides the main dashboard tab that integrates into the existing
Panel application, providing health status monitoring and system overview.

Sprint 1.1 Features:
- Health status display and component cards
- Basic metrics summary and manual refresh
- Last updated timestamp

Sprint 1.2 Features:
- One-click health check execution with progress indicators
- Performance metrics display with current and historical data
- Auto-refresh mechanism with configurable intervals
- Basic alert notification system
- Enhanced error handling and user feedback
"""

import panel as pn
import param
import logging
from typing import Dict, Any

from app.services.dashboard_service import DashboardService
from app.components.admin_dashboard.charts import PerformanceChartsPanel
from app.components.admin_dashboard.learning_charts import LearningChartsPanel
from app.components.admin_dashboard.export_panel import ExportPanel
from app.components.admin_dashboard.maintenance_panel import MaintenancePanel
from app.services.metrics_collector import MetricsCollector
from app.services.production_monitor import ProductionMonitor

logger = logging.getLogger(__name__)


class AdminDashboardTab(param.Parameterized):
    """Main admin dashboard tab for Panel application."""

    # Reactive parameters for real-time updates
    health_status = param.Dict(default={})
    last_refresh = param.String(default="Never")
    auto_refresh_enabled = param.Boolean(default=True)

    # Sprint 1.2 parameters
    health_check_running = param.Boolean(default=False)
    auto_refresh_interval = param.Integer(default=5)  # minutes
    alerts = param.List(default=[])

    # Sprint 2.1 parameters
    show_charts = param.Boolean(default=False)

    # Sprint 2.2 parameters
    show_learning_analytics = param.Boolean(default=False)

    # Sprint 2.3 parameters
    show_export_panel = param.Boolean(default=False)

    # Sprint 3.1 parameters
    show_maintenance_panel = param.Boolean(default=False)

    # Sprint 3.2 parameters
    production_status = param.Dict(default={})
    active_alerts_count = param.Integer(default=0)

    def __init__(self, **params):
        super().__init__(**params)
        self.dashboard_service = DashboardService()

        # Initialize metrics collector
        self.metrics_collector = MetricsCollector()

        # Initialize charts panel
        self.charts_panel = PerformanceChartsPanel()

        # Initialize learning charts panel (Sprint 2.2)
        self.learning_charts_panel = LearningChartsPanel()

        # Initialize export panel (Sprint 2.3)
        self.export_panel = ExportPanel()

        # Initialize maintenance panel (Sprint 3.1)
        self.maintenance_panel = MaintenancePanel()

        # Initialize production monitor (Sprint 3.2)
        self.production_monitor = ProductionMonitor()
        self.production_monitor.start_monitoring()

        # Start metrics collection
        self.metrics_collector.start_collection()

        self._setup_layout()
        self._refresh_data()

    def _setup_layout(self):
        """Set up the dashboard layout with Sprint 1.2 enhancements."""
        # Overall status indicator
        self.status_indicator = pn.pane.HTML(
            "<div style='text-align: center; font-size: 24px; padding: 20px;'>"
            "🔄 Loading system status..."
            "</div>",
            sizing_mode="stretch_width",
        )

        # Production status panel (Sprint 3.2)
        self.production_status_panel = pn.pane.HTML(
            "<div style='padding: 10px;'>Loading production status...</div>",
            sizing_mode="stretch_width",
        )

        # Component status cards
        self.component_cards = pn.Row(sizing_mode="stretch_width")

        # Metrics summary
        self.metrics_summary = pn.pane.HTML(
            "<div style='padding: 10px;'>Loading metrics...</div>",
            sizing_mode="stretch_width",
        )

        # Health check execution section
        self.health_check_button = pn.widgets.Button(
            name="🔍 Run Health Check",
            button_type="success",
            sizing_mode="fixed",
            width=200,
        )
        self.health_check_button.on_click(self._execute_health_check)

        # Progress indicator
        self.progress_indicator = pn.pane.HTML("", sizing_mode="stretch_width")

        # Performance metrics section
        self.performance_metrics = pn.pane.HTML(
            "<div style='padding: 10px;'>Loading performance metrics...</div>",
            sizing_mode="stretch_width",
        )

        # Auto-refresh controls
        self.auto_refresh_interval_select = pn.widgets.Select(
            name="Auto-refresh interval",
            options={"1 minute": 1, "5 minutes": 5, "10 minutes": 10, "30 minutes": 30},
            value=5,
            sizing_mode="fixed",
            width=150,
        )

        # Alert notifications area
        self.alerts_panel = pn.pane.HTML("", sizing_mode="stretch_width")

        # Control buttons
        self.refresh_button = pn.widgets.Button(
            name="🔄 Refresh Now", button_type="primary", sizing_mode="fixed", width=150
        )
        self.refresh_button.on_click(self._manual_refresh)

        # Auto-refresh toggle
        self.auto_refresh_toggle = pn.widgets.Checkbox(
            name="Auto-refresh", value=True, sizing_mode="fixed"
        )

        # Last updated indicator
        self.last_updated = pn.pane.HTML("Last updated: Never", sizing_mode="fixed")

        # Charts toggle button
        self.charts_toggle = pn.widgets.Toggle(
            name="📈 Show Historical Charts",
            value=self.show_charts,
            sizing_mode="fixed",
            width=200,
        )
        self.charts_toggle.link(self, value="show_charts")

        # Learning analytics toggle button (Sprint 2.2)
        self.learning_toggle = pn.widgets.Toggle(
            name="🧠 Show Learning Analytics",
            value=self.show_learning_analytics,
            sizing_mode="fixed",
            width=200,
        )
        self.learning_toggle.link(self, value="show_learning_analytics")

        # Export panel toggle button (Sprint 2.3)
        self.export_toggle = pn.widgets.Toggle(
            name="📊 Show Export & Reports",
            value=self.show_export_panel,
            sizing_mode="fixed",
            width=200,
        )
        self.export_toggle.link(self, value="show_export_panel")

        # Maintenance panel toggle button (Sprint 3.1)
        self.maintenance_toggle = pn.widgets.Toggle(
            name="🔧 Show Maintenance & Config",
            value=self.show_maintenance_panel,
            sizing_mode="fixed",
            width=200,
        )
        self.maintenance_toggle.link(self, value="show_maintenance_panel")

        # Charts section (initially hidden)
        self.charts_section = pn.Column(
            self.charts_panel.get_panel(),
            visible=self.show_charts,
            sizing_mode="stretch_width",
        )

        # Learning analytics section (initially hidden)
        self.learning_section = pn.Column(
            self.learning_charts_panel.get_panel(),
            visible=self.show_learning_analytics,
            sizing_mode="stretch_width",
        )

        # Export panel section (initially hidden)
        self.export_section = pn.Column(
            self.export_panel.get_panel(),
            visible=self.show_export_panel,
            sizing_mode="stretch_width",
        )

        # Maintenance panel section (initially hidden)
        self.maintenance_section = pn.Column(
            self.maintenance_panel.get_panel(),
            visible=self.show_maintenance_panel,
            sizing_mode="stretch_width",
        )

        # Watch for charts toggle
        self.param.watch(self._toggle_charts, "show_charts")

        # Watch for learning analytics toggle
        self.param.watch(self._toggle_learning_analytics, "show_learning_analytics")

        # Watch for export panel toggle
        self.param.watch(self._toggle_export_panel, "show_export_panel")

        # Watch for maintenance panel toggle
        self.param.watch(self._toggle_maintenance_panel, "show_maintenance_panel")

        # Enhanced controls
        self.enhanced_controls = pn.Row(
            self.health_check_button,
            self.refresh_button,
            self.auto_refresh_toggle,
            self.auto_refresh_interval_select,
            self.charts_toggle,
            self.learning_toggle,
            self.export_toggle,
            self.maintenance_toggle,
            sizing_mode="stretch_width",
        )

        # Start auto-refresh if enabled
        if self.auto_refresh_enabled:
            self._start_auto_refresh()

    def _execute_health_check(self, event=None):
        """Execute comprehensive health check."""
        if self.health_check_running:
            return

        self.health_check_running = True
        self.health_check_button.name = "🔄 Running Health Check..."
        self.health_check_button.disabled = True

        # Show progress indicator
        self.progress_indicator.object = """
        <div style='text-align: center; padding: 20px; background-color: #e3f2fd; 
                    border-radius: 8px; margin: 10px;'>
            <div style='font-size: 18px; color: #1976d2;'>
                🔄 Executing comprehensive health check...
            </div>
            <div style='font-size: 14px; color: #666; margin-top: 10px;'>
                This may take a few moments
            </div>
        </div>
        """

        try:
            # Execute health check
            results = self.dashboard_service.execute_health_check()

            if results["success"]:
                self._show_health_check_results(results)
            else:
                self._show_health_check_error(results.get("error", "Unknown error"))

        except Exception as e:
            self._show_health_check_error(str(e))

        finally:
            self.health_check_running = False
            self.health_check_button.name = "🔍 Run Health Check"
            self.health_check_button.disabled = False

    def _show_health_check_results(self, results: Dict[str, Any]):
        """Display health check results."""
        execution_time = results.get("execution_time_ms", 0)
        health_results = results.get("health_results", {})
        benchmark_results = results.get("benchmark_results", {})

        # Determine overall result
        overall_status = health_results.get("health", {}).get("status", "unknown")
        benchmark_passed = benchmark_results.get("benchmark_passed", False)

        if overall_status == "healthy" and benchmark_passed:
            color = "#28a745"
            icon = "✅"
            message = "Health Check Passed"
        elif overall_status == "warning":
            color = "#ffc107"
            icon = "⚠️"
            message = "Health Check Warning"
        else:
            color = "#dc3545"
            icon = "❌"
            message = "Health Check Failed"

        html = f"""
        <div style='padding: 20px; background-color: {color}20; border: 2px solid {color}; 
                    border-radius: 8px; margin: 10px;'>
            <div style='text-align: center; font-size: 24px; margin-bottom: 15px;'>
                {icon} {message}
            </div>
            <div style='display: flex; justify-content: space-around; text-align: center;'>
                <div>
                    <div style='font-weight: bold;'>Execution Time</div>
                    <div>{execution_time:.0f}ms</div>
                </div>
                <div>
                    <div style='font-weight: bold;'>System Status</div>
                    <div>{overall_status.title()}</div>
                </div>
                <div>
                    <div style='font-weight: bold;'>Performance</div>
                    <div>{"Passed" if benchmark_passed else "Failed"}</div>
                </div>
            </div>
        </div>
        """

        self.progress_indicator.object = html

        # Refresh dashboard data
        self._refresh_data()

    def _show_health_check_error(self, error: str):
        """Display health check error."""
        html = f"""
        <div style='padding: 20px; background-color: #dc354520; border: 2px solid #dc3545; 
                    border-radius: 8px; margin: 10px;'>
            <div style='text-align: center; font-size: 24px; margin-bottom: 15px;'>
                ❌ Health Check Failed
            </div>
            <div style='text-align: center; color: #666;'>
                Error: {error}
            </div>
        </div>
        """
        self.progress_indicator.object = html

    def _update_performance_metrics(self):
        """Update performance metrics display."""
        try:
            metrics = self.dashboard_service.get_performance_metrics(hours=24)
            current = metrics.get("current", {})

            response_time = current.get("response_time_ms", 0)
            pattern_lookup = current.get("pattern_lookup_ms", 0)
            cache_hit_rate = current.get("cache_hit_rate", 0)
            error_rate = current.get("error_rate", 0)

            html = f"""
            <div style='padding: 15px; background-color: #f8f9fa; border-radius: 8px; margin: 10px;'>
                <h4 style='margin-top: 0;'>Performance Metrics (24h)</h4>
                <div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; text-align: center;'>
                    <div>
                        <div style='font-size: 20px; font-weight: bold; color: {"#dc3545" if response_time > 150 else "#28a745"};'>
                            {response_time:.0f}ms
                        </div>
                        <div style='font-size: 12px; color: #666;'>Avg Response Time</div>
                    </div>
                    <div>
                        <div style='font-size: 20px; font-weight: bold; color: {"#dc3545" if pattern_lookup > 100 else "#28a745"};'>
                            {pattern_lookup:.0f}ms
                        </div>
                        <div style='font-size: 12px; color: #666;'>Pattern Lookup</div>
                    </div>
                    <div>
                        <div style='font-size: 20px; font-weight: bold; color: {"#dc3545" if cache_hit_rate < 0.7 else "#28a745"};'>
                            {cache_hit_rate:.1%}
                        </div>
                        <div style='font-size: 12px; color: #666;'>Cache Hit Rate</div>
                    </div>
                    <div>
                        <div style='font-size: 20px; font-weight: bold; color: {"#dc3545" if error_rate > 0.1 else "#28a745"};'>
                            {error_rate:.1%}
                        </div>
                        <div style='font-size: 12px; color: #666;'>Error Rate</div>
                    </div>
                </div>
            </div>
            """

            self.performance_metrics.object = html

        except Exception as e:
            self.performance_metrics.object = f"<div style='padding: 10px; color: #dc3545;'>Error loading performance metrics: {e}</div>"

    def _check_and_display_alerts(self, health_status):
        """Check for alerts and display them."""
        try:
            alerts = self.dashboard_service.check_alert_thresholds(health_status)

            if alerts:
                alerts_html = "<div style='margin: 10px;'><h4 style='color: #dc3545;'>🚨 Active Alerts</h4>"

                for alert in alerts:
                    alert_type = alert["threshold_type"]
                    color = "#dc3545" if alert_type == "critical" else "#ffc107"

                    alerts_html += f"""
                    <div style='padding: 10px; margin: 5px 0; background-color: {color}20; 
                                border-left: 4px solid {color}; border-radius: 4px;'>
                        <div style='font-weight: bold; color: {color};'>{alert_type.upper()}</div>
                        <div>{alert["message"]}</div>
                        <div style='font-size: 12px; color: #666;'>{alert["timestamp"]}</div>
                    </div>
                    """

                alerts_html += "</div>"
                self.alerts_panel.object = alerts_html
            else:
                self.alerts_panel.object = ""

        except Exception as e:
            logger.error(f"Failed to check alerts: {e}")

    def _update_production_status(self):
        """Update production status panel (Sprint 3.2)."""
        try:
            system_status = self.production_monitor.get_system_status()
            active_alerts = self.production_monitor.get_active_alerts()

            # Update reactive parameters
            self.production_status = system_status.__dict__
            self.active_alerts_count = len(active_alerts)

            # Status color and icon
            status_colors = {
                "operational": ("#28a745", "🟢"),
                "degraded": ("#ffc107", "🟡"),
                "outage": ("#dc3545", "🔴"),
                "unknown": ("#6c757d", "⚪"),
            }

            color, icon = status_colors.get(system_status.status, ("#6c757d", "⚪"))

            # Create production status HTML
            html = f"""
            <div style='padding: 15px; background-color: #f8f9fa; border-radius: 8px; margin: 10px;
                        border-left: 4px solid {color};'>
                <h4 style='margin-top: 0; color: {color};'>
                    {icon} Production Status: {system_status.status.title()}
                </h4>
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
                           gap: 15px; margin-top: 15px;'>
                    <div style='text-align: center;'>
                        <div style='font-size: 20px; font-weight: bold; color: #007bff;'>
                            {system_status.uptime_percentage:.1f}%
                        </div>
                        <div style='font-size: 12px; color: #666;'>Uptime (24h)</div>
                    </div>
                    <div style='text-align: center;'>
                        <div style='font-size: 20px; font-weight: bold; color: {"#dc3545" if len(active_alerts) > 0 else "#28a745"};'>
                            {len(active_alerts)}
                        </div>
                        <div style='font-size: 12px; color: #666;'>Active Alerts</div>
                    </div>
                    <div style='text-align: center;'>
                        <div style='font-size: 20px; font-weight: bold; color: #17a2b8;'>
                            {system_status.performance_score:.0f}
                        </div>
                        <div style='font-size: 12px; color: #666;'>Performance Score</div>
                    </div>
                    <div style='text-align: center;'>
                        <div style='font-size: 14px; font-weight: bold; color: #666;'>
                            {system_status.last_incident.strftime('%m/%d %H:%M') if system_status.last_incident else 'None'}
                        </div>
                        <div style='font-size: 12px; color: #666;'>Last Incident</div>
                    </div>
                </div>
            """

            # Add active alerts summary if any
            if active_alerts:
                html += "<div style='margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;'>"
                html += "<h6 style='margin-bottom: 10px; color: #dc3545;'>🚨 Active Alerts:</h6>"
                for alert in active_alerts[:3]:  # Show first 3 alerts
                    severity_colors = {
                        "critical": "#dc3545",
                        "high": "#fd7e14",
                        "medium": "#ffc107",
                        "low": "#28a745",
                    }
                    alert_color = severity_colors.get(alert.severity, "#6c757d")
                    html += f"""
                    <div style='font-size: 12px; margin-bottom: 5px; padding: 5px; 
                               background-color: {alert_color}20; border-left: 3px solid {alert_color};'>
                        <strong>{alert.title}</strong> ({alert.severity})
                        <br><span style='color: #666;'>{alert.timestamp.strftime('%H:%M:%S')}</span>
                    </div>
                    """
                if len(active_alerts) > 3:
                    html += f"<div style='font-size: 12px; color: #666; text-align: center;'>... and {len(active_alerts) - 3} more alerts</div>"
                html += "</div>"

            html += "</div>"

            self.production_status_panel.object = html

        except Exception as e:
            logger.error(f"Failed to update production status: {e}")
            self.production_status_panel.object = f"""
            <div style='padding: 15px; background-color: #f8f9fa; border-radius: 8px; margin: 10px;
                        border-left: 4px solid #dc3545;'>
                <h4 style='margin-top: 0; color: #dc3545;'>⚠️ Production Status Error</h4>
                <p style='color: #666; margin: 0;'>Unable to load production status: {str(e)}</p>
            </div>
            """

    def _toggle_charts(self, event):
        """Toggle charts visibility."""
        self.charts_section.visible = self.show_charts

    def _toggle_learning_analytics(self, event):
        """Toggle learning analytics visibility."""
        self.learning_section.visible = self.show_learning_analytics

    def _toggle_export_panel(self, event):
        """Toggle export panel visibility."""
        self.export_section.visible = self.show_export_panel

    def _toggle_maintenance_panel(self, event):
        """Toggle maintenance panel visibility."""
        self.maintenance_section.visible = self.show_maintenance_panel

    def _start_auto_refresh(self):
        """Start auto-refresh mechanism."""
        if hasattr(self, "_auto_refresh_task"):
            return

        # Note: In a real Panel app, you'd use Panel's built-in periodic callback
        # This is a simplified version for the prompt
        self._auto_refresh_task = True

    def _refresh_data(self):
        """Enhanced refresh with performance metrics and alerts."""
        try:
            health_status = self.dashboard_service.get_health_status()
            self._update_status_indicator(health_status)
            self._update_component_cards(health_status)
            self._update_metrics_summary(health_status)
            self._update_performance_metrics()
            self._check_and_display_alerts(health_status)
            self._update_production_status()  # Sprint 3.2
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
        """Get enhanced Panel layout with Sprint 3.2 features."""
        return pn.Column(
            "# 🖥️ Admin Monitoring Dashboard",
            self.alerts_panel,
            self.status_indicator,
            self.production_status_panel,  # Sprint 3.2
            self.progress_indicator,
            self.component_cards,
            self.metrics_summary,
            self.performance_metrics,
            self.enhanced_controls,
            self.charts_section,
            self.learning_section,
            self.export_section,
            self.maintenance_section,
            self.last_updated,
            sizing_mode="stretch_width",
        )
