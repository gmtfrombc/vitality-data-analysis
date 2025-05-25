# SPRINT 2.1 PROMPT - Historical Trends & Time-Series Charts

## PROJECT CONTEXT

You are working on the **Admin Monitoring Dashboard Project** - creating a web-based monitoring interface for the AAA (Ask Anything AI Assistant) Learning System. This is Sprint 2.1, beginning Phase 2 of an 8-sprint project across 3 phases.

### Project Overview
Phase 2 focuses on advanced monitoring capabilities. Sprint 2.1 adds historical trend analysis with interactive time-series charts, allowing healthcare administrators to identify patterns and trends over time.

### Current System Status (Post Phase 1)
The AAA now has a production-ready dashboard with:
- **Core Dashboard**: Health status overview with component cards
- **Interactive Features**: One-click health checks and performance metrics
- **Auto-refresh**: Configurable refresh intervals with alert notifications
- **User-Tested Interface**: Refined UI based on healthcare administrator feedback
- **Performance Optimizations**: Caching and database optimizations

### What Was Completed in Phase 1
- ✅ Dashboard foundation with database schema and service layer
- ✅ Interactive health checks with progress indicators
- ✅ Basic performance metrics and alert system
- ✅ User testing and UI refinements
- ✅ Production-ready Phase 1 release

## SPRINT 2.1 OBJECTIVES

**Goal**: Implement historical data collection, storage, and visualization through interactive time-series charts that allow administrators to analyze trends over time.

**Key Deliverables**:
1. Automated historical metrics collection and storage
2. Interactive Bokeh time-series charts for trend visualization
3. Time period selectors (24h, 7d, 30d, 90d views)
4. Data retention policies and automated cleanup
5. Performance optimization for large datasets
6. Historical trend analysis for key metrics

**User Impact**: Healthcare administrators can identify trends, patterns, and potential issues before they become critical by analyzing historical performance data.

## TECHNICAL REQUIREMENTS

### Historical Data Collection Service

Create `app/services/metrics_collector.py`:

```python
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
        logger.info(f"Started metrics collection with {self.collection_interval}s interval")
    
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
                unit="milliseconds"
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="pattern_lookup_ms",
                value=metrics.performance_metrics.get("pattern_lookup_ms", 0),
                unit="milliseconds"
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="cache_hit_rate",
                value=metrics.performance_metrics.get("cache_hit_rate", 0),
                unit="percentage"
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="error_rate",
                value=metrics.error_metrics.get("recent_error_rate", 0),
                unit="percentage"
            )
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
                unit="milliseconds"
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="health",
                metric_name="memory_usage_mb",
                value=metrics.system_metrics.get("memory_usage_mb", 0),
                unit="megabytes"
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="health",
                metric_name="active_connections",
                value=metrics.system_metrics.get("active_connections", 0),
                unit="count"
            )
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
                unit="count"
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="learning",
                metric_name="pattern_accuracy",
                value=metrics.learning_metrics.get("pattern_accuracy", 0),
                unit="percentage"
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="learning",
                metric_name="correction_success_rate",
                value=metrics.learning_metrics.get("correction_success_rate", 0),
                unit="percentage"
            )
        ]
        
        self._store_metrics_batch(learning_data)
    
    def _store_metrics_batch(self, metrics: List[MetricDataPoint]):
        """Store a batch of metrics in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for metric in metrics:
                    additional_data_json = json.dumps(metric.additional_data) if metric.additional_data else None
                    
                    cursor.execute("""
                        INSERT INTO dashboard_metrics_history 
                        (timestamp, metric_type, metric_name, metric_value, metric_unit, additional_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        metric.timestamp.isoformat(),
                        metric.metric_type,
                        metric.metric_name,
                        metric.value,
                        metric.unit,
                        additional_data_json
                    ))
                
        except Exception as e:
            logger.error(f"Failed to store metrics batch: {e}")
    
    def get_historical_data(self, metric_names: List[str], hours: int = 24) -> Dict[str, List[Dict]]:
        """Get historical data for specified metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                since_time = datetime.now() - timedelta(hours=hours)
                
                # Build query for multiple metrics
                placeholders = ','.join(['?' for _ in metric_names])
                cursor.execute(f"""
                    SELECT timestamp, metric_name, metric_value, metric_unit
                    FROM dashboard_metrics_history 
                    WHERE metric_name IN ({placeholders})
                    AND timestamp > ?
                    ORDER BY timestamp ASC
                """, metric_names + [since_time.isoformat()])
                
                rows = cursor.fetchall()
                
                # Organize data by metric name
                result = {}
                for row in rows:
                    metric_name = row["metric_name"]
                    if metric_name not in result:
                        result[metric_name] = []
                    
                    result[metric_name].append({
                        "timestamp": row["timestamp"],
                        "value": row["metric_value"],
                        "unit": row["metric_unit"]
                    })
                
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
                
                cursor.execute("""
                    DELETE FROM dashboard_metrics_history 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                
                logger.info(f"Cleaned up {deleted_count} old metric records")
                
                return {
                    "deleted_records": deleted_count,
                    "cutoff_date": cutoff_date.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return {"deleted_records": 0}
```

