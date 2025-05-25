"""
Tests for Dashboard Health Check functionality - Sprint 1.2.

This module tests the enhanced dashboard service functionality including:
- Health check execution with progress tracking
- Performance metrics collection and display
- Alert threshold checking and notifications
- Maintenance operation logging
"""

import pytest
import tempfile
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta

from app.services.dashboard_service import DashboardService, DashboardHealthStatus
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
def dashboard_service(temp_db):
    """Create a dashboard service with test database."""
    return DashboardService(db_path=temp_db)


class TestDashboardHealthChecks:
    """Test health check execution functionality."""

    @patch("scripts.learning_system_health_check.run_health_check")
    def test_execute_health_check_success(self, mock_health_check, dashboard_service):
        """Test successful health check execution."""
        # Mock health check results
        mock_health_check.return_value = {
            "health": {"status": "healthy"},
            "should_alert": False,
        }

        # Mock benchmark results
        with patch.object(
            dashboard_service, "_run_performance_benchmark"
        ) as mock_benchmark:
            mock_benchmark.return_value = {
                "benchmark_passed": True,
                "average_lookup_time_ms": 50.0,
            }

            result = dashboard_service.execute_health_check()

            assert result["success"] is True
            assert "execution_time_ms" in result
            assert result["health_results"]["health"]["status"] == "healthy"
            assert result["benchmark_results"]["benchmark_passed"] is True

    @patch("scripts.learning_system_health_check.run_health_check")
    def test_execute_health_check_failure(self, mock_health_check, dashboard_service):
        """Test health check execution failure."""
        mock_health_check.side_effect = Exception("Health check failed")

        result = dashboard_service.execute_health_check()

        assert result["success"] is False
        assert "error" in result
        assert "Health check failed" in result["error"]

    def test_get_performance_metrics(self, dashboard_service, temp_db):
        """Test getting performance metrics."""
        # Insert some test metrics
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO dashboard_metrics_history 
                (metric_type, metric_name, metric_value, metric_unit)
                VALUES ('performance', 'response_time_ms', 120.5, 'milliseconds')
            """
            )

        metrics = dashboard_service.get_performance_metrics(hours=24)

        assert "current" in metrics
        assert "historical" in metrics
        assert metrics["time_range_hours"] == 24

    def test_check_alert_thresholds(self, dashboard_service, temp_db):
        """Test alert threshold checking."""
        # Insert alert configuration
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO alert_configurations 
                (metric_name, threshold_type, threshold_value, comparison_operator)
                VALUES ('error_rate', 'warning', 0.1, '>')
            """
            )

        # Create mock health status with high error rate
        health_status = DashboardHealthStatus(
            overall_status="warning",
            components={},
            metrics={"error_rate": 0.15},
            recommendations=[],
            last_updated="2024-01-01T00:00:00",
        )

        alerts = dashboard_service.check_alert_thresholds(health_status)

        assert len(alerts) == 1
        assert alerts[0]["metric_name"] == "error_rate"
        assert alerts[0]["threshold_type"] == "warning"

    def test_log_maintenance_operation(self, dashboard_service, temp_db):
        """Test logging maintenance operations."""
        dashboard_service._log_maintenance_operation(
            operation_type="health_check",
            operation_status="completed",
            duration_ms=1500,
            operation_details='{"test": "data"}',
        )

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT operation_type, operation_status, duration_ms 
                FROM maintenance_logs 
                WHERE operation_type = 'health_check'
            """
            )

            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "health_check"
            assert row[1] == "completed"
            assert row[2] == 1500

    def test_get_historical_performance_data(self, dashboard_service, temp_db):
        """Test getting historical performance data."""
        # Insert test data
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            # Insert data from different time periods
            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)

            cursor.execute(
                """
                INSERT INTO dashboard_metrics_history 
                (timestamp, metric_type, metric_name, metric_value)
                VALUES (?, 'performance', 'response_time_ms', 100.0)
            """,
                (one_hour_ago.isoformat(),),
            )

            cursor.execute(
                """
                INSERT INTO dashboard_metrics_history 
                (timestamp, metric_type, metric_name, metric_value)
                VALUES (?, 'performance', 'response_time_ms', 150.0)
            """,
                (now.isoformat(),),
            )

        historical_data = dashboard_service._get_historical_performance_data(hours=2)

        assert "response_time_ms" in historical_data
        assert len(historical_data["response_time_ms"]) == 2

    def test_evaluate_threshold_operators(self, dashboard_service):
        """Test threshold evaluation with different operators."""
        # Test greater than
        assert dashboard_service._evaluate_threshold(10, ">", 5) is True
        assert dashboard_service._evaluate_threshold(5, ">", 10) is False

        # Test less than
        assert dashboard_service._evaluate_threshold(5, "<", 10) is True
        assert dashboard_service._evaluate_threshold(10, "<", 5) is False

        # Test equals
        assert dashboard_service._evaluate_threshold(10, "==", 10) is True
        assert dashboard_service._evaluate_threshold(10, "==", 5) is False

    def test_get_metric_value_extraction(self, dashboard_service):
        """Test metric value extraction from health status."""
        health_status = DashboardHealthStatus(
            overall_status="healthy",
            components={},
            metrics={"error_rate": 0.05, "response_time_ms": 120},
            recommendations=[],
            last_updated="2024-01-01T00:00:00",
        )

        error_rate = dashboard_service._get_metric_value(health_status, "error_rate")
        response_time = dashboard_service._get_metric_value(
            health_status, "response_time_ms"
        )
        unknown_metric = dashboard_service._get_metric_value(
            health_status, "unknown_metric"
        )

        assert error_rate == 0.05
        assert response_time == 120
        assert unknown_metric is None


class TestPerformanceBenchmarks:
    """Test performance benchmark functionality."""

    @patch("scripts.learning_system_health_check.run_performance_benchmark")
    def test_run_performance_benchmark_success(self, mock_benchmark, dashboard_service):
        """Test successful performance benchmark execution."""
        mock_benchmark.return_value = {
            "benchmark_passed": True,
            "average_lookup_time_ms": 75.5,
            "max_lookup_time_ms": 120.0,
            "cache_cleanup_time_ms": 25.0,
        }

        result = dashboard_service._run_performance_benchmark()

        assert result["benchmark_passed"] is True
        assert result["average_lookup_time_ms"] == 75.5
        assert result["max_lookup_time_ms"] == 120.0

    @patch("scripts.learning_system_health_check.run_performance_benchmark")
    def test_run_performance_benchmark_failure(self, mock_benchmark, dashboard_service):
        """Test performance benchmark execution failure."""
        mock_benchmark.side_effect = Exception("Benchmark failed")

        result = dashboard_service._run_performance_benchmark()

        assert result["benchmark_passed"] is False
        assert "error" in result
        assert "Benchmark failed" in result["error"]


class TestAlertThresholds:
    """Test alert threshold functionality."""

    def test_no_alerts_when_thresholds_not_exceeded(self, dashboard_service, temp_db):
        """Test that no alerts are generated when thresholds are not exceeded."""
        # Insert alert configuration
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO alert_configurations 
                (metric_name, threshold_type, threshold_value, comparison_operator)
                VALUES ('error_rate', 'warning', 0.1, '>')
            """
            )

        # Create health status with low error rate
        health_status = DashboardHealthStatus(
            overall_status="healthy",
            components={},
            metrics={"error_rate": 0.05},
            recommendations=[],
            last_updated="2024-01-01T00:00:00",
        )

        alerts = dashboard_service.check_alert_thresholds(health_status)

        assert len(alerts) == 0

    def test_multiple_alert_thresholds(self, dashboard_service, temp_db):
        """Test multiple alert thresholds being checked."""
        # Insert multiple alert configurations
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO alert_configurations 
                (metric_name, threshold_type, threshold_value, comparison_operator)
                VALUES 
                ('error_rate', 'warning', 0.1, '>'),
                ('response_time_ms', 'critical', 200, '>')
            """
            )

        # Create health status that exceeds both thresholds
        health_status = DashboardHealthStatus(
            overall_status="critical",
            components={},
            metrics={"error_rate": 0.15, "response_time_ms": 250},
            recommendations=[],
            last_updated="2024-01-01T00:00:00",
        )

        alerts = dashboard_service.check_alert_thresholds(health_status)

        assert len(alerts) == 2
        metric_names = [alert["metric_name"] for alert in alerts]
        assert "error_rate" in metric_names
        assert "response_time_ms" in metric_names

    def test_disabled_alert_configurations(self, dashboard_service, temp_db):
        """Test that disabled alert configurations are ignored."""
        # Insert disabled alert configuration
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO alert_configurations 
                (metric_name, threshold_type, threshold_value, comparison_operator, notification_enabled)
                VALUES ('error_rate', 'warning', 0.1, '>', 0)
            """
            )

        # Create health status that would exceed threshold
        health_status = DashboardHealthStatus(
            overall_status="warning",
            components={},
            metrics={"error_rate": 0.15},
            recommendations=[],
            last_updated="2024-01-01T00:00:00",
        )

        alerts = dashboard_service.check_alert_thresholds(health_status)

        assert len(alerts) == 0


