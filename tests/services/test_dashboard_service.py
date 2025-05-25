"""
Tests for DashboardService - Sprint 1.1 functionality.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path

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


class TestDashboardService:
    """Test DashboardService functionality."""

    def test_init_creates_tables(self, temp_db):
        """Test that initializing service creates required tables."""
        service = DashboardService(db_path=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            tables = [
                "dashboard_metrics_history",
                "alert_configurations",
                "dashboard_preferences",
                "maintenance_logs",
            ]

            for table in tables:
                cursor.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                )
                assert cursor.fetchone() is not None, f"Table {table} not found"

    def test_get_health_status(self, dashboard_service):
        """Test getting health status."""
        health_status = dashboard_service.get_health_status()

        assert isinstance(health_status, DashboardHealthStatus)
        assert health_status.overall_status in ["healthy", "warning", "critical"]
        assert "database" in health_status.components
        assert "pattern_learning" in health_status.components
        assert "cache" in health_status.components
        assert health_status.last_updated is not None

    def test_store_metric(self, dashboard_service, temp_db):
        """Test storing metrics."""
        dashboard_service.store_metric("health", "error_rate", 0.05, "percentage")

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT metric_type, metric_name, metric_value, metric_unit 
                FROM dashboard_metrics_history 
                WHERE metric_name = 'error_rate'
            """
            )

            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "health"
            assert row[1] == "error_rate"
            assert row[2] == 0.05
            assert row[3] == "percentage"

    def test_fallback_health_status(self, dashboard_service):
        """Test fallback health status when monitoring fails."""
        # This would require mocking the monitor to fail
        # For now, just verify the fallback method exists
        fallback = dashboard_service._get_fallback_health_status()

        assert fallback.overall_status == "critical"
        assert "failure" in fallback.recommendations[0].lower()

    def test_component_status_structure(self, dashboard_service):
        """Test that component status has expected structure."""
        health_status = dashboard_service.get_health_status()

        # Check database component
        db_component = health_status.components["database"]
        assert "status" in db_component
        assert "icon" in db_component
        assert db_component["status"] in ["connected", "disconnected"]

        # Check pattern learning component
        pattern_component = health_status.components["pattern_learning"]
        assert "status" in pattern_component
        assert "icon" in pattern_component
        assert pattern_component["status"] in ["active", "inactive"]

        # Check cache component
        cache_component = health_status.components["cache"]
        assert "performance" in cache_component
        assert "icon" in cache_component

    def test_metrics_structure(self, dashboard_service):
        """Test that metrics have expected structure."""
        health_status = dashboard_service.get_health_status()

        assert "error_rate" in health_status.metrics
        assert "response_time_ms" in health_status.metrics
        assert "uptime_hours" in health_status.metrics

        # Verify types
        assert isinstance(health_status.metrics["error_rate"], (int, float))
        assert isinstance(health_status.metrics["response_time_ms"], (int, float))
        assert isinstance(health_status.metrics["uptime_hours"], (int, float))

    def test_cache_icon_logic(self, dashboard_service):
        """Test cache icon selection logic."""
        assert dashboard_service._get_cache_icon("excellent") == "✅"
        assert dashboard_service._get_cache_icon("good") == "✅"
        assert dashboard_service._get_cache_icon("fair") == "⚠️"
        assert dashboard_service._get_cache_icon("poor") == "❌"
        assert dashboard_service._get_cache_icon("unknown") == "❌"