### Time-Series Chart Components

Create `app/components/admin_dashboard/charts.py`:

```python
"""
Chart components for the admin monitoring dashboard.

This module provides Bokeh-based interactive charts for displaying
historical trends and time-series data.
"""

import panel as pn
import param
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import HoverTool, DatetimeTickFormatter
from bokeh.palettes import Category10
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from app.services.metrics_collector import MetricsCollector


class TimeSeriesChart(param.Parameterized):
    """Interactive time-series chart for metrics visualization."""
    
    # Parameters for reactive updates
    time_range = param.ObjectSelector(
        default="24h",
        objects=["24h", "7d", "30d", "90d"],
        doc="Time range for chart data"
    )
    
    selected_metrics = param.List(
        default=["response_time_ms", "error_rate"],
        doc="List of metrics to display"
    )
    
    def __init__(self, **params):
        super().__init__(**params)
        self.metrics_collector = MetricsCollector()
        self.chart_pane = pn.pane.Bokeh(sizing_mode="stretch_width", height=400)
        self._setup_chart()
        
        # Watch for parameter changes
        self.param.watch(self._update_chart, ['time_range', 'selected_metrics'])
    
    def _setup_chart(self):
        """Set up the initial chart."""
        self._update_chart()
    
    def _update_chart(self, *events):
        """Update chart with current data."""
        try:
            # Get time range in hours
            hours = self._parse_time_range(self.time_range)
            
            # Get historical data
            data = self.metrics_collector.get_historical_data(
                metric_names=self.selected_metrics,
                hours=hours
            )
            
            # Create chart
            chart = self._create_bokeh_chart(data, hours)
            self.chart_pane.object = chart
            
        except Exception as e:
            # Show error in chart
            error_chart = self._create_error_chart(str(e))
            self.chart_pane.object = error_chart
    
    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to hours."""
        if time_range == "24h":
            return 24
        elif time_range == "7d":
            return 24 * 7
        elif time_range == "30d":
            return 24 * 30
        elif time_range == "90d":
            return 24 * 90
        else:
            return 24
    
    def _create_bokeh_chart(self, data: Dict[str, List[Dict]], hours: int) -> figure:
        """Create Bokeh chart from data."""
        # Create figure
        p = figure(
            title=f"Performance Metrics - Last {self.time_range}",
            x_axis_type='datetime',
            width=800,
            height=400,
            tools="pan,wheel_zoom,box_zoom,reset,save"
        )
        
        # Color palette for multiple metrics
        colors = Category10[max(3, len(self.selected_metrics))]
        
        # Add line for each metric
        for i, metric_name in enumerate(self.selected_metrics):
            if metric_name in data and data[metric_name]:
                metric_data = data[metric_name]
                
                # Convert to pandas for easier handling
                df = pd.DataFrame(metric_data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Add line to chart
                line = p.line(
                    x='timestamp',
                    y='value',
                    source=df,
                    legend_label=self._format_metric_name(metric_name),
                    line_width=2,
                    color=colors[i % len(colors)]
                )
                
                # Add circle markers
                p.circle(
                    x='timestamp',
                    y='value',
                    source=df,
                    size=4,
                    color=colors[i % len(colors)],
                    alpha=0.6
                )
                
                # Add hover tool for this line
                hover = HoverTool(
                    tooltips=[
                        ("Metric", metric_name),
                        ("Time", "@timestamp{%F %T}"),
                        ("Value", "@value{0.00}"),
                        ("Unit", f"{metric_data[0].get('unit', '')}")
                    ],
                    formatters={"@timestamp": "datetime"},
                    renderers=[line]
                )
                p.add_tools(hover)
        
        # Customize chart appearance
        p.title.text_font_size = "16pt"
        p.legend.location = "top_left"
        p.legend.click_policy = "hide"
        
        # Format x-axis
        p.xaxis.formatter = DatetimeTickFormatter(
            hours="%H:%M",
            days="%m/%d",
            months="%m/%Y"
        )
        
        # Set y-axis label
        p.yaxis.axis_label = "Value"
        
        return p
    
    def _format_metric_name(self, metric_name: str) -> str:
        """Format metric name for display."""
        name_map = {
            "response_time_ms": "Response Time (ms)",
            "error_rate": "Error Rate (%)",
            "cache_hit_rate": "Cache Hit Rate (%)",
            "pattern_lookup_ms": "Pattern Lookup (ms)",
            "active_patterns": "Active Patterns",
            "pattern_accuracy": "Pattern Accuracy (%)"
        }
        return name_map.get(metric_name, metric_name.replace('_', ' ').title())
    
    def _create_error_chart(self, error_message: str) -> figure:
        """Create error chart when data loading fails."""
        p = figure(
            title="Chart Error",
            width=800,
            height=400,
            tools=""
        )
        
        # Add error text
        p.text(
            x=[0.5], y=[0.5],
            text=[f"Error loading chart data: {error_message}"],
            text_align="center",
            text_baseline="middle"
        )
        
        # Remove axes
        p.xaxis.visible = False
        p.yaxis.visible = False
        p.grid.visible = False
        
        return p
    
    def get_panel(self) -> pn.Panel:
        """Get Panel layout for the chart."""
        # Time range selector
        time_selector = pn.widgets.RadioButtonGroup(
            name="Time Range",
            options=["24h", "7d", "30d", "90d"],
            value=self.time_range,
            button_type="outline"
        )
        time_selector.link(self, value='time_range')
        
        # Metric selector
        metric_options = [
            "response_time_ms",
            "error_rate", 
            "cache_hit_rate",
            "pattern_lookup_ms",
            "active_patterns",
            "pattern_accuracy"
        ]
        
        metric_selector = pn.widgets.CheckBoxGroup(
            name="Metrics to Display",
            options=metric_options,
            value=self.selected_metrics
        )
        metric_selector.link(self, value='selected_metrics')
        
        # Refresh button
        refresh_button = pn.widgets.Button(
            name="🔄 Refresh Chart",
            button_type="outline",
            width=120
        )
        refresh_button.on_click(lambda event: self._update_chart())
        
        # Controls panel
        controls = pn.Row(
            time_selector,
            refresh_button,
            sizing_mode="stretch_width"
        )
        
        metrics_panel = pn.Column(
            metric_selector,
            width=200
        )
        
        # Main layout
        return pn.Column(
            "## 📈 Historical Trends",
            controls,
            pn.Row(
                self.chart_pane,
                metrics_panel,
                sizing_mode="stretch_width"
            ),
            sizing_mode="stretch_width"
        )


class PerformanceChartsPanel(param.Parameterized):
    """Panel containing multiple performance charts."""
    
    def __init__(self, **params):
        super().__init__(**params)
        self.setup_charts()
    
    def setup_charts(self):
        """Set up multiple chart panels."""
        # Response time and error rate chart
        self.performance_chart = TimeSeriesChart(
            selected_metrics=["response_time_ms", "error_rate"],
            name="Performance Metrics"
        )
        
        # Cache and pattern metrics chart
        self.cache_chart = TimeSeriesChart(
            selected_metrics=["cache_hit_rate", "pattern_lookup_ms"],
            name="Cache & Pattern Metrics"
        )
        
        # Learning system metrics chart
        self.learning_chart = TimeSeriesChart(
            selected_metrics=["active_patterns", "pattern_accuracy"],
            name="Learning System Metrics"
        )
    
    def get_panel(self) -> pn.Panel:
        """Get complete charts panel."""
        return pn.Column(
            self.performance_chart.get_panel(),
            pn.Spacer(height=20),
            self.cache_chart.get_panel(),
            pn.Spacer(height=20),
            self.learning_chart.get_panel(),
            sizing_mode="stretch_width"
        )
```

