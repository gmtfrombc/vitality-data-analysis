"""
Tests for Chart Components - Sprint 2.1 functionality.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.components.admin_dashboard.charts import (
    TimeSeriesChart,
    PerformanceChartsPanel,
)
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
def sample_metrics_data(temp_db):
    """Create sample metrics data for testing."""
    collector = MetricsCollector(db_path=temp_db)

    # Create sample data points over the last 24 hours
    now = datetime.now()
    metrics = []

    for i in range(24):  # 24 hours of data
        timestamp = now - timedelta(hours=i)

        metrics.extend(
            [
                MetricDataPoint(
                    timestamp=timestamp,
                    metric_type="performance",
                    metric_name="response_time_ms",
                    value=100 + (i * 2),  # Increasing response time
                    unit="milliseconds",
                ),
                MetricDataPoint(
                    timestamp=timestamp,
                    metric_type="performance",
                    metric_name="error_rate",
                    value=0.01 + (i * 0.001),  # Increasing error rate
                    unit="percentage",
                ),
                MetricDataPoint(
                    timestamp=timestamp,
                    metric_type="performance",
                    metric_name="cache_hit_rate",
                    value=0.95 - (i * 0.01),  # Decreasing cache hit rate
                    unit="percentage",
                ),
            ]
        )

    collector._store_metrics_batch(metrics)
    return temp_db


class TestTimeSeriesChart:
    """Test TimeSeriesChart functionality."""

    def test_chart_initialization(self):
        """Test chart initialization with default parameters."""
        chart = TimeSeriesChart()

        assert chart.time_range == "24h"
        assert chart.selected_metrics == ["response_time_ms", "error_rate"]
        assert chart.chart_pane is not None

    def test_parse_time_range(self):
        """Test time range parsing."""
        chart = TimeSeriesChart()

        assert chart._parse_time_range("24h") == 24
        assert chart._parse_time_range("7d") == 24 * 7
        assert chart._parse_time_range("30d") == 24 * 30
        assert chart._parse_time_range("90d") == 24 * 90
        assert chart._parse_time_range("invalid") == 24  # Default fallback

    def test_format_metric_name(self):
        """Test metric name formatting."""
        chart = TimeSeriesChart()

        assert chart._format_metric_name("response_time_ms") == "Response Time (ms)"
        assert chart._format_metric_name("error_rate") == "Error Rate (%)"
        assert chart._format_metric_name("cache_hit_rate") == "Cache Hit Rate (%)"
        assert chart._format_metric_name("unknown_metric") == "Unknown Metric"

    @patch("app.components.admin_dashboard.charts.MetricsCollector")
    def test_chart_update_with_data(self, mock_collector_class, sample_metrics_data):
        """Test chart update with sample data."""
        # Mock the metrics collector
        mock_collector = Mock()
        mock_collector_class.return_value = mock_collector

        # Sample data
        mock_data = {
            "response_time_ms": [
                {
                    "timestamp": "2024-01-01T12:00:00",
                    "value": 100,
                    "unit": "milliseconds",
                },
                {
                    "timestamp": "2024-01-01T13:00:00",
                    "value": 110,
                    "unit": "milliseconds",
                },
            ],
            "error_rate": [
                {
                    "timestamp": "2024-01-01T12:00:00",
                    "value": 0.01,
                    "unit": "percentage",
                },
                {
                    "timestamp": "2024-01-01T13:00:00",
                    "value": 0.02,
                    "unit": "percentage",
                },
            ],
        }
        mock_collector.get_historical_data.return_value = mock_data

        chart = TimeSeriesChart()
        chart._update_chart()

        # Verify collector was called (may be called during initialization and update)
        assert mock_collector.get_historical_data.call_count >= 1
        mock_collector.get_historical_data.assert_called_with(
            metric_names=["response_time_ms", "error_rate"], hours=24
        )

        # Verify chart pane was updated
        assert chart.chart_pane.object is not None

    @patch("app.components.admin_dashboard.charts.MetricsCollector")
    def test_chart_update_with_error(self, mock_collector_class):
        """Test chart update when data loading fails."""
        # Mock the metrics collector to raise an exception
        mock_collector = Mock()
        mock_collector_class.return_value = mock_collector
        mock_collector.get_historical_data.side_effect = Exception("Database error")

        chart = TimeSeriesChart()
        chart._update_chart()

        # Verify error chart was created
        assert chart.chart_pane.object is not None
        # The chart should be an error chart (we can't easily test the exact content)

    def test_chart_parameter_changes(self):
        """Test chart updates when parameters change."""
        chart = TimeSeriesChart()

        # Change time range
        original_time_range = chart.time_range
        chart.time_range = "7d"
        assert chart.time_range != original_time_range

        # Change selected metrics
        original_metrics = chart.selected_metrics.copy()
        chart.selected_metrics = ["cache_hit_rate", "pattern_lookup_ms"]
        assert chart.selected_metrics != original_metrics

    def test_get_panel_structure(self):
        """Test that get_panel returns proper Panel structure."""
        chart = TimeSeriesChart()
        panel = chart.get_panel()

        # Verify panel is returned
        assert panel is not None

        # Panel should be a Column with multiple components
        assert hasattr(panel, "objects")

    @patch("app.components.admin_dashboard.charts.MetricsCollector")
    def test_chart_with_empty_data(self, mock_collector_class):
        """Test chart behavior with empty data."""
        mock_collector = Mock()
        mock_collector_class.return_value = mock_collector
        mock_collector.get_historical_data.return_value = {}

        chart = TimeSeriesChart()
        chart._update_chart()

        # Chart should handle empty data gracefully
        assert chart.chart_pane.object is not None


class TestPerformanceChartsPanel:
    """Test PerformanceChartsPanel functionality."""

    def test_panel_initialization(self):
        """Test panel initialization."""
        panel = PerformanceChartsPanel()

        # Verify charts are created
        assert hasattr(panel, "performance_chart")
        assert hasattr(panel, "cache_chart")
        assert hasattr(panel, "learning_chart")

        # Verify chart configurations
        assert panel.performance_chart.selected_metrics == [
            "response_time_ms",
            "error_rate",
        ]
        assert panel.cache_chart.selected_metrics == [
            "cache_hit_rate",
            "pattern_lookup_ms",
        ]
        assert panel.learning_chart.selected_metrics == [
            "active_patterns",
            "pattern_accuracy",
        ]

    def test_get_panel_structure(self):
        """Test that get_panel returns proper structure."""
        panel = PerformanceChartsPanel()
        layout = panel.get_panel()

        # Verify layout is returned
        assert layout is not None

        # Layout should be a Column with multiple charts
        assert hasattr(layout, "objects")

        # Should contain multiple chart panels
        assert len(layout.objects) >= 3  # At least 3 charts plus spacers

    def test_chart_independence(self):
        """Test that charts operate independently."""
        panel = PerformanceChartsPanel()

        # Change one chart's time range
        panel.performance_chart.time_range = "7d"

        # Other charts should maintain their default time range
        assert panel.cache_chart.time_range == "24h"
        assert panel.learning_chart.time_range == "24h"

    def test_chart_metric_configurations(self):
        """Test that each chart has correct metric configurations."""
        panel = PerformanceChartsPanel()

        # Performance chart should have performance metrics
        perf_metrics = panel.performance_chart.selected_metrics
        assert "response_time_ms" in perf_metrics
        assert "error_rate" in perf_metrics

        # Cache chart should have cache metrics
        cache_metrics = panel.cache_chart.selected_metrics
        assert "cache_hit_rate" in cache_metrics
        assert "pattern_lookup_ms" in cache_metrics

        # Learning chart should have learning metrics
        learning_metrics = panel.learning_chart.selected_metrics
        assert "active_patterns" in learning_metrics
        assert "pattern_accuracy" in learning_metrics


class TestChartIntegration:
    """Test chart integration with metrics collector."""

    @patch("app.components.admin_dashboard.charts.MetricsCollector")
    def test_chart_data_flow(self, mock_collector_class, sample_metrics_data):
        """Test complete data flow from collector to chart."""
        # Setup mock collector with real data structure
        mock_collector = Mock()
        mock_collector_class.return_value = mock_collector

        # Create realistic data
        mock_data = {
            "response_time_ms": [
                {
                    "timestamp": "2024-01-01T12:00:00",
                    "value": 100,
                    "unit": "milliseconds",
                },
                {
                    "timestamp": "2024-01-01T13:00:00",
                    "value": 105,
                    "unit": "milliseconds",
                },
                {
                    "timestamp": "2024-01-01T14:00:00",
                    "value": 110,
                    "unit": "milliseconds",
                },
            ]
        }
        mock_collector.get_historical_data.return_value = mock_data

        # Create chart and update
        chart = TimeSeriesChart(selected_metrics=["response_time_ms"])
        chart._update_chart()

        # Verify data was requested correctly
        mock_collector.get_historical_data.assert_called_with(
            metric_names=["response_time_ms"], hours=24
        )

    def test_multiple_time_ranges(self):
        """Test charts with different time ranges."""
        chart = TimeSeriesChart()

        # Test different time ranges
        time_ranges = ["24h", "7d", "30d", "90d"]
        expected_hours = [24, 168, 720, 2160]

        for time_range, expected in zip(time_ranges, expected_hours):
            chart.time_range = time_range
            hours = chart._parse_time_range(time_range)
            assert hours == expected
