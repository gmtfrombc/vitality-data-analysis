"""
Automated tests simulating user scenarios from user testing.
"""

import pytest
import time
from unittest.mock import patch

from app.services.dashboard_service import DashboardService


class TestUserScenarios:
    """Test scenarios based on user testing feedback."""

    def test_system_health_assessment_speed(self, dashboard_service):
        """Test that health status loads quickly (Scenario 1)."""
        start_time = time.time()

        health_status = dashboard_service.get_health_status()

        load_time = time.time() - start_time

        # Should load in under 3 seconds
        assert load_time < 3.0
        assert health_status.overall_status in ["healthy", "warning", "critical"]

    def test_performance_investigation_workflow(self, dashboard_service):
        """Test performance investigation workflow (Scenario 2)."""
        # Get performance metrics
        metrics = dashboard_service.get_performance_metrics(hours=24)

        # Should have current metrics
        assert "current" in metrics
        assert "response_time_ms" in metrics["current"]
        assert "error_rate" in metrics["current"]

        # Should have historical data structure
        assert "historical" in metrics
        assert "time_range_hours" in metrics

    def test_health_check_execution_reliability(self, dashboard_service):
        """Test health check execution reliability (Scenario 3)."""
        with patch(
            "scripts.learning_system_health_check.run_health_check"
        ) as mock_check:
            mock_check.return_value = {
                "health": {"status": "healthy"},
                "should_alert": False,
            }

            result = dashboard_service.execute_health_check()

            assert result["success"] is True
            assert "execution_time_ms" in result
            assert result["execution_time_ms"] > 0

    def test_alert_comprehension(self, dashboard_service, temp_db):
        """Test alert system comprehension (Scenario 4)."""
        # Set up alert configuration
        import sqlite3

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO alert_configurations 
                (metric_name, threshold_type, threshold_value, comparison_operator)
                VALUES ('error_rate', 'warning', 0.05, '>')
            """
            )

        # Create health status that triggers alert
        from app.services.dashboard_service import DashboardHealthStatus

        health_status = DashboardHealthStatus(
            overall_status="warning",
            components={},
            metrics={"error_rate": 0.08},
            recommendations=[],
            last_updated="2024-01-01T00:00:00",
        )

        alerts = dashboard_service.check_alert_thresholds(health_status)

        assert len(alerts) == 1
        assert alerts[0]["threshold_type"] == "warning"
        assert "error_rate" in alerts[0]["message"]

    def test_dashboard_performance_under_load(self, dashboard_service):
        """Test dashboard performance with multiple rapid requests."""
        start_time = time.time()

        # Simulate multiple rapid requests
        for _ in range(10):
            health_status = dashboard_service.get_health_status()
            assert health_status is not None

        total_time = time.time() - start_time

        # Should handle 10 requests in under 5 seconds (with caching)
        assert total_time < 5.0

    def test_error_handling_user_experience(self, dashboard_service):
        """Test that errors are handled gracefully for users."""
        # Test with monitor failure
        with patch.object(
            dashboard_service.monitor, "get_system_health"
        ) as mock_health:
            mock_health.side_effect = Exception("Monitor system failed")

            # Should return fallback status instead of crashing
            health_status = dashboard_service.get_health_status()

            assert health_status.overall_status == "critical"
            assert (
                "Dashboard monitoring system failure"
                in health_status.recommendations[0]
            )

    def test_caching_improves_performance(self, dashboard_service):
        """Test that caching improves repeated request performance."""
        # Clear any existing cache
        dashboard_service.cache.clear()

        # First request (no cache)
        start_time = time.time()
        health_status_1 = dashboard_service.get_health_status()
        first_request_time = time.time() - start_time

        # Second request (should use cache)
        start_time = time.time()
        health_status_2 = dashboard_service.get_health_status()
        second_request_time = time.time() - start_time

        # Cached request should be significantly faster
        assert second_request_time < first_request_time * 0.5

        # Results should be identical
        assert health_status_1.overall_status == health_status_2.overall_status

    def test_database_optimization_functionality(self, dashboard_service):
        """Test database optimization features work correctly."""
        # Test database optimization
        result = dashboard_service.optimize_database_queries()
        assert result is True

        # Test metrics cleanup
        cleanup_result = dashboard_service.cleanup_old_metrics(days_to_keep=7)

        if cleanup_result is not None:  # May be None if no old data exists
            assert "metrics_deleted" in cleanup_result
            assert "logs_deleted" in cleanup_result
            assert "cutoff_date" in cleanup_result


@pytest.fixture
def dashboard_service(temp_db):
    """Create a dashboard service for testing."""
    return DashboardService(db_path=temp_db)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_dashboard.db"

    # Initialize database with required tables
    import sqlite3

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()

        # Create required tables for testing
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                threshold_type TEXT NOT NULL,
                threshold_value REAL NOT NULL,
                comparison_operator TEXT NOT NULL,
                notification_enabled INTEGER DEFAULT 1
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dashboard_metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metric_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS maintenance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                operation_type TEXT NOT NULL,
                operation_status TEXT NOT NULL,
                duration_ms INTEGER,
                operation_details TEXT,
                completed_at DATETIME
            )
        """
        )

    return str(db_path)