### Enhanced Dashboard Integration

Extend `app/components/admin_dashboard/dashboard_tab.py` to include charts:

```python
# Add these imports and methods to the existing AdminDashboardTab class

from app.components.admin_dashboard.charts import PerformanceChartsPanel
from app.services.metrics_collector import MetricsCollector

class AdminDashboardTab(param.Parameterized):
    # Add new parameter
    show_charts = param.Boolean(default=False)
    
    def __init__(self, **params):
        super().__init__(**params)
        # ... existing initialization ...
        
        # Initialize metrics collector
        self.metrics_collector = MetricsCollector()
        
        # Initialize charts panel
        self.charts_panel = PerformanceChartsPanel()
        
        # Start metrics collection
        self.metrics_collector.start_collection()
    
    def _setup_layout(self):
        """Enhanced layout setup with charts."""
        # ... existing layout setup ...
        
        # Charts toggle button
        self.charts_toggle = pn.widgets.Toggle(
            name="📈 Show Historical Charts",
            value=self.show_charts,
            sizing_mode="fixed",
            width=200
        )
        self.charts_toggle.link(self, value='show_charts')
        
        # Charts section (initially hidden)
        self.charts_section = pn.Column(
            self.charts_panel.get_panel(),
            visible=self.show_charts,
            sizing_mode="stretch_width"
        )
        
        # Watch for charts toggle
        self.param.watch(self._toggle_charts, 'show_charts')
    
    def _toggle_charts(self, event):
        """Toggle charts visibility."""
        self.charts_section.visible = self.show_charts
    
    def get_panel(self):
        """Get enhanced Panel layout with charts."""
        return pn.Column(
            "# 🖥️ Admin Monitoring Dashboard",
            self.alerts_panel,
            self.status_indicator,
            self.progress_indicator,
            self.component_cards,
            self.metrics_summary,
            self.performance_metrics,
            self.enhanced_controls,
            self.charts_toggle,
            self.charts_section,
            self.last_updated,
            sizing_mode="stretch_width"
        )
```

