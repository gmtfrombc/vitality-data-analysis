"""
Metrics Collection Service for Historical Data

This service automatically collects and stores metrics data for historical
trend analysis in the admin monitoring dashboard.
"""

import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.utils.saved_questions_db import DB_FILE
from app.utils.learning_metrics import LearningSystemMonitor
from app.services.correction_service import CorrectionService

logger = logging.getLogger(__name__)


@dataclass
class MetricDataPoint:
    """Represents a single metric data point."""

    timestamp: datetime
    metric_type: str
    metric_name: str
    value: float
    unit: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class MetricsCollector:
    """Service for collecting and storing historical metrics."""

    def __init__(self, db_path: Optional[str] = None, collection_interval: int = 300):
        """Initialize metrics collector.

        Args:
            db_path: Database path (for testing)
            collection_interval: Collection interval in seconds (default: 5 minutes)
        """
        self.db_path = db_path or DB_FILE
        self.collection_interval = collection_interval
        self.monitor = LearningSystemMonitor(db_path)
        self.correction_service = CorrectionService(db_path)
        self._running = False
        self._thread = None

    def start_collection(self):
        """Start automated metrics collection."""
        if self._running:
            logger.warning("Metrics collection already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()
        logger.info(
            f"Started metrics collection with {self.collection_interval}s interval"
        )

    def stop_collection(self):
        """Stop automated metrics collection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Stopped metrics collection")

    def _collection_loop(self):
        """Main collection loop running in background thread."""
        while self._running:
            try:
                self._collect_current_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

    def _collect_current_metrics(self):
        """Collect current metrics and store them."""
        try:
            # Get comprehensive metrics from monitor
            metrics = self.monitor.get_comprehensive_metrics()
            timestamp = datetime.now()

            # Collect performance metrics
            self._store_performance_metrics(timestamp, metrics)

            # Collect health metrics
            self._store_health_metrics(timestamp, metrics)

            # Collect learning metrics
            self._store_learning_metrics(timestamp, metrics)

            logger.debug(f"Collected metrics at {timestamp}")

        except Exception as e:
            logger.error(f"Failed to collect current metrics: {e}")

    def _store_performance_metrics(self, timestamp: datetime, metrics: Any):
        """Store performance-related metrics."""
        performance_data = [
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="response_time_ms",
                value=metrics.performance_metrics.get("average_response_time_ms", 0),
                unit="milliseconds",
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="pattern_lookup_ms",
                value=metrics.performance_metrics.get("pattern_lookup_ms", 0),
                unit="milliseconds",
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="cache_hit_rate",
                value=metrics.performance_metrics.get("cache_hit_rate", 0),
                unit="percentage",
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="error_rate",
                value=metrics.error_metrics.get("recent_error_rate", 0),
                unit="percentage",
            ),
        ]

        self._store_metrics_batch(performance_data)

    def _store_health_metrics(self, timestamp: datetime, metrics: Any):
        """Store health-related metrics."""
        health_data = [
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="health",
                metric_name="database_response_ms",
                value=50.0,  # Would measure actual DB response time
                unit="milliseconds",
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="health",
                metric_name="memory_usage_mb",
                value=100.0,  # Placeholder - would measure actual memory usage
                unit="megabytes",
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="health",
                metric_name="active_connections",
                value=1.0,  # Placeholder - would measure actual connections
                unit="count",
            ),
        ]

        self._store_metrics_batch(health_data)

    def _store_learning_metrics(self, timestamp: datetime, metrics: Any):
        """Store learning system metrics."""
        learning_data = [
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="learning",
                metric_name="active_patterns",
                value=metrics.usage_metrics.get("active_patterns", 0),
                unit="count",
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="learning",
                metric_name="pattern_accuracy",
                value=metrics.accuracy_metrics.get("pattern_accuracy", 0),
                unit="percentage",
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="learning",
                metric_name="correction_success_rate",
                value=metrics.accuracy_metrics.get("correction_success_rate", 0),
                unit="percentage",
            ),
        ]

        self._store_metrics_batch(learning_data)

    def _store_metrics_batch(self, metrics: List[MetricDataPoint]):
        """Store a batch of metrics in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for metric in metrics:
                    additional_data_json = (
                        json.dumps(metric.additional_data)
                        if metric.additional_data
                        else None
                    )

                    cursor.execute(
                        """
                        INSERT INTO dashboard_metrics_history 
                        (timestamp, metric_type, metric_name, metric_value, metric_unit, additional_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            metric.timestamp.isoformat(),
                            metric.metric_type,
                            metric.metric_name,
                            metric.value,
                            metric.unit,
                            additional_data_json,
                        ),
                    )

        except Exception as e:
            logger.error(f"Failed to store metrics batch: {e}")

    def get_historical_data(
        self, metric_names: List[str], hours: int = 24
    ) -> Dict[str, List[Dict]]:
        """Get historical data for specified metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                since_time = datetime.now() - timedelta(hours=hours)

                # Build query for multiple metrics
                placeholders = ",".join(["?" for _ in metric_names])
                cursor.execute(
                    f"""
                    SELECT timestamp, metric_name, metric_value, metric_unit
                    FROM dashboard_metrics_history 
                    WHERE metric_name IN ({placeholders})
                    AND timestamp > ?
                    ORDER BY timestamp ASC
                """,
                    metric_names + [since_time.isoformat()],
                )

                rows = cursor.fetchall()

                # Organize data by metric name
                result = {}
                for row in rows:
                    metric_name = row["metric_name"]
                    if metric_name not in result:
                        result[metric_name] = []

                    result[metric_name].append(
                        {
                            "timestamp": row["timestamp"],
                            "value": row["metric_value"],
                            "unit": row["metric_unit"],
                        }
                    )

                return result

        except Exception as e:
            logger.error(f"Failed to get historical data: {e}")
            return {}

    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Clean up old historical data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cutoff_date = datetime.now() - timedelta(days=days_to_keep)

                cursor.execute(
                    """
                    DELETE FROM dashboard_metrics_history 
                    WHERE timestamp < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                deleted_count = cursor.rowcount

                logger.info(f"Cleaned up {deleted_count} old metric records")

                return {
                    "deleted_records": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return {"deleted_records": 0}
