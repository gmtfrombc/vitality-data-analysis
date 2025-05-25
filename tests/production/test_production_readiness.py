"""Production readiness validation tests."""

import pytest
import sqlite3
from pathlib import Path

from app.services.dashboard_service import DashboardService
from app.services.production_monitor import ProductionMonitor
from deployment.deploy import DeploymentManager


class TestProductionReadiness:
    """Test production deployment readiness."""

    @pytest.fixture
    def test_db_path(self, tmp_path):
        """Create test database with required tables."""
        db_path = str(tmp_path / "test_production.db")

        # Initialize all services to create their tables
        from app.services.dashboard_service import DashboardService
        from app.services.metrics_collector import MetricsCollector
        from app.services.benchmark_service import BenchmarkService
        from app.services.maintenance_service import MaintenanceService
        from app.services.export_service import ExportService
        from app.services.learning_analytics import LearningAnalyticsService
        from app.services.production_monitor import ProductionMonitor

        services = [
            DashboardService(db_path),
            MetricsCollector(db_path),
            BenchmarkService(db_path),
            MaintenanceService(db_path),
            ExportService(db_path),
            LearningAnalyticsService(db_path),
            ProductionMonitor(db_path),
        ]

        return db_path

    def test_all_required_tables_exist(self, test_db_path):
        """Test that all required database tables exist."""
        required_tables = [
            "dashboard_metrics_history",
            "alert_configurations",
            "dashboard_preferences",
            "maintenance_logs",
            "benchmark_results",
            "learning_metrics",
            "maintenance_history",
            "system_configuration",
            "alert_rules",
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

    def test_all_services_initialize(self, test_db_path):
        """Test that all services can be initialized."""
        from app.services.dashboard_service import DashboardService
        from app.services.metrics_collector import MetricsCollector
        from app.services.benchmark_service import BenchmarkService
        from app.services.maintenance_service import MaintenanceService
        from app.services.export_service import ExportService
        from app.services.learning_analytics import LearningAnalyticsService
        from app.services.production_monitor import ProductionMonitor

        services = [
            DashboardService(test_db_path),
            MetricsCollector(test_db_path),
            BenchmarkService(test_db_path),
            MaintenanceService(test_db_path),
            ExportService(test_db_path),
            LearningAnalyticsService(test_db_path),
            ProductionMonitor(test_db_path),
        ]

        for service in services:
            assert service is not None

    def test_deployment_script_validation(self):
        """Test deployment script validation."""
        deployment_manager = DeploymentManager("development")

        # Should not raise exception
        deployment_manager._validate_environment()

    def test_production_monitoring_setup(self, test_db_path):
        """Test production monitoring can be set up."""
        monitor = ProductionMonitor(test_db_path)

        # Test monitoring can start and stop
        monitor.start_monitoring()
        assert monitor._monitoring_thread is not None

        monitor.stop_monitoring()

    def test_documentation_exists(self):
        """Test that all required documentation exists."""
        required_docs = ["docs/admin_monitoring_dashboard/USER_GUIDE.md", "README.md"]

        for doc_path in required_docs:
            assert Path(
                doc_path
            ).exists(), f"Required documentation not found: {doc_path}"

    def test_deployment_configuration_files(self):
        """Test that deployment configuration files exist."""
        deployment_files = ["deployment/deploy.py", "requirements.txt", "run.py"]

        for file_path in deployment_files:
            assert Path(
                file_path
            ).exists(), f"Required deployment file not found: {file_path}"

    def test_admin_dashboard_components_exist(self):
        """Test that all admin dashboard components exist."""
        component_files = [
            "app/components/admin_dashboard/dashboard_tab.py",
            "app/components/admin_dashboard/maintenance_panel.py",
            "app/components/admin_dashboard/export_panel.py",
            "app/components/admin_dashboard/learning_charts.py",
            "app/components/admin_dashboard/charts.py",
        ]

        for file_path in component_files:
            assert Path(
                file_path
            ).exists(), f"Required component file not found: {file_path}"

    def test_service_files_exist(self):
        """Test that all required service files exist."""
        service_files = [
            "app/services/dashboard_service.py",
            "app/services/metrics_collector.py",
            "app/services/benchmark_service.py",
            "app/services/maintenance_service.py",
            "app/services/export_service.py",
            "app/services/learning_analytics.py",
            "app/services/production_monitor.py",
        ]

        for file_path in service_files:
            assert Path(
                file_path
            ).exists(), f"Required service file not found: {file_path}"

    def test_integration_tests_exist(self):
        """Test that integration tests exist."""
        test_files = [
            "tests/integration/test_complete_dashboard.py",
            "tests/production/test_production_readiness.py",
        ]

        for file_path in test_files:
            assert Path(
                file_path
            ).exists(), f"Required test file not found: {file_path}"

    def test_basic_dashboard_functionality(self, test_db_path):
        """Test basic dashboard functionality works."""
        dashboard_service = DashboardService(test_db_path)

        # Test health status
        health = dashboard_service.get_health_status()
        assert health is not None
        assert hasattr(health, "overall_status")

        # Test performance metrics
        metrics = dashboard_service.get_performance_metrics()
        assert isinstance(metrics, dict)

    def test_production_monitor_functionality(self, test_db_path):
        """Test production monitor basic functionality."""
        monitor = ProductionMonitor(test_db_path)

        # Test system status
        status = monitor.get_system_status()
        assert status is not None
        assert hasattr(status, "status")
        assert hasattr(status, "uptime_percentage")

        # Test alert management
        active_alerts = monitor.get_active_alerts()
        assert isinstance(active_alerts, list)

        alert_history = monitor.get_alert_history()
        assert isinstance(alert_history, list)
