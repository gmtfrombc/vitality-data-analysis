"""
Maintenance Panel Component for Admin Dashboard

Provides user interface for maintenance operations, scheduling,
and system configuration.

Sprint 3.1 Features:
- One-click maintenance operations
- Maintenance scheduling interface
- Progress tracking and results
- System configuration management
"""

import panel as pn
import pandas as pd
import asyncio
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta

from app.services.maintenance_service import MaintenanceService, MaintenanceSchedule
from app.services.configuration_service import ConfigurationService, AlertRule

logger = logging.getLogger(__name__)

pn.extension("bokeh", "tabulator")


class MaintenancePanel:
    """Panel for maintenance operations and configuration."""

    def __init__(
        self,
        maintenance_service: Optional[MaintenanceService] = None,
        config_service: Optional[ConfigurationService] = None,
    ):
        """Initialize the maintenance panel.

        Args:
            maintenance_service: Optional maintenance service (for testing)
            config_service: Optional configuration service (for testing)
        """
        self.maintenance_service = maintenance_service or MaintenanceService()
        self.config_service = config_service or ConfigurationService()

        # Create UI components
        self._create_components()

    def _create_components(self):
        """Create all UI components."""
        # Maintenance operations section
        self._create_maintenance_components()

        # Configuration section
        self._create_configuration_components()

        # Alert management section
        self._create_alert_components()

    def _create_maintenance_components(self):
        """Create maintenance operation components."""
        # Available operations
        operations = self.maintenance_service.get_available_operations()

        # Operation selector
        self.operation_selector = pn.widgets.CheckBoxGroup(
            name="Select Operations",
            value=[],
            options={op.name: op.operation_id for op in operations},
            inline=False,
            width=400,
        )

        # Quick maintenance buttons
        self.quick_maintenance_buttons = pn.Row(
            pn.widgets.Button(
                name="🗄️ Database Cleanup", button_type="primary", width=150
            ),
            pn.widgets.Button(
                name="🧹 Cache Cleanup", button_type="primary", width=150
            ),
            pn.widgets.Button(name="📝 Log Rotation", button_type="primary", width=150),
            pn.widgets.Button(
                name="⚡ Full Optimization", button_type="success", width=150
            ),
        )

        # Bind quick maintenance buttons
        self.quick_maintenance_buttons[0].on_click(
            lambda event: self._run_quick_maintenance(["db_vacuum", "db_analyze"])
        )
        self.quick_maintenance_buttons[1].on_click(
            lambda event: self._run_quick_maintenance(["cache_cleanup"])
        )
        self.quick_maintenance_buttons[2].on_click(
            lambda event: self._run_quick_maintenance(["log_rotation", "log_cleanup"])
        )
        self.quick_maintenance_buttons[3].on_click(
            lambda event: self._run_quick_maintenance(
                ["db_vacuum", "db_analyze", "cache_cleanup", "performance_optimization"]
            )
        )

        # Custom maintenance button
        self.run_maintenance_button = pn.widgets.Button(
            name="Run Selected Operations", button_type="primary", width=200
        )
        self.run_maintenance_button.on_click(self._on_run_maintenance)

        # Progress and status
        self.maintenance_status = pn.pane.HTML(
            "<p>Ready to run maintenance operations</p>", width=600
        )

        self.maintenance_progress = pn.indicators.Progress(
            name="Maintenance Progress", value=0, width=600, visible=False
        )

        # Results display
        self.maintenance_results = pn.Column(width=800)

        # Maintenance history
        history_data = self._get_maintenance_history_data()
        history_df = (
            pd.DataFrame(history_data)
            if history_data
            else pd.DataFrame(
                columns=[
                    "operation",
                    "status",
                    "started_at",
                    "duration",
                    "recommendations",
                ]
            )
        )

        self.maintenance_history_table = pn.widgets.Tabulator(
            value=history_df, pagination="remote", page_size=10, width=800, height=300
        )

        # Schedule maintenance
        self.schedule_name_input = pn.widgets.TextInput(
            name="Schedule Name", placeholder="Enter schedule name", width=200
        )

        self.schedule_type_selector = pn.widgets.Select(
            name="Schedule Type",
            value="weekly",
            options=["daily", "weekly", "monthly"],
            width=150,
        )

        self.create_schedule_button = pn.widgets.Button(
            name="Create Schedule", button_type="success", width=150
        )
        self.create_schedule_button.on_click(self._on_create_schedule)

    def _create_configuration_components(self):
        """Create configuration management components."""
        # Configuration category selector
        categories = self.config_service.get_all_categories()
        self.config_category_selector = pn.widgets.Select(
            name="Configuration Category",
            value=categories[0] if categories else "",
            options=categories,
            width=200,
        )
        self.config_category_selector.param.watch(
            self._on_config_category_change, "value"
        )

        # Configuration table
        config_data = self._get_config_data()
        config_df = (
            pd.DataFrame(config_data)
            if config_data
            else pd.DataFrame(
                columns=["key", "value", "type", "description", "requires_restart"]
            )
        )

        self.config_table = pn.widgets.Tabulator(
            value=config_df,
            pagination="local",
            page_size=15,
            width=800,
            height=400,
            editors={"value": {"type": "input"}, "description": None},  # Read-only
        )

        # Configuration save button
        self.save_config_button = pn.widgets.Button(
            name="Save Configuration", button_type="primary", width=150
        )
        self.save_config_button.on_click(self._on_save_config)

        # Configuration status
        self.config_status = pn.pane.HTML(
            "<p>Configuration ready for editing</p>", width=600
        )

    def _create_alert_components(self):
        """Create alert management components."""
        # Alert rule form
        self.alert_name_input = pn.widgets.TextInput(
            name="Alert Name", placeholder="Enter alert name", width=200
        )

        self.alert_metric_selector = pn.widgets.Select(
            name="Metric",
            options=[
                "db_response_time_ms",
                "cache_hit_rate",
                "error_rate",
                "memory_usage_percent",
                "disk_usage_percent",
            ],
            width=200,
        )

        self.alert_condition_selector = pn.widgets.Select(
            name="Condition",
            options=[
                ("Greater than", "greater_than"),
                ("Less than", "less_than"),
                ("Equals", "equals"),
                ("Not equals", "not_equals"),
            ],
            width=150,
        )

        self.alert_threshold_input = pn.widgets.FloatInput(
            name="Threshold", value=0.0, width=100
        )

        self.alert_severity_selector = pn.widgets.Select(
            name="Severity",
            options=["info", "warning", "error", "critical"],
            value="warning",
            width=100,
        )

        self.create_alert_button = pn.widgets.Button(
            name="Create Alert Rule", button_type="primary", width=150
        )
        self.create_alert_button.on_click(self._on_create_alert)

        # Alert rules table
        alert_data = self._get_alert_rules_data()
        alert_df = (
            pd.DataFrame(alert_data)
            if alert_data
            else pd.DataFrame(
                columns=[
                    "name",
                    "metric",
                    "condition",
                    "severity",
                    "enabled",
                    "rule_id",
                ]
            )
        )

        self.alert_rules_table = pn.widgets.Tabulator(
            value=alert_df, pagination="local", page_size=10, width=800, height=300
        )

    def _run_quick_maintenance(self, operation_ids: List[str]):
        """Run quick maintenance operations."""
        self.maintenance_status.object = (
            f"<p>🔄 Running {len(operation_ids)} maintenance operations...</p>"
        )
        self.maintenance_progress.visible = True
        self.maintenance_progress.value = 0

        # Run maintenance in background
        asyncio.create_task(self._execute_maintenance_suite(operation_ids))

    def _on_run_maintenance(self, event):
        """Handle run maintenance button click."""
        selected_operations = self.operation_selector.value
        if not selected_operations:
            self.maintenance_status.object = (
                "<p>⚠️ Please select at least one operation</p>"
            )
            return

        self._run_quick_maintenance(selected_operations)

    async def _execute_maintenance_suite(self, operation_ids: List[str]):
        """Execute maintenance operations asynchronously."""
        try:
            total_operations = len(operation_ids)

            for i, operation_id in enumerate(operation_ids):
                # Update progress
                progress = (i / total_operations) * 100
                self.maintenance_progress.value = int(progress)

                # Execute operation
                result = await self.maintenance_service.execute_maintenance_operation(
                    operation_id
                )

                # Add result to display
                result_card = self._create_result_card(result)
                self.maintenance_results.append(result_card)

                # Keep only last 5 results
                if len(self.maintenance_results) > 5:
                    self.maintenance_results.pop(0)

            # Complete
            self.maintenance_progress.value = 100
            self.maintenance_status.object = f"<p>✅ Maintenance completed successfully! {total_operations} operations executed.</p>"

            # Hide progress after delay
            await asyncio.sleep(2)
            self.maintenance_progress.visible = False

            # Refresh history table
            history_data = self._get_maintenance_history_data()
            history_df = (
                pd.DataFrame(history_data)
                if history_data
                else pd.DataFrame(
                    columns=[
                        "operation",
                        "status",
                        "started_at",
                        "duration",
                        "recommendations",
                    ]
                )
            )
            self.maintenance_history_table.value = history_df

        except Exception as e:
            logger.error(f"Error executing maintenance suite: {e}")
            self.maintenance_status.object = f"<p>❌ Maintenance failed: {str(e)}</p>"
            self.maintenance_progress.visible = False

    def _create_result_card(self, result) -> pn.pane.HTML:
        """Create a result card for maintenance operation."""
        status_icon = "✅" if result.success else "❌"
        status_color = "#d4edda" if result.success else "#f8d7da"

        duration = ""
        if result.completed_at and result.started_at:
            duration_seconds = (result.completed_at - result.started_at).total_seconds()
            duration = f"Duration: {duration_seconds:.1f}s"

        recommendations_html = ""
        if result.recommendations:
            recommendations_html = "<br><strong>Recommendations:</strong><ul>"
            for rec in result.recommendations[:3]:  # Show first 3
                recommendations_html += f"<li>{rec}</li>"
            recommendations_html += "</ul>"

        card_html = f"""
        <div style="background: {status_color}; padding: 15px; border-radius: 8px; margin: 5px 0; border-left: 4px solid {'#28a745' if result.success else '#dc3545'};">
            <h4 style="margin: 0 0 5px 0;">{status_icon} {result.operation_name}</h4>
            <p style="margin: 0; color: #666;">
                {duration} | Started: {result.started_at.strftime('%H:%M:%S')}
            </p>
            {recommendations_html}
        </div>
        """

        return pn.pane.HTML(card_html, width=780)

    def _get_maintenance_history_data(self) -> List[Dict[str, Any]]:
        """Get maintenance history data for table."""
        try:
            history = self.maintenance_service.get_maintenance_history(30)

            data = []
            for result in history:
                duration = ""
                if result.completed_at and result.started_at:
                    duration_seconds = (
                        result.completed_at - result.started_at
                    ).total_seconds()
                    duration = f"{duration_seconds:.1f}s"

                data.append(
                    {
                        "operation": result.operation_name,
                        "status": "✅ Success" if result.success else "❌ Failed",
                        "started_at": result.started_at.strftime("%Y-%m-%d %H:%M"),
                        "duration": duration,
                        "recommendations": len(result.recommendations),
                    }
                )

            return data

        except Exception as e:
            logger.error(f"Error getting maintenance history data: {e}")
            return []

    def _on_create_schedule(self, event):
        """Handle create schedule button click."""
        try:
            if not self.schedule_name_input.value:
                self.maintenance_status.object = "<p>⚠️ Please enter a schedule name</p>"
                return

            selected_operations = self.operation_selector.value
            if not selected_operations:
                self.maintenance_status.object = (
                    "<p>⚠️ Please select operations for the schedule</p>"
                )
                return

            # Create schedule
            schedule = MaintenanceSchedule(
                schedule_id=f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                name=self.schedule_name_input.value,
                operations=selected_operations,
                schedule_type=self.schedule_type_selector.value,
                schedule_config={},
                enabled=True,
                last_run=None,
                next_run=datetime.now() + timedelta(days=1),  # Start tomorrow
                notification_settings={},
            )

            success = self.maintenance_service.create_maintenance_schedule(schedule)

            if success:
                self.maintenance_status.object = (
                    f"<p>✅ Schedule '{schedule.name}' created successfully!</p>"
                )
                self.schedule_name_input.value = ""
                self.operation_selector.value = []
            else:
                self.maintenance_status.object = "<p>❌ Failed to create schedule</p>"

        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            self.maintenance_status.object = (
                f"<p>❌ Error creating schedule: {str(e)}</p>"
            )

    def _get_config_data(self) -> List[Dict[str, Any]]:
        """Get configuration data for table."""
        try:
            category = self.config_category_selector.value
            if not category:
                return []

            configs = self.config_service.get_configuration_by_category(category)

            data = []
            for config in configs:
                data.append(
                    {
                        "key": config.key,
                        "value": str(config.value),
                        "type": config.config_type,
                        "description": config.description,
                        "requires_restart": "⚠️" if config.requires_restart else "",
                    }
                )

            return data

        except Exception as e:
            logger.error(f"Error getting config data: {e}")
            return []

    def _on_config_category_change(self, event):
        """Handle configuration category change."""
        config_data = self._get_config_data()
        config_df = (
            pd.DataFrame(config_data)
            if config_data
            else pd.DataFrame(
                columns=["key", "value", "type", "description", "requires_restart"]
            )
        )
        self.config_table.value = config_df

    def _on_save_config(self, event):
        """Handle save configuration button click."""
        try:
            # Get modified data from table
            modified_data = self.config_table.value

            saved_count = 0
            for row in modified_data:
                key = row["key"]
                new_value = row["value"]

                # Parse value based on type
                config_type = row["type"]
                if config_type == "boolean":
                    parsed_value = new_value.lower() in ("true", "1", "yes", "on")
                elif config_type == "integer":
                    parsed_value = int(new_value)
                elif config_type == "float":
                    parsed_value = float(new_value)
                else:
                    parsed_value = new_value

                # Save configuration
                if self.config_service.set_configuration(
                    key, parsed_value, "admin_dashboard", "Updated via dashboard"
                ):
                    saved_count += 1

            self.config_status.object = (
                f"<p>✅ Saved {saved_count} configuration changes</p>"
            )

        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            self.config_status.object = (
                f"<p>❌ Error saving configuration: {str(e)}</p>"
            )

    def _get_alert_rules_data(self) -> List[Dict[str, Any]]:
        """Get alert rules data for table."""
        try:
            rules = self.config_service.get_alert_rules()

            data = []
            for rule in rules:
                data.append(
                    {
                        "name": rule.rule_name,
                        "metric": rule.metric_name,
                        "condition": f"{rule.condition_type} {rule.threshold_value}",
                        "severity": rule.severity,
                        "enabled": "✅" if rule.enabled else "❌",
                        "rule_id": rule.rule_id,
                    }
                )

            return data

        except Exception as e:
            logger.error(f"Error getting alert rules data: {e}")
            return []

    def _on_create_alert(self, event):
        """Handle create alert button click."""
        try:
            if not self.alert_name_input.value:
                return

            # Create alert rule
            rule = AlertRule(
                rule_id=f"rule_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                rule_name=self.alert_name_input.value,
                metric_name=self.alert_metric_selector.value,
                condition_type=self.alert_condition_selector.value,
                threshold_value=self.alert_threshold_input.value,
                severity=self.alert_severity_selector.value,
                enabled=True,
                escalation_rules={},
                notification_channels=["dashboard"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            success = self.config_service.create_alert_rule(rule)

            if success:
                # Clear form
                self.alert_name_input.value = ""
                self.alert_threshold_input.value = 0.0

                # Refresh table
                alert_data = self._get_alert_rules_data()
                alert_df = (
                    pd.DataFrame(alert_data)
                    if alert_data
                    else pd.DataFrame(
                        columns=[
                            "name",
                            "metric",
                            "condition",
                            "severity",
                            "enabled",
                            "rule_id",
                        ]
                    )
                )
                self.alert_rules_table.value = alert_df

        except Exception as e:
            logger.error(f"Error creating alert rule: {e}")

    def get_panel(self):
        """Get the complete maintenance panel."""
        return pn.Tabs(
            (
                "🔧 Maintenance Operations",
                pn.Column(
                    pn.pane.HTML("<h2>🔧 Maintenance Operations</h2>"),
                    # Quick maintenance
                    pn.pane.HTML("<h3>⚡ Quick Maintenance</h3>"),
                    self.quick_maintenance_buttons,
                    pn.pane.HTML("<hr style='margin: 20px 0;'>"),
                    # Custom maintenance
                    pn.pane.HTML("<h3>🛠️ Custom Maintenance</h3>"),
                    pn.Row(
                        self.operation_selector,
                        pn.Spacer(width=50),
                        pn.Column(
                            self.run_maintenance_button,
                            pn.pane.HTML("<h4>📅 Schedule Maintenance</h4>"),
                            pn.Row(
                                self.schedule_name_input,
                                self.schedule_type_selector,
                                self.create_schedule_button,
                            ),
                        ),
                    ),
                    pn.pane.HTML("<hr style='margin: 20px 0;'>"),
                    # Status and progress
                    self.maintenance_status,
                    self.maintenance_progress,
                    # Results
                    pn.pane.HTML("<h3>📊 Recent Results</h3>"),
                    self.maintenance_results,
                    # History
                    pn.pane.HTML("<h3>📋 Maintenance History</h3>"),
                    self.maintenance_history_table,
                    width=900,
                ),
            ),
            (
                "⚙️ System Configuration",
                pn.Column(
                    pn.pane.HTML("<h2>⚙️ System Configuration</h2>"),
                    pn.Row(
                        self.config_category_selector,
                        pn.Spacer(width=50),
                        self.save_config_button,
                    ),
                    self.config_status,
                    self.config_table,
                    width=900,
                ),
            ),
            (
                "🚨 Alert Management",
                pn.Column(
                    pn.pane.HTML("<h2>🚨 Alert Management</h2>"),
                    pn.pane.HTML("<h3>Create New Alert Rule</h3>"),
                    pn.Row(
                        self.alert_name_input,
                        self.alert_metric_selector,
                        self.alert_condition_selector,
                        self.alert_threshold_input,
                        self.alert_severity_selector,
                        self.create_alert_button,
                    ),
                    pn.pane.HTML("<hr style='margin: 20px 0;'>"),
                    pn.pane.HTML("<h3>Existing Alert Rules</h3>"),
                    self.alert_rules_table,
                    width=900,
                ),
            ),
        )