## FILES TO CREATE/MODIFY

### Files to Create
```
app/services/metrics_collector.py
app/components/admin_dashboard/charts.py
tests/services/test_metrics_collector.py
tests/components/test_charts.py
```

### Files to Modify
```
app/components/admin_dashboard/dashboard_tab.py - Add charts integration
app/services/dashboard_service.py - Add historical data methods
```

## TESTING REQUIREMENTS

Create `tests/services/test_metrics_collector.py`:

```python
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
            unit="milliseconds"
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
                unit="milliseconds"
            ),
            MetricDataPoint(
                timestamp=timestamp,
                metric_type="performance",
                metric_name="error_rate",
                value=0.05,
                unit="percentage"
            )
        ]
        
        metrics_collector._store_metrics_batch(metrics)
        
        # Verify data was stored
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metric_name, metric_value, metric_unit 
                FROM dashboard_metrics_history 
                WHERE metric_type = 'performance'
                ORDER BY metric_name
            """)
            
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
                unit="milliseconds"
            ),
            MetricDataPoint(
                timestamp=timestamp - timedelta(hours=1),
                metric_type="performance",
                metric_name="response_time_ms",
                value=110.0,
                unit="milliseconds"
            )
        ]
        
        metrics_collector._store_metrics_batch(metrics)
        
        # Get historical data
        data = metrics_collector.get_historical_data(
            metric_names=["response_time_ms"],
            hours=24
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
                value=100.0
            ),
            MetricDataPoint(
                timestamp=new_timestamp,
                metric_type="performance",
                metric_name="response_time_ms",
                value=110.0
            )
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
```