class TestMaintenanceLogs:
    """Test maintenance operation logging."""

    def test_log_completed_operation(self, dashboard_service, temp_db):
        """Test logging a completed maintenance operation."""
        operation_details = json.dumps({"cache_entries_cleaned": 150})

        dashboard_service._log_maintenance_operation(
            operation_type="cache_cleanup",
            operation_status="completed",
            duration_ms=2500,
            operation_details=operation_details,
        )

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT operation_type, operation_status, duration_ms, operation_details, completed_at
                FROM maintenance_logs 
                WHERE operation_type = 'cache_cleanup'
            """
            )

            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "cache_cleanup"
            assert row[1] == "completed"
            assert row[2] == 2500
            assert row[3] == operation_details
            assert row[4] is not None  # completed_at should be set

    def test_log_failed_operation(self, dashboard_service, temp_db):
        """Test logging a failed maintenance operation."""
        error_details = json.dumps({"error": "Database connection failed"})

        dashboard_service._log_maintenance_operation(
            operation_type="database_optimize",
            operation_status="failed",
            operation_details=error_details,
        )

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT operation_type, operation_status, operation_details
                FROM maintenance_logs 
                WHERE operation_type = 'database_optimize'
            """
            )

            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "database_optimize"
            assert row[1] == "failed"
            assert row[2] == error_details


