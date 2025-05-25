"""
Dashboard Service for AAA Admin Monitoring

This service provides the core functionality for the admin monitoring dashboard,
integrating with existing monitoring utilities to provide a unified interface.

Sprint 1.1 Features:
- Health status aggregation from multiple sources
- Component status monitoring
- Basic metrics collection and storage
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
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