## SUCCESS CRITERIA

You are done when:
- [ ] Automated metrics collection runs in background
- [ ] Historical data is stored with proper timestamps and organization
- [ ] Interactive Bokeh charts display time-series data correctly
- [ ] Time period selectors (24h, 7d, 30d, 90d) work properly
- [ ] Multiple metrics can be displayed on same chart
- [ ] Data retention policies automatically clean up old data
- [ ] Charts are responsive and performant with large datasets
- [ ] All tests pass and verify chart functionality
- [ ] Charts integrate seamlessly with existing dashboard

## DEVELOPMENT WORKFLOW

1. **Create metrics collector** - Automated background data collection
2. **Implement data storage** - Efficient storage of time-series data
3. **Build chart components** - Interactive Bokeh charts with Panel
4. **Add time selectors** - Multiple time range options
5. **Integrate with dashboard** - Seamless integration with existing UI
6. **Optimize performance** - Handle large datasets efficiently
7. **Create comprehensive tests** - Verify all chart functionality

## TESTING & VALIDATION

After implementation:

1. **Run tests**:
   ```bash
   pytest tests/services/test_metrics_collector.py -v
   pytest tests/components/test_charts.py -v
   ```

2. **Test metrics collection**:
   ```bash
   python -c "
   from app.services.metrics_collector import MetricsCollector
   import time
   
   collector = MetricsCollector(collection_interval=5)
   collector.start_collection()
   print('Collection started, waiting 10 seconds...')
   time.sleep(10)
   collector.stop_collection()
   print('Collection stopped')
   "
   ```

3. **Test dashboard with charts**:
   ```bash
   python run.py
   ```
   - Navigate to Admin Dashboard
   - Toggle "Show Historical Charts"
   - Test different time ranges
   - Verify chart interactivity

4. **Commit changes**:
   ```bash
   git add . && git commit -m "Sprint 2.1: Add historical trends and time-series charts

   - Implement automated metrics collection service
   - Create interactive Bokeh time-series charts
   - Add time period selectors (24h, 7d, 30d, 90d)
   - Implement data retention policies and cleanup
   - Optimize performance for large datasets
   - Integrate charts with existing dashboard
   - Add comprehensive tests for metrics collection and charts" && git push origin main
   ```

## IMPORTANT NOTES

- **Performance**: Charts must handle large datasets efficiently
- **Interactivity**: Charts should be responsive and user-friendly
- **Data Quality**: Ensure accurate timestamps and metric values
- **Memory Management**: Background collection should not impact system performance
- **Visual Design**: Charts should match dashboard aesthetic

## NEXT SPRINT PREVIEW

Sprint 2.2 will add:
- Learning system analytics and pattern effectiveness tracking
- Advanced pattern performance visualization
- User feedback analysis and correction success trends
- Learning progress indicators and milestones

---

**START IMPLEMENTING SPRINT 2.1 NOW** 