class TestIntegration:
    """Integration tests for dashboard health check functionality."""

    def test_full_health_check_workflow(self, dashboard_service, temp_db):
        """Test the complete health check workflow."""
        # Setup alert configuration
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO alert_configurations 
                (metric_name, threshold_type, threshold_value, comparison_operator)
                VALUES ('error_rate', 'warning', 0.1, '>')
            """
            )

            # Mock the health check components
        with patch(
            "scripts.learning_system_health_check.run_health_check"
        ) as mock_health_check, patch.object(
            dashboard_service, "_run_performance_benchmark"
        ) as mock_benchmark:

            mock_health_check.return_value = {
                "health": {"status": "warning"},
                "should_alert": True,
            }

            mock_benchmark.return_value = {
                "benchmark_passed": False,
                "average_lookup_time_ms": 150.0,
            }

            # Execute health check
            result = dashboard_service.execute_health_check()

            # Verify results
            assert result["success"] is True
            assert result["health_results"]["health"]["status"] == "warning"
            assert result["benchmark_results"]["benchmark_passed"] is False

            # Verify maintenance log was created
            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM maintenance_logs 
                    WHERE operation_type = 'health_check' AND operation_status = 'completed'
                """
                )

                count = cursor.fetchone()[0]
                assert count == 1

    def test_performance_metrics_with_historical_data(self, dashboard_service, temp_db):
        """Test performance metrics retrieval with historical data."""
        # Insert historical performance data
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            # Insert data points over the last 24 hours
            for i in range(24):
                timestamp = datetime.now() - timedelta(hours=i)
                cursor.execute(
                    """
                    INSERT INTO dashboard_metrics_history 
                    (timestamp, metric_type, metric_name, metric_value)
                    VALUES (?, 'performance', 'response_time_ms', ?)
                """,
                    (timestamp.isoformat(), 100 + i * 5),
                )

        # Get performance metrics
        metrics = dashboard_service.get_performance_metrics(hours=24)

        # Verify structure
        assert "current" in metrics
        assert "historical" in metrics
        assert "time_range_hours" in metrics
        assert "last_updated" in metrics

        # Verify historical data
        assert "response_time_ms" in metrics["historical"]
        assert len(metrics["historical"]["response_time_ms"]) == 24
