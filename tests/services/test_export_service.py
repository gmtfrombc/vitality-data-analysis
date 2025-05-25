"""
Tests for Export Service

Sprint 2.3 Testing:
- Data export functionality
- Report generation
- Format handling
- Template system
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import os

from app.services.export_service import ExportService, ExportRequest


class TestExportService:
    """Test cases for ExportService."""

    @pytest.fixture
    def export_service(self):
        """Create export service with test database."""
        # Create temporary database for testing
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.close()

        # Create temporary export directory
        temp_dir = tempfile.mkdtemp()

        service = ExportService(temp_db.name)
        service.export_dir = Path(temp_dir)

        yield service

        # Cleanup
        try:
            os.unlink(temp_db.name)
            import shutil

            shutil.rmtree(temp_dir)
        except OSError:
            pass

    def test_export_csv(self, export_service):
        """Test CSV export functionality."""
        request = ExportRequest(
            export_type="csv", data_types=["health"], time_period=7, format_options={}
        )

        # Mock the dashboard service
        mock_health_status = Mock()
        mock_health_status.overall_status = "healthy"
        mock_health_status.components = {"database": {"status": "connected"}}
        mock_health_status.last_updated = "2024-01-01T00:00:00"

        with patch.object(
            export_service.dashboard_service,
            "get_health_status",
            return_value=mock_health_status,
        ):
            result = export_service.export_data(request)

            assert result.success
            assert result.export_type == "csv"
            assert result.file_path is not None
            assert Path(result.file_path).exists()
            assert result.metadata["file_size"] > 0

            # Check CSV content
            with open(result.file_path, "r") as f:
                content = f.read()
                assert "Export ID" in content
                assert "HEALTH DATA" in content
                assert "database" in content

    def test_export_json(self, export_service):
        """Test JSON export functionality."""
        request = ExportRequest(
            export_type="json",
            data_types=["performance"],
            time_period=30,
            format_options={},
        )

        # Mock the dashboard service
        mock_metrics = {"response_time": 100, "error_rate": 0.01}
        mock_system_info = {"version": "1.0", "uptime": 3600}

        with patch.object(
            export_service.dashboard_service,
            "_get_current_metrics",
            return_value=mock_metrics,
        ), patch.object(
            export_service.dashboard_service,
            "_get_system_info",
            return_value=mock_system_info,
        ):

            result = export_service.export_data(request)

            assert result.success
            assert result.export_type == "json"
            assert result.file_path is not None

            # Verify JSON content
            with open(result.file_path, "r") as f:
                data = json.load(f)
                assert "export_id" in data
                assert "data" in data
                assert "performance" in data["data"]
                assert data["time_period_days"] == 30
                assert data["data_types"] == ["performance"]

    @pytest.mark.skipif(
        not hasattr(ExportService, "_export_pdf"),
        reason="PDF export requires reportlab",
    )
    def test_export_pdf(self, export_service):
        """Test PDF export functionality."""
        request = ExportRequest(
            export_type="pdf",
            data_types=["health", "performance"],
            time_period=14,
            format_options={},
        )

        # Mock the required services
        mock_health_status = Mock()
        mock_health_status.overall_status = "healthy"
        mock_health_status.components = {"database": {"status": "connected"}}
        mock_health_status.recommendations = []
        mock_health_status.last_updated = "2024-01-01T00:00:00"

        mock_metrics = {"response_time": 100}

        with patch.object(
            export_service.dashboard_service,
            "get_health_status",
            return_value=mock_health_status,
        ), patch.object(
            export_service.dashboard_service,
            "_get_current_metrics",
            return_value=mock_metrics,
        ):

            result = export_service.export_data(request)

            assert result.success
            assert result.export_type == "pdf"
            assert result.file_path is not None
            assert Path(result.file_path).suffix == ".pdf"
            assert result.metadata["file_size"] > 0

    def test_export_unsupported_format(self, export_service):
        """Test export with unsupported format."""
        request = ExportRequest(
            export_type="xml",  # Unsupported format
            data_types=["health"],
            time_period=7,
            format_options={},
        )

        result = export_service.export_data(request)

        assert not result.success
        assert result.error_message is not None
        assert "Unsupported export type" in result.error_message

    def test_get_export_templates(self, export_service):
        """Test export template retrieval."""
        templates = export_service.get_export_templates()

        assert len(templates) > 0

        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "data_types" in template
            assert "format" in template
            assert "time_period" in template
            assert template["format"] in ["csv", "pdf", "json"]
            assert isinstance(template["data_types"], list)
            assert isinstance(template["time_period"], int)

        # Check for specific templates
        template_ids = [t["id"] for t in templates]
        assert "executive_summary" in template_ids
        assert "technical_report" in template_ids
        assert "learning_analytics" in template_ids
        assert "performance_data" in template_ids
        assert "complete_export" in template_ids

    def test_collect_export_data_health(self, export_service):
        """Test data collection for health export."""
        request = ExportRequest(
            export_type="json", data_types=["health"], time_period=7, format_options={}
        )

        mock_health_status = Mock()
        mock_health_status.overall_status = "healthy"

        with patch.object(
            export_service.dashboard_service,
            "get_health_status",
            return_value=mock_health_status,
        ):
            data = export_service._collect_export_data(request)

            assert "health" in data
            assert "current_status" in data["health"]
            assert "timestamp" in data["health"]
            assert data["health"]["current_status"] == mock_health_status

    def test_collect_export_data_performance(self, export_service):
        """Test data collection for performance export."""
        request = ExportRequest(
            export_type="json",
            data_types=["performance"],
            time_period=7,
            format_options={},
        )

        mock_metrics = {"response_time": 100}
        mock_system_info = {"version": "1.0"}

        with patch.object(
            export_service.dashboard_service,
            "_get_current_metrics",
            return_value=mock_metrics,
        ), patch.object(
            export_service.dashboard_service,
            "_get_system_info",
            return_value=mock_system_info,
        ):

            data = export_service._collect_export_data(request)

            assert "performance" in data
            assert "current_metrics" in data["performance"]
            assert "system_info" in data["performance"]
            assert "timestamp" in data["performance"]
            assert data["performance"]["current_metrics"] == mock_metrics
            assert data["performance"]["system_info"] == mock_system_info

    def test_collect_export_data_learning(self, export_service):
        """Test data collection for learning export."""
        request = ExportRequest(
            export_type="json",
            data_types=["learning"],
            time_period=30,
            format_options={},
        )

        # Mock learning analytics service methods
        mock_pattern_effectiveness = [Mock()]
        mock_correction_analysis = Mock()
        mock_learning_progress = Mock()
        mock_user_feedback = Mock()

        with patch.object(
            export_service.analytics_service,
            "get_pattern_effectiveness",
            return_value=mock_pattern_effectiveness,
        ), patch.object(
            export_service.analytics_service,
            "get_correction_analysis",
            return_value=mock_correction_analysis,
        ), patch.object(
            export_service.analytics_service,
            "get_learning_progress",
            return_value=mock_learning_progress,
        ), patch.object(
            export_service.analytics_service,
            "get_user_feedback_analytics",
            return_value=mock_user_feedback,
        ):

            data = export_service._collect_export_data(request)

            assert "learning" in data
            assert "pattern_effectiveness" in data["learning"]
            assert "correction_analysis" in data["learning"]
            assert "learning_progress" in data["learning"]
            assert "user_feedback" in data["learning"]
            assert "timestamp" in data["learning"]

    def test_collect_export_data_benchmarks(self, export_service):
        """Test data collection for benchmarks export."""
        request = ExportRequest(
            export_type="json",
            data_types=["benchmarks"],
            time_period=30,
            format_options={},
        )

        # Mock benchmark history
        mock_benchmark_history = [Mock()]
        mock_benchmark_history[0].performance_score = 85.0
        mock_benchmark_history[0].avg_duration_ms = 150.0

        with patch.object(
            export_service.benchmark_service,
            "get_benchmark_history",
            return_value=mock_benchmark_history,
        ):
            data = export_service._collect_export_data(request)

            assert "benchmarks" in data
            assert "recent_suites" in data["benchmarks"]
            assert "summary" in data["benchmarks"]
            assert "timestamp" in data["benchmarks"]
            assert data["benchmarks"]["recent_suites"] == mock_benchmark_history

    def test_summarize_benchmarks_empty(self, export_service):
        """Test benchmark summarization with empty history."""
        summary = export_service._summarize_benchmarks([])
        assert summary == {}

    def test_summarize_benchmarks_with_data(self, export_service):
        """Test benchmark summarization with data."""
        mock_suite1 = Mock()
        mock_suite1.performance_score = 85.0
        mock_suite1.avg_duration_ms = 150.0

        mock_suite2 = Mock()
        mock_suite2.performance_score = 90.0
        mock_suite2.avg_duration_ms = 120.0

        benchmark_history = [mock_suite1, mock_suite2]

        summary = export_service._summarize_benchmarks(benchmark_history)

        assert summary["total_suites"] == 2
        assert summary["avg_performance_score"] == 87.5
        assert summary["avg_duration_ms"] == 135.0
        assert summary["latest_score"] == 85.0
        assert summary["trend"] in ["improving", "stable"]

    def test_serialize_for_json_dataclass(self, export_service):
        """Test JSON serialization of dataclass objects."""
        from dataclasses import dataclass
        from datetime import datetime

        @dataclass
        class TestData:
            name: str
            value: int
            timestamp: datetime

        test_obj = TestData("test", 42, datetime.now())

        serialized = export_service._serialize_for_json(test_obj)

        assert isinstance(serialized, dict)
        assert serialized["name"] == "test"
        assert serialized["value"] == 42
        assert isinstance(serialized["timestamp"], str)  # Should be ISO format

    def test_serialize_for_json_nested_structures(self, export_service):
        """Test JSON serialization of nested structures."""
        from datetime import datetime

        test_data = {
            "list": [1, 2, {"nested": datetime.now()}],
            "dict": {"key": datetime.now()},
            "datetime": datetime.now(),
            "simple": "value",
        }

        serialized = export_service._serialize_for_json(test_data)

        assert isinstance(serialized, dict)
        assert isinstance(serialized["list"], list)
        assert isinstance(serialized["list"][2]["nested"], str)
        assert isinstance(serialized["dict"]["key"], str)
        assert isinstance(serialized["datetime"], str)
        assert serialized["simple"] == "value"

    def test_write_health_csv(self, export_service):
        """Test writing health data to CSV."""
        import io
        import csv

        mock_health_status = Mock()
        mock_health_status.overall_status = "healthy"
        mock_health_status.components = {
            "database": {"status": "connected", "icon": "✅"},
            "cache": {"status": "active", "icon": "🗄️"},
        }
        mock_health_status.last_updated = "2024-01-01T00:00:00"

        health_data = {"current_status": mock_health_status}

        # Create a string buffer to capture CSV output
        output = io.StringIO()
        writer = csv.writer(output)

        export_service._write_health_csv(writer, health_data)

        csv_content = output.getvalue()
        assert "Component,Status,Details" in csv_content
        assert "database" in csv_content
        assert "cache" in csv_content
        assert "Overall Status,healthy" in csv_content

    def test_write_performance_csv(self, export_service):
        """Test writing performance data to CSV."""
        import io
        import csv

        performance_data = {
            "current_metrics": {
                "response_time": 100.5,
                "error_rate": 0.01,
                "throughput": 1000,
            }
        }

        output = io.StringIO()
        writer = csv.writer(output)

        export_service._write_performance_csv(writer, performance_data)

        csv_content = output.getvalue()
        assert "Metric,Value,Unit" in csv_content
        assert "response_time,100.5" in csv_content
        assert "error_rate,0.01" in csv_content
        assert "throughput,1000" in csv_content

    def test_export_error_handling(self, export_service):
        """Test export error handling."""
        request = ExportRequest(
            export_type="invalid_format",
            data_types=["health"],
            time_period=7,
            format_options={},
        )

        result = export_service.export_data(request)

        assert not result.success
        assert result.error_message is not None
        assert "Unsupported export type" in result.error_message
        assert result.file_path is None
        assert result.file_content is None

    def test_export_data_collection_error(self, export_service):
        """Test export when data collection fails."""
        request = ExportRequest(
            export_type="csv", data_types=["health"], time_period=7, format_options={}
        )

        # Mock dashboard service to raise an exception
        with patch.object(
            export_service.dashboard_service,
            "get_health_status",
            side_effect=Exception("Database error"),
        ):
            result = export_service.export_data(request)

            assert not result.success
            assert "Database error" in result.error_message

    def test_export_directory_creation(self, export_service):
        """Test that export directory is created if it doesn't exist."""
        # Remove the export directory
        import shutil

        if export_service.export_dir.exists():
            shutil.rmtree(export_service.export_dir)

        # Create a new export service instance
        new_service = ExportService(export_service.db_path)

        # The export directory should be created
        assert new_service.export_dir.exists()

    def test_template_validation(self, export_service):
        """Test that all templates have valid configurations."""
        templates = export_service.get_export_templates()

        valid_formats = ["csv", "pdf", "json"]
        valid_data_types = ["health", "performance", "learning", "benchmarks"]

        for template in templates:
            # Check required fields
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "data_types" in template
            assert "format" in template
            assert "time_period" in template

            # Check valid values
            assert template["format"] in valid_formats
            assert isinstance(template["data_types"], list)
            assert len(template["data_types"]) > 0
            assert all(dt in valid_data_types for dt in template["data_types"])
            assert isinstance(template["time_period"], int)
            assert template["time_period"] > 0

            # Check string fields are not empty
            assert len(template["id"]) > 0
            assert len(template["name"]) > 0
            assert len(template["description"]) > 0
