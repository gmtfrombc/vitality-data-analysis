"""
Production Monitoring Service

Comprehensive monitoring service for production deployment,
including error tracking, performance monitoring, and alerting.

Sprint 3.2 Features:
- Production error tracking
- Performance monitoring
- Automated alerting
- Health check automation
- System status reporting
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
import time
import traceback
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import threading
from pathlib import Path

from app.services.dashboard_service import DashboardService
from app.services.maintenance_service import MaintenanceService
from app.utils.learning_metrics import LearningSystemMonitor

logger = logging.getLogger(__name__)


@dataclass
class ProductionAlert:
    """Production alert definition."""

    alert_id: str
    alert_type: str  # 'error', 'performance', 'health', 'security'
    severity: str  # 'low', 'medium', 'high', 'critical'
    title: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False
    acknowledged: bool = False


@dataclass
class SystemStatus:
    """Overall system status for production."""

    status: str  # 'operational', 'degraded', 'outage'
    uptime_percentage: float
    last_incident: Optional[datetime]
    active_alerts: int
    performance_score: float
    components: Dict[str, str]


class ProductionMonitor:
    """Production monitoring and alerting service."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize production monitor.

        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path
        self.dashboard_service = DashboardService(db_path)
        self.maintenance_service = MaintenanceService(db_path)
        self.monitor = LearningSystemMonitor(db_path)

        # Monitoring configuration
        self.monitoring_enabled = True
        self.alert_thresholds = self._load_alert_thresholds()
        self.notification_settings = self._load_notification_settings()

        # Background monitoring
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()

        # Alert tracking
        self.active_alerts: Dict[str, ProductionAlert] = {}
        self.alert_history: List[ProductionAlert] = []

    def _load_alert_thresholds(self) -> Dict[str, Any]:
        """Load alert thresholds from configuration."""
        return {
            "response_time_ms": {"warning": 1000, "critical": 3000},
            "error_rate": {"warning": 0.05, "critical": 0.10},
            "database_response_ms": {"warning": 500, "critical": 2000},
            "cache_hit_rate": {"warning": 0.70, "critical": 0.50},
            "disk_usage_percentage": {"warning": 80, "critical": 95},
            "memory_usage_percentage": {"warning": 85, "critical": 95},
        }

    def _load_notification_settings(self) -> Dict[str, Any]:
        """Load notification settings from environment."""
        return {
            "email_enabled": os.getenv("ALERT_EMAIL_ENABLED", "false").lower()
            == "true",
            "email_smtp_server": os.getenv("ALERT_SMTP_SERVER", "localhost"),
            "email_smtp_port": int(os.getenv("ALERT_SMTP_PORT", "587")),
            "email_username": os.getenv("ALERT_EMAIL_USERNAME"),
            "email_password": os.getenv("ALERT_EMAIL_PASSWORD"),
            "email_from": os.getenv("ALERT_EMAIL_FROM", "admin@aaa-system.local"),
            "email_to": os.getenv("ALERT_EMAIL_TO", "").split(","),
            "slack_enabled": os.getenv("ALERT_SLACK_ENABLED", "false").lower()
            == "true",
            "slack_webhook_url": os.getenv("ALERT_SLACK_WEBHOOK_URL"),
        }

    def start_monitoring(self):
        """Start background production monitoring."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            logger.warning("Production monitoring already running")
            return

        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, name="ProductionMonitor", daemon=True
        )
        self._monitoring_thread.start()
        logger.info("Production monitoring started")

    def stop_monitoring(self):
        """Stop background production monitoring."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=10)
            logger.info("Production monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while not self._stop_monitoring.is_set():
            try:
                # Check system health
                self._check_system_health()

                # Check performance metrics
                self._check_performance_metrics()

                # Check for errors
                self._check_error_conditions()

                # Process alerts
                self._process_alerts()

                # Wait before next check
                self._stop_monitoring.wait(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in production monitoring loop: {e}")
                logger.error(traceback.format_exc())
                self._stop_monitoring.wait(60)

    def _check_system_health(self):
        """Check overall system health."""
        try:
            health = self.dashboard_service.get_health_status()

            # Check for critical health issues
            if health.overall_status == "critical":
                self._create_alert(
                    alert_type="health",
                    severity="critical",
                    title="System Health Critical",
                    message=f'System health is critical. Components affected: {", ".join([k for k, v in health.components.items() if v.get("status") != "healthy"])}',
                    details={"health_status": health.__dict__},
                )
            elif health.overall_status == "warning":
                self._create_alert(
                    alert_type="health",
                    severity="medium",
                    title="System Health Warning",
                    message=f'System health warning detected. Check components: {", ".join([k for k, v in health.components.items() if v.get("status") == "warning"])}',
                    details={"health_status": health.__dict__},
                )

        except Exception as e:
            self._create_alert(
                alert_type="error",
                severity="high",
                title="Health Check Failed",
                message=f"Unable to perform health check: {str(e)}",
                details={"error": str(e), "traceback": traceback.format_exc()},
            )

    def _check_performance_metrics(self):
        """Check performance metrics against thresholds."""
        try:
            current_metrics = self.dashboard_service.get_current_metrics()

            # Check response time
            response_time = current_metrics.get("response_time_ms", 0)
            if response_time > self.alert_thresholds["response_time_ms"]["critical"]:
                self._create_alert(
                    alert_type="performance",
                    severity="critical",
                    title="Critical Response Time",
                    message=f'Response time is {response_time}ms (threshold: {self.alert_thresholds["response_time_ms"]["critical"]}ms)',
                    details={"response_time_ms": response_time},
                )
            elif response_time > self.alert_thresholds["response_time_ms"]["warning"]:
                self._create_alert(
                    alert_type="performance",
                    severity="medium",
                    title="High Response Time",
                    message=f'Response time is {response_time}ms (threshold: {self.alert_thresholds["response_time_ms"]["warning"]}ms)',
                    details={"response_time_ms": response_time},
                )

            # Check error rate
            error_rate = current_metrics.get("error_rate", 0)
            if error_rate > self.alert_thresholds["error_rate"]["critical"]:
                self._create_alert(
                    alert_type="performance",
                    severity="critical",
                    title="Critical Error Rate",
                    message=f'Error rate is {error_rate:.2%} (threshold: {self.alert_thresholds["error_rate"]["critical"]:.2%})',
                    details={"error_rate": error_rate},
                )
            elif error_rate > self.alert_thresholds["error_rate"]["warning"]:
                self._create_alert(
                    alert_type="performance",
                    severity="medium",
                    title="High Error Rate",
                    message=f'Error rate is {error_rate:.2%} (threshold: {self.alert_thresholds["error_rate"]["warning"]:.2%})',
                    details={"error_rate": error_rate},
                )

        except Exception as e:
            logger.error(f"Error checking performance metrics: {e}")

    def _check_error_conditions(self):
        """Check for error conditions in logs and system."""
        try:
            # Check recent error logs
            log_file = Path("app.log")
            if log_file.exists():
                # Read recent log entries
                with open(log_file, "r") as f:
                    lines = f.readlines()
                    recent_lines = lines[-100:]  # Last 100 lines

                    error_count = sum(1 for line in recent_lines if "ERROR" in line)
                    if error_count > 10:  # More than 10 errors in recent logs
                        self._create_alert(
                            alert_type="error",
                            severity="high",
                            title="High Error Count in Logs",
                            message=f"Found {error_count} errors in recent log entries",
                            details={"error_count": error_count},
                        )

        except Exception as e:
            logger.error(f"Error checking error conditions: {e}")

    def _create_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        details: Dict[str, Any],
    ):
        """Create and process a new alert."""
        alert_id = f"{alert_type}_{severity}_{int(time.time())}"

        # Check if similar alert already exists
        similar_alert = self._find_similar_alert(alert_type, title)
        if similar_alert:
            # Update existing alert instead of creating new one
            similar_alert.details.update(details)
            similar_alert.timestamp = datetime.now()
            return

        alert = ProductionAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            details=details,
            timestamp=datetime.now(),
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Send notifications
        self._send_alert_notification(alert)

        logger.warning(f"Production alert created: {title} ({severity})")

    def _find_similar_alert(
        self, alert_type: str, title: str
    ) -> Optional[ProductionAlert]:
        """Find similar active alert."""
        for alert in self.active_alerts.values():
            if (
                alert.alert_type == alert_type
                and alert.title == title
                and not alert.resolved
                and (datetime.now() - alert.timestamp).total_seconds() < 3600
            ):  # Within last hour
                return alert
        return None

    def _send_alert_notification(self, alert: ProductionAlert):
        """Send alert notification via configured channels."""
        try:
            # Email notification
            if self.notification_settings["email_enabled"]:
                self._send_email_alert(alert)

            # Slack notification (if configured)
            if self.notification_settings["slack_enabled"]:
                self._send_slack_alert(alert)

        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")

    def _send_email_alert(self, alert: ProductionAlert):
        """Send email alert notification."""
        try:
            if not self.notification_settings["email_to"]:
                return

            msg = MIMEMultipart()
            msg["From"] = self.notification_settings["email_from"]
            msg["To"] = ", ".join(self.notification_settings["email_to"])
            msg["Subject"] = f"[AAA Alert - {alert.severity.upper()}] {alert.title}"

            body = f"""
AAA System Alert

Alert Type: {alert.alert_type}
Severity: {alert.severity}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Message:
{alert.message}

Details:
{json.dumps(alert.details, indent=2)}

Please investigate and take appropriate action.

---
AAA Production Monitoring System
            """

            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(
                self.notification_settings["email_smtp_server"],
                self.notification_settings["email_smtp_port"],
            )

            if self.notification_settings["email_username"]:
                server.starttls()
                server.login(
                    self.notification_settings["email_username"],
                    self.notification_settings["email_password"],
                )

            server.send_message(msg)
            server.quit()

            logger.info(f"Email alert sent for: {alert.title}")

        except Exception as e:
            logger.error(f"Error sending email alert: {e}")

    def _send_slack_alert(self, alert: ProductionAlert):
        """Send Slack alert notification."""
        try:
            import requests

            webhook_url = self.notification_settings["slack_webhook_url"]
            if not webhook_url:
                return

            color = {
                "low": "#36a64f",
                "medium": "#ff9500",
                "high": "#ff0000",
                "critical": "#8b0000",
            }.get(alert.severity, "#36a64f")

            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"AAA Alert - {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.upper(),
                                "short": True,
                            },
                            {"title": "Type", "value": alert.alert_type, "short": True},
                            {
                                "title": "Time",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True,
                            },
                        ],
                        "footer": "AAA Production Monitoring",
                        "ts": int(alert.timestamp.timestamp()),
                    }
                ]
            }

            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"Slack alert sent for: {alert.title}")

        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")

    def _process_alerts(self):
        """Process and manage active alerts."""
        current_time = datetime.now()

        # Auto-resolve old alerts
        for alert_id, alert in list(self.active_alerts.items()):
            if (current_time - alert.timestamp).total_seconds() > 3600:  # 1 hour old
                alert.resolved = True
                del self.active_alerts[alert_id]
                logger.info(f"Auto-resolved old alert: {alert.title}")

    def get_system_status(self) -> SystemStatus:
        """Get overall system status for production dashboard."""
        try:
            health = self.dashboard_service.get_health_status()
            current_metrics = self.dashboard_service.get_current_metrics()

            # Calculate uptime percentage (last 24 hours)
            uptime_percentage = self._calculate_uptime_percentage()

            # Calculate performance score
            performance_score = self._calculate_performance_score(current_metrics)

            # Determine overall status
            if (
                health.overall_status == "critical"
                or len(
                    [a for a in self.active_alerts.values() if a.severity == "critical"]
                )
                > 0
            ):
                status = "outage"
            elif (
                health.overall_status == "warning"
                or len(
                    [
                        a
                        for a in self.active_alerts.values()
                        if a.severity in ["high", "medium"]
                    ]
                )
                > 0
            ):
                status = "degraded"
            else:
                status = "operational"

            return SystemStatus(
                status=status,
                uptime_percentage=uptime_percentage,
                last_incident=self._get_last_incident_time(),
                active_alerts=len(self.active_alerts),
                performance_score=performance_score,
                components={
                    component: data.get("status", "unknown")
                    for component, data in health.components.items()
                },
            )

        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return SystemStatus(
                status="unknown",
                uptime_percentage=0.0,
                last_incident=datetime.now(),
                active_alerts=len(self.active_alerts),
                performance_score=0.0,
                components={},
            )

    def _calculate_uptime_percentage(self) -> float:
        """Calculate system uptime percentage for last 24 hours."""
        try:
            # Get health check history for last 24 hours
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)

            # For now, return a simple calculation
            # In production, this would analyze actual health check logs
            critical_alerts = [
                a
                for a in self.alert_history
                if a.severity == "critical" and a.timestamp >= start_time
            ]

            if not critical_alerts:
                return 99.9

            # Estimate downtime based on critical alerts
            # Assume 5 minutes per critical alert
            downtime_minutes = len(critical_alerts) * 5
            total_minutes = 24 * 60
            uptime_percentage = max(
                0, (total_minutes - downtime_minutes) / total_minutes * 100
            )

            return round(uptime_percentage, 2)

        except Exception as e:
            logger.error(f"Error calculating uptime: {e}")
            return 95.0  # Default conservative estimate

    def _calculate_performance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)."""
        try:
            score = 100.0

            # Response time impact
            response_time = metrics.get("response_time_ms", 0)
            if response_time > 1000:
                score -= min(30, (response_time - 1000) / 100)

            # Error rate impact
            error_rate = metrics.get("error_rate", 0)
            if error_rate > 0.01:
                score -= min(40, error_rate * 1000)

            # Cache performance impact
            cache_hit_rate = metrics.get("cache_hit_rate", 1.0)
            if cache_hit_rate < 0.8:
                score -= (0.8 - cache_hit_rate) * 50

            return max(0, round(score, 1))

        except Exception as e:
            logger.error(f"Error calculating performance score: {e}")
            return 75.0  # Default moderate score

    def _get_last_incident_time(self) -> Optional[datetime]:
        """Get timestamp of last critical incident."""
        critical_alerts = [
            a for a in self.alert_history if a.severity in ["critical", "high"]
        ]

        if critical_alerts:
            return max(alert.timestamp for alert in critical_alerts)

        return None

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an active alert."""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")

    def resolve_alert(self, alert_id: str, resolved_by: str):
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            del self.active_alerts[alert_id]
            logger.info(f"Alert {alert_id} resolved by {resolved_by}")

    def get_active_alerts(self) -> List[ProductionAlert]:
        """Get list of active alerts."""
        return list(self.active_alerts.values())

    def get_alert_history(self, hours: int = 24) -> List[ProductionAlert]:
        """Get alert history for specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
