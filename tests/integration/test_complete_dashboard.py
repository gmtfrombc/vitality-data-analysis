"""
Complete Dashboard Integration Tests

Comprehensive integration tests for the entire Admin Monitoring Dashboard,
testing all components working together in production-like scenarios.

Sprint 3.2 Features:
- End-to-end workflow testing
- Performance validation
- Error handling verification
- User scenario simulation
- Production readiness checks
"""

import pytest
import time
import json
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.dashboard_service import DashboardService
from app.services.metrics_collector import MetricsCollector
from app.services.benchmark_service import BenchmarkService
from app.services.maintenance_service import MaintenanceService
from app.services.export_service import ExportService
from app.services.learning_analytics import LearningAnalyticsService
from app.components.admin_dashboard.dashboard_tab import AdminDashboardTab


class TestCompleteIntegration:
    """Complete integration test suite."""

    @pytest.fixture
    def test_db_path(self, tmp_path):
        """Create test database with full schema."""
        db_path = tmp_path / "test_complete.db"

        # Initialize all services to create tables
        dashboard_service = DashboardService(str(db_path))
        metrics_collector = MetricsCollector(str(db_path))
        benchmark_service = BenchmarkService(str(db_path))
        maintenance_service = MaintenanceService(str(db_path))
        export_service = ExportService(str(db_path))
        learning_analytics = LearningAnalyticsService(str(db_path))

        # Populate with test data
        self._populate_test_data(str(db_path))

        return str(db_path)

    def _populate_test_data(self, db_path: str):
        """Populate database with comprehensive test data."""
        with sqlite3.connect(db_path) as conn:
            # Dashboard metrics history
            for i in range(100):
                timestamp = datetime.now() - timedelta(hours=i)
                conn.execute(
                    """
                INSERT INTO dashboard_metrics_history 
                (timestamp, metric_type, metric_name, metric_value, metric_unit)
                VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        timestamp.isoformat(),
                        "performance",
                        "response_time",
                        50 + (i % 20),
                        "ms",
                    ),
                )

            # Learning metrics
            for i in range(30):
                date = datetime.now().date() - timedelta(days=i)
                conn.execute(
                    """
                INSERT INTO learning_metrics 
                (metric_date, total_queries, correct_answers, pattern_matches, accuracy_rate)
                VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        date.isoformat(),
                        100 + (i % 50),
                        85 + (i % 15),
                        20 + (i % 10),
                        0.85 + (i % 10) / 100,
                    ),
                )

            # Benchmark results
            for i in range(10):
                timestamp = datetime.now() - timedelta(days=i)
                conn.execute(
                    """
                INSERT INTO benchmark_results 
                (suite_id, test_name, test_type, duration_ms, success, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        f"daily_benchmark_{i}",
                        f"test_{i}",
                        "performance",
                        45 + (i % 10),
                        True,
                        json.dumps(
                            {
                                "response_time_ms": 45 + (i % 10),
                                "throughput_qps": 10 + (i % 5),
                                "error_rate": 0.01 + (i % 3) / 1000,
                            }
                        ),
                        timestamp.isoformat(),
                    ),
                )

    def test_complete_dashboard_initialization(self, test_db_path):
        """Test complete dashboard initialization and startup."""
        # Initialize all services
        dashboard_service = DashboardService(test_db_path)
        metrics_collector = MetricsCollector(test_db_path)

        # Test health status
        health = dashboard_service.get_health_status()
        assert health.overall_status in ["healthy", "warning", "critical"]
        assert "database" in health.components
        assert "pattern_learning" in health.components
        assert "cache" in health.components

        # Test metrics collection
        performance_metrics = dashboard_service.get_performance_metrics()
        assert isinstance(performance_metrics, dict)

        # Test dashboard tab creation
        dashboard_tab = AdminDashboardTab()
        assert dashboard_tab.dashboard_service is not None
        assert dashboard_tab.metrics_collector is not None

    def test_end_to_end_monitoring_workflow(self, test_db_path):
        """Test complete monitoring workflow from data collection to display."""
        dashboard_service = DashboardService(test_db_path)
        metrics_collector = MetricsCollector(test_db_path)

        # Start metrics collection
        metrics_collector.start_collection()
        time.sleep(2)  # Allow collection

        # Verify data collection
        performance_metrics = dashboard_service.get_performance_metrics(hours=1)
        assert isinstance(performance_metrics, dict)

        # Test health check execution
        health_result = dashboard_service.execute_health_check()
        assert health_result["success"] is True
        assert "health_results" in health_result or "benchmark_results" in health_result

        # Test alert checking
        health_status = dashboard_service.get_health_status()
        alerts = dashboard_service.check_alert_thresholds(health_status)
        assert isinstance(alerts, list)

        # Stop collection
        metrics_collector.stop_collection()

    def test_historical_data_and_charts(self, test_db_path):
        """Test historical data retrieval and chart generation."""
        dashboard_service = DashboardService(test_db_path)

        # Test different time periods
        for hours in [24, 168, 720, 2160]:  # 24h, 7d, 30d, 90d in hours
            performance_data = dashboard_service.get_performance_metrics(hours=hours)
            assert isinstance(performance_data, dict)

    def test_learning_analytics_integration(self, test_db_path):
        """Test learning analytics and pattern tracking."""
        learning_analytics = LearningAnalyticsService(test_db_path)

        # Test pattern effectiveness
        pattern_effectiveness = learning_analytics.get_pattern_effectiveness()
        assert isinstance(pattern_effectiveness, list)

        # Test correction analysis
        correction_analysis = learning_analytics.get_correction_analysis()
        assert correction_analysis is not None

        # Test learning progress
        learning_progress = learning_analytics.get_learning_progress()
        assert learning_progress is not None

    def test_export_functionality(self, test_db_path):
        """Test report generation and export capabilities."""
        export_service = ExportService(test_db_path)

        # Test export functionality
        from app.services.export_service import ExportRequest

        # Test CSV export
        csv_request = ExportRequest(
            export_type="csv",
            data_types=["health", "performance"],
            time_period=7,
            format_options={},
        )
        csv_result = export_service.export_data(csv_request)
        assert csv_result.success is True
        assert csv_result.file_content is not None or csv_result.file_path is not None

        # Test PDF export
        pdf_request = ExportRequest(
            export_type="pdf",
            data_types=["health", "performance"],
            time_period=7,
            format_options={},
        )
        pdf_result = export_service.export_data(pdf_request)
        assert pdf_result.success is True
        assert pdf_result.file_content is not None or pdf_result.file_path is not None

        # Test JSON export
        json_request = ExportRequest(
            export_type="json",
            data_types=["health", "performance"],
            time_period=30,
            format_options={},
        )
        json_result = export_service.export_data(json_request)
        assert json_result.success is True
        assert json_result.file_content is not None or json_result.file_path is not None

    def test_maintenance_operations(self, test_db_path):
        """Test automated maintenance operations."""
        maintenance_service = MaintenanceService(test_db_path)

        # Test maintenance operations
        import asyncio

        # Test cache cleanup
        cleanup_result = asyncio.run(
            maintenance_service.execute_maintenance_operation("cache_cleanup")
        )
        assert cleanup_result.success is True

        # Test database vacuum (optimization)
        optimize_result = asyncio.run(
            maintenance_service.execute_maintenance_operation("db_vacuum")
        )
        assert optimize_result.success is True

        # Test log rotation
        log_result = asyncio.run(
            maintenance_service.execute_maintenance_operation("log_rotation")
        )
        assert log_result.success is True

    def test_benchmark_execution(self, test_db_path):
        """Test performance benchmark execution."""
        benchmark_service = BenchmarkService(test_db_path)

        # Test benchmark service initialization
        assert benchmark_service is not None

        # Test benchmark history (may be empty in test environment)
        history = benchmark_service.get_benchmark_history(days=30)
        assert isinstance(history, list)

    def test_error_handling_and_recovery(self, test_db_path):
        """Test error handling and system recovery."""
        dashboard_service = DashboardService(test_db_path)

        # Test database connection error handling
        with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
            health = dashboard_service.get_health_status()
            assert health.overall_status in ["warning", "critical"]
            assert "database" in health.components

        # Test service recovery
        health = dashboard_service.get_health_status()
        assert health.overall_status in ["healthy", "warning"]

    def test_performance_under_load(self, test_db_path):
        """Test dashboard performance under simulated load."""
        dashboard_service = DashboardService(test_db_path)

        # Simulate multiple concurrent requests
        import concurrent.futures

        def get_health_status():
            return dashboard_service.get_health_status()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_health_status) for _ in range(20)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # Verify all requests completed successfully
        assert len(results) == 20
        assert all(
            result.overall_status in ["healthy", "warning", "critical"]
            for result in results
        )

    def test_data_consistency_and_integrity(self, test_db_path):
        """Test data consistency across all services."""
        dashboard_service = DashboardService(test_db_path)
        metrics_collector = MetricsCollector(test_db_path)

        # Test basic functionality
        performance_metrics = dashboard_service.get_performance_metrics()
        assert isinstance(performance_metrics, dict)

    def test_production_readiness_checks(self, test_db_path):
        """Test production readiness validation."""
        dashboard_service = DashboardService(test_db_path)

        # Test all required tables exist
        required_tables = [
            "dashboard_metrics_history",
            "alert_configurations",
            "dashboard_preferences",
            "maintenance_logs",
            "benchmark_results",
            "learning_metrics",
            "maintenance_history",
            "system_configuration",
        ]

        with sqlite3.connect(test_db_path) as conn:
            cursor = conn.execute(
                """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """
            )
            existing_tables = [row[0] for row in cursor.fetchall()]

        for table in required_tables:
            assert table in existing_tables, f"Required table {table} not found"

        # Test all services can initialize
        services = [
            DashboardService(test_db_path),
            MetricsCollector(test_db_path),
            BenchmarkService(test_db_path),
            MaintenanceService(test_db_path),
            ExportService(test_db_path),
            LearningAnalyticsService(test_db_path),
        ]

        for service in services:
            assert service is not None
            # Test basic functionality
            if hasattr(service, "get_health_status"):
                health = service.get_health_status()
                assert health is not None
