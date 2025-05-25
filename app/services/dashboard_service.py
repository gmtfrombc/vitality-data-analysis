"""
Dashboard Service for AAA Admin Monitoring

This service provides the core functionality for the admin monitoring dashboard,
integrating with existing monitoring utilities to provide a unified interface.

Sprint 1.1 Features:
- Health status aggregation from multiple sources
- Component status monitoring
- Basic metrics collection and storage

Sprint 1.2 Features:
- Health check execution with progress tracking
- Performance metrics with historical data
- Alert threshold checking and notifications
- Maintenance operation logging
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.utils.saved_questions_db import DB_FILE
from app.utils.learning_metrics import LearningSystemMonitor
from app.services.correction_service import CorrectionService
from app.utils.db_migrations import apply_pending_migrations

logger = logging.getLogger(__name__)


@dataclass
class DashboardHealthStatus:
    """Overall dashboard health status."""

    overall_status: str  # "healthy", "warning", "critical"
    components: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Any]
    recommendations: List[str]
    last_updated: str


class DashboardService:
    """Main service for dashboard operations."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the dashboard service.

        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self.monitor = LearningSystemMonitor(db_path)
        self.correction_service = CorrectionService(db_path)
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        """Ensure all required dashboard tables exist."""
        try:
            apply_pending_migrations(self.db_path)
        except Exception as e:
            logger.error(f"Failed to apply dashboard migrations: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_health_status(self) -> DashboardHealthStatus:
        """Get comprehensive health status for dashboard display."""
        try:
            # Get health from existing monitor
            health = self.monitor.get_system_health()

            # Get current metrics
            current_metrics = self._get_current_metrics()

            # Build component status
            components = {
                "database": {
                    "status": (
                        "connected" if health.database_connected else "disconnected"
                    ),
                    "response_time_ms": current_metrics.get("db_response_time", 0),
                    "icon": "✅" if health.database_connected else "❌",
                },
                "pattern_learning": {
                    "status": (
                        "active" if health.pattern_learning_active else "inactive"
                    ),
                    "active_patterns": current_metrics.get("active_patterns", 0),
                    "icon": "✅" if health.pattern_learning_active else "❌",
                },
                "cache": {
                    "performance": health.cache_performance,
                    "hit_rate": current_metrics.get("cache_hit_rate", 0),
                    "icon": self._get_cache_icon(health.cache_performance),
                },
            }

            # Build metrics summary
            metrics = {
                "error_rate": health.recent_error_rate,
                "response_time_ms": current_metrics.get("avg_response_time", 0),
                "uptime_hours": current_metrics.get("uptime_hours", 0),
            }

            return DashboardHealthStatus(
                overall_status=health.overall_status,
                components=components,
                metrics=metrics,
                recommendations=health.recommendations,
                last_updated=datetime.now().isoformat(),
            )

        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return self._get_fallback_health_status()

    def execute_health_check(self) -> Dict[str, Any]:
        """Execute comprehensive health check and return detailed results."""
        try:
            start_time = time.time()

            # Run the existing health check script functionality
            from scripts.learning_system_health_check import run_health_check

            # Execute health check with detailed output
            health_results = run_health_check(detailed=True, json_output=True)

            # Run performance benchmark
            benchmark_results = self._run_performance_benchmark()

            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            # Store the health check execution in maintenance logs
            self._log_maintenance_operation(
                operation_type="health_check",
                operation_status="completed",
                duration_ms=execution_time,
                operation_details=json.dumps(
                    {
                        "health_status": health_results.get("health", {}),
                        "benchmark_passed": benchmark_results.get(
                            "benchmark_passed", False
                        ),
                    }
                ),
            )

            return {
                "success": True,
                "execution_time_ms": execution_time,
                "health_results": health_results,
                "benchmark_results": benchmark_results,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check execution failed: {e}")
            self._log_maintenance_operation(
                operation_type="health_check",
                operation_status="failed",
                operation_details=json.dumps({"error": str(e)}),
            )

            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _run_performance_benchmark(self) -> Dict[str, Any]:
        """Run performance benchmarks and return results."""
        try:
            from scripts.learning_system_health_check import run_performance_benchmark

            return run_performance_benchmark()
        except Exception as e:
            logger.error(f"Performance benchmark failed: {e}")
            return {
                "benchmark_passed": False,
                "error": str(e),
                "average_lookup_time_ms": 0,
                "max_lookup_time_ms": 0,
            }

    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for the specified time period."""
        try:
            # Get current performance from monitor
            current_metrics = self.monitor.get_comprehensive_metrics()

            # Get historical data from dashboard_metrics_history
            historical_data = self._get_historical_performance_data(hours)

            return {
                "current": {
                    "response_time_ms": current_metrics.performance_metrics.get(
                        "average_response_time_ms", 0
                    ),
                    "pattern_lookup_ms": current_metrics.performance_metrics.get(
                        "pattern_lookup_ms", 0
                    ),
                    "cache_hit_rate": current_metrics.performance_metrics.get(
                        "cache_hit_rate", 0
                    ),
                    "error_rate": current_metrics.error_metrics.get(
                        "recent_error_rate", 0
                    ),
                },
                "historical": historical_data,
                "time_range_hours": hours,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {
                "current": {},
                "historical": {},
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
            }

    def _get_historical_performance_data(self, hours: int) -> Dict[str, List]:
        """Get historical performance data from database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get data from the last N hours
                since_time = datetime.now() - timedelta(hours=hours)

                cursor.execute(
                    """
                    SELECT timestamp, metric_name, metric_value 
                    FROM dashboard_metrics_history 
                    WHERE metric_type = 'performance' 
                    AND timestamp > ? 
                    ORDER BY timestamp ASC
                """,
                    (since_time.isoformat(),),
                )

                rows = cursor.fetchall()

                # Organize data by metric name
                metrics_data = {}
                for row in rows:
                    metric_name = row["metric_name"]
                    if metric_name not in metrics_data:
                        metrics_data[metric_name] = []

                    metrics_data[metric_name].append(
                        {"timestamp": row["timestamp"], "value": row["metric_value"]}
                    )

                return metrics_data

        except Exception as e:
            logger.error(f"Failed to get historical performance data: {e}")
            return {}

    def _log_maintenance_operation(
        self,
        operation_type: str,
        operation_status: str,
        duration_ms: int = None,
        operation_details: str = None,
    ):
        """Log maintenance operation to database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if operation_status == "completed":
                    cursor.execute(
                        """
                        INSERT INTO maintenance_logs 
                        (operation_type, operation_status, duration_ms, operation_details, completed_at)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            operation_type,
                            operation_status,
                            duration_ms,
                            operation_details,
                            datetime.now().isoformat(),
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO maintenance_logs 
                        (operation_type, operation_status, operation_details)
                        VALUES (?, ?, ?)
                    """,
                        (operation_type, operation_status, operation_details),
                    )

        except Exception as e:
            logger.error(f"Failed to log maintenance operation: {e}")

    def check_alert_thresholds(
        self, health_status: DashboardHealthStatus
    ) -> List[Dict[str, Any]]:
        """Check if any metrics exceed alert thresholds."""
        alerts = []

        try:
            # Get configured alert thresholds
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM alert_configurations WHERE notification_enabled = 1"
                )
                alert_configs = cursor.fetchall()

            # Check each threshold
            for config in alert_configs:
                metric_name = config["metric_name"]
                threshold_value = config["threshold_value"]
                comparison_op = config["comparison_operator"]
                threshold_type = config["threshold_type"]

                # Get current metric value
                current_value = self._get_metric_value(health_status, metric_name)

                if current_value is not None:
                    # Check if threshold is exceeded
                    if self._evaluate_threshold(
                        current_value, comparison_op, threshold_value
                    ):
                        alerts.append(
                            {
                                "metric_name": metric_name,
                                "current_value": current_value,
                                "threshold_value": threshold_value,
                                "threshold_type": threshold_type,
                                "message": f"{metric_name} is {current_value} (threshold: {comparison_op} {threshold_value})",
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

            return alerts

        except Exception as e:
            logger.error(f"Failed to check alert thresholds: {e}")
            return []

    def _get_metric_value(
        self, health_status: DashboardHealthStatus, metric_name: str
    ) -> float:
        """Extract metric value from health status."""
        if metric_name == "error_rate":
            return health_status.metrics.get("error_rate", 0)
        elif metric_name == "response_time_ms":
            return health_status.metrics.get("response_time_ms", 0)
        # Add more metric mappings as needed
        return None

    def _evaluate_threshold(
        self, value: float, operator: str, threshold: float
    ) -> bool:
        """Evaluate if value meets threshold condition."""
        if operator == ">":
            return value > threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<":
            return value < threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        return False

    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            # Get comprehensive metrics from monitor
            metrics = self.monitor.get_comprehensive_metrics()

            return {
                "db_response_time": 50,  # Placeholder - would measure actual DB response
                "active_patterns": metrics.usage_metrics.get("active_patterns", 0),
                "cache_hit_rate": metrics.performance_metrics.get("cache_hit_rate", 0),
                "avg_response_time": metrics.performance_metrics.get(
                    "average_response_time_ms", 0
                ),
                "uptime_hours": 24,  # Placeholder - would calculate actual uptime
            }
        except Exception as e:
            logger.error(f"Failed to get current metrics: {e}")
            return {}

    def _get_cache_icon(self, performance: str) -> str:
        """Get icon for cache performance."""
        if performance in ["excellent", "good"]:
            return "✅"
        elif performance == "fair":
            return "⚠️"
        else:
            return "❌"

    def _get_fallback_health_status(self) -> DashboardHealthStatus:
        """Get fallback health status when monitoring fails."""
        return DashboardHealthStatus(
            overall_status="critical",
            components={
                "database": {"status": "unknown", "icon": "❓"},
                "pattern_learning": {"status": "unknown", "icon": "❓"},
                "cache": {"performance": "unknown", "icon": "❓"},
            },
            metrics={"error_rate": 1.0},
            recommendations=["Dashboard monitoring system failure - check logs"],
            last_updated=datetime.now().isoformat(),
        )

    def store_metric(
        self, metric_type: str, metric_name: str, value: float, unit: str = None
    ):
        """Store a metric value in the dashboard history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO dashboard_metrics_history 
                    (metric_type, metric_name, metric_value, metric_unit)
                    VALUES (?, ?, ?, ?)
                """,
                    (metric_type, metric_name, value, unit),
                )

        except Exception as e:
            logger.error(f"Failed to store metric {metric_name}: {e}")
