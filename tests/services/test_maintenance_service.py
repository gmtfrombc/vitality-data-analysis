"""
Tests for Maintenance Service

Sprint 3.1 Testing:
- Maintenance operation execution
- Performance impact calculation
- Scheduling functionality
- Error handling
"""

import pytest
from datetime import datetime, timedelta

from app.services.maintenance_service import (
    MaintenanceService,
    MaintenanceResult,
    MaintenanceSchedule,
)


class TestMaintenanceService:
    """Test cases for MaintenanceService."""

    @pytest.fixture
    def maintenance_service(self, tmp_path):
        """Create maintenance service with test database."""
        db_path = tmp_path / "test_maintenance.db"
        return MaintenanceService(str(db_path))

    @pytest.mark.asyncio
    async def test_execute_maintenance_operation(self, maintenance_service):
        """Test executing a single maintenance operation."""
        result = await maintenance_service.execute_maintenance_operation("db_vacuum")

        assert result is not None
        assert result.operation_id == "db_vacuum"
        assert result.operation_name == "Database Vacuum"
        assert result.started_at is not None
        assert result.completed_at is not None
        assert isinstance(result.success, bool)
        assert isinstance(result.details, dict)
        assert isinstance(result.recommendations, list)

    @pytest.mark.asyncio
    async def test_execute_maintenance_suite(self, maintenance_service):
        """Test executing multiple maintenance operations."""
        operation_ids = ["db_vacuum", "cache_cleanup"]
        results = await maintenance_service.execute_maintenance_suite(operation_ids)

        assert len(results) == 2
        assert all(isinstance(r, MaintenanceResult) for r in results)
        assert results[0].operation_id == "db_vacuum"
        assert results[1].operation_id == "cache_cleanup"

    def test_get_available_operations(self, maintenance_service):
        """Test getting available maintenance operations."""
        operations = maintenance_service.get_available_operations()

        assert len(operations) > 0
        assert any(op.operation_id == "db_vacuum" for op in operations)
        assert any(op.operation_id == "cache_cleanup" for op in operations)

        # Check operation structure
        for op in operations:
            assert hasattr(op, "operation_id")
            assert hasattr(op, "name")
            assert hasattr(op, "description")
            assert hasattr(op, "category")
            assert hasattr(op, "risk_level")

    def test_vacuum_database(self, maintenance_service):
        """Test database vacuum operation."""
        result = maintenance_service._vacuum_database()

        assert isinstance(result, dict)
        assert "size_before_mb" in result
        assert "size_after_mb" in result
        assert "space_reclaimed_mb" in result
        assert result["size_before_mb"] >= result["size_after_mb"]

    def test_analyze_database(self, maintenance_service):
        """Test database analysis operation."""
        result = maintenance_service._analyze_database()

        assert isinstance(result, dict)
        assert "tables_analyzed" in result
        assert "analysis_completed" in result
        assert result["analysis_completed"] is True

    def test_check_database_integrity(self, maintenance_service):
        """Test database integrity check."""
        result = maintenance_service._check_database_integrity()

        assert isinstance(result, dict)
        assert "integrity_ok" in result
        assert "check_results" in result
        assert isinstance(result["integrity_ok"], bool)
        assert isinstance(result["check_results"], list)

    def test_cleanup_cache(self, maintenance_service):
        """Test cache cleanup operation."""
        result = maintenance_service._cleanup_cache()

        assert isinstance(result, dict)
        assert "cache_entries_before" in result
        assert "cache_entries_after" in result
        assert "entries_removed" in result

    def test_performance_baseline(self, maintenance_service):
        """Test performance baseline measurement."""
        baseline = maintenance_service._get_performance_baseline()

        assert isinstance(baseline, dict)
        assert "db_response_time_ms" in baseline
        assert "timestamp" in baseline
        assert baseline["db_response_time_ms"] >= 0

    def test_calculate_performance_impact(self, maintenance_service):
        """Test performance impact calculation."""
        before = {
            "db_response_time_ms": 100.0,
            "cache_performance": 0.8,
            "error_rate": 0.05,
        }

        after = {
            "db_response_time_ms": 80.0,
            "cache_performance": 0.9,
            "error_rate": 0.03,
        }

        impact = maintenance_service._calculate_performance_impact(before, after)

        assert isinstance(impact, dict)
        assert "db_response_time_ms_change_percent" in impact
        # Should be negative (improvement)
        assert impact["db_response_time_ms_change_percent"] < 0

    def test_generate_recommendations(self, maintenance_service):
        """Test recommendation generation."""
        details = {"space_reclaimed_percent": 15.0}
        impact = {"db_response_time_ms_change_percent": -20.0}

        recommendations = maintenance_service._generate_maintenance_recommendations(
            "db_vacuum", details, impact
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all(isinstance(rec, str) for rec in recommendations)

    def test_create_maintenance_schedule(self, maintenance_service):
        """Test creating maintenance schedule."""
        schedule = MaintenanceSchedule(
            schedule_id="test_schedule",
            name="Test Schedule",
            operations=["db_vacuum", "cache_cleanup"],
            schedule_type="daily",
            schedule_config={},
            enabled=True,
            last_run=None,
            next_run=datetime.now() + timedelta(days=1),
            notification_settings={},
        )

        success = maintenance_service.create_maintenance_schedule(schedule)
        assert success is True

    def test_get_maintenance_history(self, maintenance_service):
        """Test getting maintenance history."""
        # Initially should be empty
        history = maintenance_service.get_maintenance_history(30)
        assert isinstance(history, list)
        # History might be empty for new database

    def test_scheduler_start_stop(self, maintenance_service):
        """Test scheduler start and stop."""
        # Start scheduler
        maintenance_service.start_scheduler()
        assert maintenance_service._scheduler_running is True
        assert maintenance_service._scheduler_thread is not None

        # Stop scheduler
        maintenance_service.stop_scheduler()
        assert maintenance_service._scheduler_running is False
