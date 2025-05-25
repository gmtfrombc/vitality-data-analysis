"""
Tests for MetricsCollector - Sprint 2.1 functionality.
"""

import pytest
import tempfile
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta

from app.services.metrics_collector import MetricsCollector, MetricDataPoint
from app.utils.db_migrations import apply_pending_migrations


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    try:
        Path(path).unlink()
        apply_pending_migrations(path)
        yield path
    finally:
        if Path(path).exists():
            Path(path).unlink()


@pytest.fixture
def metrics_collector(temp_db):
    """Create a metrics collector with test database."""
    return MetricsCollector(db_path=temp_db, collection_interval=1)


class TestMetricsCollector:
    """Test MetricsCollector functionality."""

    def test_metric_data_point_creation(self):
        """Test creating metric data points."""
        timestamp = datetime.now()
        metric = MetricDataPoint(
            timestamp=timestamp,
            metric_type="performance",
            metric_name="response_time_ms",
            value=150.5,
            unit="milliseconds",
        )

        assert metric.timestamp == timestamp
        assert metric.metric_type == "performance"
        assert metric.metric_name == "response_time_ms"
        assert metric.value == 150.5
        assert metric.unit == "milliseconds"

    def test_store_metrics_batch(self, metrics_collector, temp_db):
        """Test storing a batch of metrics."""
        timestamp = datetime.now()
        metrics = [
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="response_time_ms",
                value=120.0,
                unit="milliseconds",
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="error_rate",
                value=0.05,
                unit="percentage",
            ),
        ]

        metrics_collector._store_metrics_batch(metrics)

        # Verify data was stored
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT metric_name, metric_value, metric_unit 
                FROM dashboard_metrics_history 
                WHERE metric_type = 'performance'
                ORDER BY metric_name
            """
            )

            rows = cursor.fetchall()
            assert len(rows) == 2

            # Check error_rate
            assert rows[0][0] == "error_rate"
            assert rows[0][1] == 0.05
            assert rows[0][2] == "percentage"

            # Check response_time_ms
            assert rows[1][0] == "response_time_ms"
            assert rows[1][1] == 120.0
            assert rows[1][2] == "milliseconds"

    def test_get_historical_data(self, metrics_collector, temp_db):
        """Test retrieving historical data."""
        # Insert test data
        timestamp = datetime.now()
        metrics = [
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="response_time_ms",
                value=100.0,
                unit="milliseconds",
            ),
            MetricDataPoint(
                timestamp=timestamp - timedelta(hours=1),
                metric_type="performance",
                metric_name="response_time_ms",
                value=110.0,
                unit="milliseconds",
            ),
        ]

        metrics_collector._store_metrics_batch(metrics)

        # Get historical data
        data = metrics_collector.get_historical_data(
            metric_names=["response_time_ms"], hours=24
        )

        assert "response_time_ms" in data
        assert len(data["response_time_ms"]) == 2

        # Check data structure
        point = data["response_time_ms"][0]
        assert "timestamp" in point
        assert "value" in point
        assert "unit" in point

    def test_cleanup_old_data(self, metrics_collector, temp_db):
        """Test cleaning up old data."""
        # Insert old and new data
        old_timestamp = datetime.now() - timedelta(days=35)
        new_timestamp = datetime.now()

        metrics = [
            MetricDataPoint(
                timestamp=old_timestamp,
                metric_type="performance",
                metric_name="response_time_ms",
                value=100.0,
            ),
            MetricDataPoint(
                timestamp=new_timestamp,
                metric_type="performance",
                metric_name="response_time_ms",
                value=110.0,
            ),
        ]

        metrics_collector._store_metrics_batch(metrics)

        # Cleanup old data (keep 30 days)
        result = metrics_collector.cleanup_old_data(days_to_keep=30)

        assert result["deleted_records"] == 1

        # Verify only new data remains
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM dashboard_metrics_history")
            count = cursor.fetchone()[0]
            assert count == 1

    def test_collection_start_stop(self, metrics_collector):
        """Test starting and stopping collection."""
        assert not metrics_collector._running

        metrics_collector.start_collection()
        assert metrics_collector._running
        assert metrics_collector._thread is not None

        # Wait a moment for thread to start
        time.sleep(0.1)

        metrics_collector.stop_collection()
        assert not metrics_collector._running

    def test_get_historical_data_empty_result(self, metrics_collector):
        """Test getting historical data when no data exists."""
        data = metrics_collector.get_historical_data(
            metric_names=["nonexistent_metric"], hours=24
        )

        assert data == {}

    def test_get_historical_data_multiple_metrics(self, metrics_collector, temp_db):
        """Test retrieving multiple metrics at once."""
        timestamp = datetime.now()
        metrics = [
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="response_time_ms",
                value=100.0,
                unit="milliseconds",
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="error_rate",
                value=0.05,
                unit="percentage",
            ),
        ]

        metrics_collector._store_metrics_batch(metrics)

        # Get historical data for multiple metrics
        data = metrics_collector.get_historical_data(
            metric_names=["response_time_ms", "error_rate"], hours=24
        )

        assert "response_time_ms" in data
        assert "error_rate" in data
        assert len(data["response_time_ms"]) == 1
        assert len(data["error_rate"]) == 1

    def test_store_metrics_with_additional_data(self, metrics_collector, temp_db):
        """Test storing metrics with additional JSON data."""
        timestamp = datetime.now()
        additional_data = {"source": "test", "details": {"key": "value"}}

        metric = MetricDataPoint(
            timestamp=timestamp,
            metric_type="performance",
            metric_name="response_time_ms",
            value=120.0,
            unit="milliseconds",
            additional_data=additional_data,
        )

        metrics_collector._store_metrics_batch([metric])

        # Verify additional data was stored
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT additional_data 
                FROM dashboard_metrics_history 
                WHERE metric_name = 'response_time_ms'
            """
            )

            row = cursor.fetchone()
            assert row is not None

            import json

            stored_data = json.loads(row[0])
            assert stored_data == additional_data
