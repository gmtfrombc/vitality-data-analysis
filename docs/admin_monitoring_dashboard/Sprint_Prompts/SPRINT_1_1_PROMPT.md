# SPRINT 1.1 PROMPT - Dashboard Foundation & Health Status

## PROJECT CONTEXT

You are working on the **Admin Monitoring Dashboard Project** - creating a web-based monitoring interface for the AAA (Ask Anything AI Assistant) Learning System. This is Sprint 1.1 of an 8-sprint project across 3 phases.

### Project Overview
The AAA is a healthcare data analysis assistant with a recently deployed Learning Enhancement system. Currently, all post-deployment monitoring is done through CLI commands, which requires technical knowledge. We're building a modern, visual dashboard that allows non-technical healthcare administrators to monitor system health, performance, and learning metrics through a web interface.

### Current System Status
The AAA already has:
- **Working Panel application**: Main interface with data query, validation, and learning tabs
- **Learning System**: Recently deployed with `LearningSystemMonitor` and `CorrectionService`
- **CLI monitoring**: `scripts/learning_system_health_check.py` for health checks
- **SQLite database**: Existing patient data and learning system tables
- **Monitoring utilities**: `app/utils/learning_metrics.py` with comprehensive monitoring

## SPRINT 1.1 OBJECTIVES

**Goal**: Establish dashboard infrastructure and implement basic health status overview within the existing Panel application.

**Key Deliverables**:
1. New "Admin Dashboard" tab in Panel application
2. Database schema extensions for dashboard metrics
3. Basic `DashboardService` class for health status aggregation
4. Visual health status indicator (Green/Yellow/Red)
5. Component status cards for Database, Pattern Learning, Cache
6. Integration with existing `LearningSystemMonitor`

**User Impact**: Healthcare administrators can see system health at a glance without using CLI commands.

## TECHNICAL REQUIREMENTS

### Database Schema Extensions

Create `migrations/010_dashboard_tables.sql`:

```sql
-- Dashboard metrics history for trend analysis
CREATE TABLE IF NOT EXISTS dashboard_metrics_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metric_type VARCHAR(50) NOT NULL,  -- 'health', 'performance', 'learning'
    metric_name VARCHAR(100) NOT NULL,
    metric_value REAL,
    metric_unit VARCHAR(20),
    additional_data TEXT,  -- JSON for complex metrics
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Alert configurations for dashboard notifications
CREATE TABLE IF NOT EXISTS alert_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name VARCHAR(100) NOT NULL,
    threshold_type VARCHAR(20) NOT NULL,  -- 'warning', 'critical'
    threshold_value REAL NOT NULL,
    comparison_operator VARCHAR(10) NOT NULL,  -- '>', '<', '>=', '<=', '=='
    notification_enabled BOOLEAN DEFAULT 1,
    notification_email VARCHAR(255),
    notification_sms VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Dashboard user preferences
CREATE TABLE IF NOT EXISTS dashboard_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) DEFAULT 'default',
    preference_key VARCHAR(100) NOT NULL,
    preference_value TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Maintenance operation logs
CREATE TABLE IF NOT EXISTS maintenance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type VARCHAR(50) NOT NULL,  -- 'cache_cleanup', 'db_optimize', etc.
    operation_status VARCHAR(20) NOT NULL,  -- 'started', 'completed', 'failed'
    operation_details TEXT,  -- JSON with operation specifics
    duration_ms INTEGER,
    initiated_by VARCHAR(100) DEFAULT 'dashboard',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_metrics_history_timestamp ON dashboard_metrics_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_history_type_name ON dashboard_metrics_history(metric_type, metric_name);
CREATE INDEX IF NOT EXISTS idx_alert_config_metric_type ON alert_configurations(metric_name, threshold_type);
CREATE INDEX IF NOT EXISTS idx_dashboard_prefs_user_key ON dashboard_preferences(user_id, preference_key);
CREATE INDEX IF NOT EXISTS idx_maintenance_logs_timestamp ON maintenance_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_maintenance_logs_type ON maintenance_logs(operation_type);
```

### Dashboard Service Implementation

Create `app/services/dashboard_service.py`:

```python
"""
Dashboard Service for AAA Admin Monitoring

This service provides the core functionality for the admin monitoring dashboard,
integrating with existing monitoring utilities to provide a unified interface.

Sprint 1.1 Features:
- Health status aggregation from multiple sources
- Component status monitoring
- Basic metrics collection and storage
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.utils.saved_questions_db import DB_FILE
from app.utils.learning_metrics import LearningSystemMonitor
from app.services.correction_service import CorrectionService
from app.utils.db_migrations import apply_pending_migrations

logger = logging.getLogger(__name__)


@dataclass
class DashboardHealthStatus:
    """Overall dashboard health status."""
    overall_status: str  # "healthy", "warning", "critical"
    components: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Any]
    recommendations: List[str]
    last_updated: str


class DashboardService:
    """Main service for dashboard operations."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the dashboard service.
        
        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self.monitor = LearningSystemMonitor(db_path)
        self.correction_service = CorrectionService(db_path)
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Ensure all required dashboard tables exist."""
        try:
            apply_pending_migrations(self.db_path)
        except Exception as e:
            logger.error(f"Failed to apply dashboard migrations: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_health_status(self) -> DashboardHealthStatus:
        """Get comprehensive health status for dashboard display."""
        try:
            # Get health from existing monitor
            health = self.monitor.get_system_health()
            
            # Get current metrics
            current_metrics = self._get_current_metrics()
            
            # Build component status
            components = {
                'database': {
                    'status': 'connected' if health.database_connected else 'disconnected',
                    'response_time_ms': current_metrics.get('db_response_time', 0),
                    'icon': '✅' if health.database_connected else '❌'
                },
                'pattern_learning': {
                    'status': 'active' if health.pattern_learning_active else 'inactive',
                    'active_patterns': current_metrics.get('active_patterns', 0),
                    'icon': '✅' if health.pattern_learning_active else '❌'
                },
                'cache': {
                    'performance': health.cache_performance,
                    'hit_rate': current_metrics.get('cache_hit_rate', 0),
                    'icon': self._get_cache_icon(health.cache_performance)
                }
            }
            
            # Build metrics summary
            metrics = {
                'error_rate': health.recent_error_rate,
                'response_time_ms': current_metrics.get('avg_response_time', 0),
                'uptime_hours': current_metrics.get('uptime_hours', 0)
            }
            
            return DashboardHealthStatus(
                overall_status=health.overall_status,
                components=components,
                metrics=metrics,
                recommendations=health.recommendations,
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return self._get_fallback_health_status()
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            # Get comprehensive metrics from monitor
            metrics = self.monitor.get_comprehensive_metrics()
            
            return {
                'db_response_time': 50,  # Placeholder - would measure actual DB response
                'active_patterns': metrics.usage_metrics.get('active_patterns', 0),
                'cache_hit_rate': metrics.performance_metrics.get('cache_hit_rate', 0),
                'avg_response_time': metrics.performance_metrics.get('average_response_time_ms', 0),
                'uptime_hours': 24  # Placeholder - would calculate actual uptime
            }
        except Exception as e:
            logger.error(f"Failed to get current metrics: {e}")
            return {}
    
    def _get_cache_icon(self, performance: str) -> str:
        """Get icon for cache performance."""
        if performance in ['excellent', 'good']:
            return '✅'
        elif performance == 'fair':
            return '⚠️'
        else:
            return '❌'
    
    def _get_fallback_health_status(self) -> DashboardHealthStatus:
        """Get fallback health status when monitoring fails."""
        return DashboardHealthStatus(
            overall_status="critical",
            components={
                'database': {'status': 'unknown', 'icon': '❓'},
                'pattern_learning': {'status': 'unknown', 'icon': '❓'},
                'cache': {'performance': 'unknown', 'icon': '❓'}
            },
            metrics={'error_rate': 1.0},
            recommendations=["Dashboard monitoring system failure - check logs"],
            last_updated=datetime.now().isoformat()
        )
    
    def store_metric(self, metric_type: str, metric_name: str, value: float, unit: str = None):
        """Store a metric value in the dashboard history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO dashboard_metrics_history 
                    (metric_type, metric_name, metric_value, metric_unit)
                    VALUES (?, ?, ?, ?)
                """, (metric_type, metric_name, value, unit))
                
        except Exception as e:
            logger.error(f"Failed to store metric {metric_name}: {e}")
```

### Dashboard UI Components

Create `app/components/admin_dashboard/__init__.py`:

```python
"""
Admin Dashboard Components

Panel-based components for the admin monitoring dashboard.
"""

from .dashboard_tab import AdminDashboardTab

__all__ = ['AdminDashboardTab']
```

Create `app/components/admin_dashboard/dashboard_tab.py`:

```python
"""
Main Admin Dashboard Tab

This module provides the main dashboard tab that integrates into the existing
Panel application, providing health status monitoring and system overview.
"""

import panel as pn
import param
from typing import Dict, Any

from app.services.dashboard_service import DashboardService


class AdminDashboardTab(param.Parameterized):
    """Main admin dashboard tab for Panel application."""
    
    # Reactive parameters for real-time updates
    health_status = param.Dict(default={})
    last_refresh = param.String(default="Never")
    auto_refresh_enabled = param.Boolean(default=True)
    
    def __init__(self, **params):
        super().__init__(**params)
        self.dashboard_service = DashboardService()
        self._setup_layout()
        self._refresh_data()
    
    def _setup_layout(self):
        """Set up the dashboard layout."""
        # Overall status indicator
        self.status_indicator = pn.pane.HTML(
            "<div style='text-align: center; font-size: 24px; padding: 20px;'>"
            "🔄 Loading system status..."
            "</div>",
            sizing_mode="stretch_width"
        )
        
        # Component status cards
        self.component_cards = pn.Row(
            sizing_mode="stretch_width"
        )
        
        # Metrics summary
        self.metrics_summary = pn.pane.HTML(
            "<div style='padding: 10px;'>Loading metrics...</div>",
            sizing_mode="stretch_width"
        )
        
        # Control buttons
        self.refresh_button = pn.widgets.Button(
            name="🔄 Refresh Now",
            button_type="primary",
            sizing_mode="fixed",
            width=150
        )
        self.refresh_button.on_click(self._manual_refresh)
        
        # Auto-refresh toggle
        self.auto_refresh_toggle = pn.widgets.Checkbox(
            name="Auto-refresh (5 min)",
            value=True,
            sizing_mode="fixed"
        )
        
        # Last updated indicator
        self.last_updated = pn.pane.HTML(
            "Last updated: Never",
            sizing_mode="fixed"
        )
        
        # Control panel
        self.controls = pn.Row(
            self.refresh_button,
            self.auto_refresh_toggle,
            self.last_updated,
            sizing_mode="stretch_width"
        )
    
    def _refresh_data(self):
        """Refresh dashboard data from service."""
        try:
            health_status = self.dashboard_service.get_health_status()
            self._update_status_indicator(health_status)
            self._update_component_cards(health_status)
            self._update_metrics_summary(health_status)
            self._update_last_updated(health_status.last_updated)
            
        except Exception as e:
            self._show_error(f"Failed to refresh data: {e}")
    
    def _update_status_indicator(self, health_status):
        """Update the main status indicator."""
        status = health_status.overall_status
        
        if status == "healthy":
            color = "#28a745"  # Green
            icon = "✅"
            message = "System Healthy"
        elif status == "warning":
            color = "#ffc107"  # Yellow
            icon = "⚠️"
            message = "System Warning"
        else:  # critical
            color = "#dc3545"  # Red
            icon = "❌"
            message = "System Critical"
        
        html = f"""
        <div style='text-align: center; padding: 30px; background-color: {color}20; 
                    border: 2px solid {color}; border-radius: 10px; margin: 10px;'>
            <div style='font-size: 48px; margin-bottom: 10px;'>{icon}</div>
            <div style='font-size: 24px; font-weight: bold; color: {color};'>{message}</div>
            <div style='font-size: 14px; margin-top: 10px; color: #666;'>
                Overall system status
            </div>
        </div>
        """
        
        self.status_indicator.object = html
    
    def _update_component_cards(self, health_status):
        """Update component status cards."""
        cards = []
        
        for component_name, component_data in health_status.components.items():
            card_html = self._create_component_card(component_name, component_data)
            cards.append(pn.pane.HTML(card_html, sizing_mode="stretch_width"))
        
        self.component_cards.objects = cards
    
    def _create_component_card(self, name: str, data: Dict[str, Any]) -> str:
        """Create HTML for a component status card."""
        display_name = name.replace('_', ' ').title()
        icon = data.get('icon', '❓')
        status = data.get('status', 'unknown')
        
        # Additional info based on component
        extra_info = ""
        if name == 'database':
            response_time = data.get('response_time_ms', 0)
            extra_info = f"Response: {response_time}ms"
        elif name == 'pattern_learning':
            patterns = data.get('active_patterns', 0)
            extra_info = f"Active patterns: {patterns}"
        elif name == 'cache':
            hit_rate = data.get('hit_rate', 0)
            extra_info = f"Hit rate: {hit_rate:.1%}"
        
        return f"""
        <div style='border: 1px solid #ddd; border-radius: 8px; padding: 15px; 
                    margin: 5px; background-color: #f8f9fa;'>
            <div style='text-align: center; font-size: 32px; margin-bottom: 10px;'>{icon}</div>
            <div style='text-align: center; font-weight: bold; font-size: 16px;'>{display_name}</div>
            <div style='text-align: center; color: #666; font-size: 14px;'>{status}</div>
            {f'<div style="text-align: center; color: #888; font-size: 12px; margin-top: 5px;">{extra_info}</div>' if extra_info else ''}
        </div>
        """
    
    def _update_metrics_summary(self, health_status):
        """Update metrics summary display."""
        metrics = health_status.metrics
        error_rate = metrics.get('error_rate', 0)
        response_time = metrics.get('response_time_ms', 0)
        uptime = metrics.get('uptime_hours', 0)
        
        html = f"""
        <div style='padding: 15px; background-color: #f8f9fa; border-radius: 8px; margin: 10px;'>
            <h4 style='margin-top: 0;'>System Metrics</h4>
            <div style='display: flex; justify-content: space-around; text-align: center;'>
                <div>
                    <div style='font-size: 24px; font-weight: bold; color: {"#dc3545" if error_rate > 0.1 else "#28a745"};'>
                        {error_rate:.1%}
                    </div>
                    <div style='font-size: 12px; color: #666;'>Error Rate</div>
                </div>
                <div>
                    <div style='font-size: 24px; font-weight: bold; color: {"#dc3545" if response_time > 150 else "#28a745"};'>
                        {response_time:.0f}ms
                    </div>
                    <div style='font-size: 12px; color: #666;'>Response Time</div>
                </div>
                <div>
                    <div style='font-size: 24px; font-weight: bold; color: #007bff;'>
                        {uptime:.0f}h
                    </div>
                    <div style='font-size: 12px; color: #666;'>Uptime</div>
                </div>
            </div>
        </div>
        """
        
        self.metrics_summary.object = html
    
    def _update_last_updated(self, timestamp: str):
        """Update last updated timestamp."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            self.last_updated.object = f"Last updated: {formatted_time}"
        except:
            self.last_updated.object = f"Last updated: {timestamp}"
    
    def _manual_refresh(self, event=None):
        """Handle manual refresh button click."""
        self._refresh_data()
    
    def _show_error(self, message: str):
        """Show error message in dashboard."""
        self.status_indicator.object = f"""
        <div style='text-align: center; padding: 30px; background-color: #dc354520; 
                    border: 2px solid #dc3545; border-radius: 10px; margin: 10px;'>
            <div style='font-size: 48px; margin-bottom: 10px;'>❌</div>
            <div style='font-size: 18px; font-weight: bold; color: #dc3545;'>Dashboard Error</div>
            <div style='font-size: 14px; margin-top: 10px; color: #666;'>{message}</div>
        </div>
        """
    
    def get_panel(self):
        """Get the Panel layout for the dashboard."""
        return pn.Column(
            "# 🖥️ Admin Monitoring Dashboard",
            self.status_indicator,
            self.component_cards,
            self.metrics_summary,
            self.controls,
            sizing_mode="stretch_width"
        )
```

### Integration with Main Application

Modify the main Panel application to include the dashboard tab. You'll need to find where tabs are defined (likely in `run.py` or similar) and add:

```python
from app.components.admin_dashboard import AdminDashboardTab

# In the tab creation section, add:
admin_dashboard = AdminDashboardTab()
dashboard_tab = ("🖥️ Admin Dashboard", admin_dashboard.get_panel())

# Add to the tabs list
```

## FILES TO CREATE/MODIFY

### Files to Create
```
migrations/010_dashboard_tables.sql
app/services/dashboard_service.py
app/components/admin_dashboard/__init__.py
app/components/admin_dashboard/dashboard_tab.py
tests/services/test_dashboard_service.py
```

### Files to Modify
- Main Panel application file (likely `run.py`) to add dashboard tab
- `app/services/__init__.py` to include DashboardService

## TESTING REQUIREMENTS

Create `tests/services/test_dashboard_service.py`:

```python
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
                'dashboard_metrics_history',
                'alert_configurations', 
                'dashboard_preferences',
                'maintenance_logs'
            ]
            
            for table in tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                assert cursor.fetchone() is not None, f"Table {table} not found"
    
    def test_get_health_status(self, dashboard_service):
        """Test getting health status."""
        health_status = dashboard_service.get_health_status()
        
        assert isinstance(health_status, DashboardHealthStatus)
        assert health_status.overall_status in ['healthy', 'warning', 'critical']
        assert 'database' in health_status.components
        assert 'pattern_learning' in health_status.components
        assert 'cache' in health_status.components
        assert health_status.last_updated is not None
    
    def test_store_metric(self, dashboard_service, temp_db):
        """Test storing metrics."""
        dashboard_service.store_metric('health', 'error_rate', 0.05, 'percentage')
        
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metric_type, metric_name, metric_value, metric_unit 
                FROM dashboard_metrics_history 
                WHERE metric_name = 'error_rate'
            """)
            
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == 'health'
            assert row[1] == 'error_rate'
            assert row[2] == 0.05
            assert row[3] == 'percentage'
    
    def test_fallback_health_status(self, dashboard_service):
        """Test fallback health status when monitoring fails."""
        # This would require mocking the monitor to fail
        # For now, just verify the fallback method exists
        fallback = dashboard_service._get_fallback_health_status()
        
        assert fallback.overall_status == "critical"
        assert "failure" in fallback.recommendations[0].lower()
```

## SUCCESS CRITERIA

You are done when:
- [ ] Migration file creates all 4 dashboard tables with proper schema
- [ ] `DashboardService` can aggregate health status from existing monitors
- [ ] Admin Dashboard tab displays in Panel application
- [ ] Health status indicator shows Green/Yellow/Red based on system status
- [ ] Component status cards display Database, Pattern Learning, and Cache status
- [ ] Manual refresh button updates dashboard data
- [ ] All tests pass and verify core functionality
- [ ] No existing functionality is broken
- [ ] Dashboard integrates seamlessly with existing Panel app

## DEVELOPMENT WORKFLOW

1. **Create migration file first** - Establish database foundation
2. **Run migration** - Verify tables are created
3. **Implement DashboardService** - Core health status aggregation
4. **Create dashboard UI components** - Panel-based interface
5. **Integrate with main application** - Add dashboard tab
6. **Create comprehensive tests** - Verify functionality
7. **Test integration** - Ensure no breaking changes

## TESTING & VALIDATION

After implementation:

1. **Run migration**:
   ```bash
   python -c "from app.utils.db_migrations import apply_pending_migrations; apply_pending_migrations('patient_data.db')"
   ```

2. **Run tests**:
   ```bash
   pytest tests/services/test_dashboard_service.py -v
   ```

3. **Start application and verify**:
   ```bash
   python run.py
   ```
   - Navigate to Admin Dashboard tab
   - Verify health status displays correctly
   - Test refresh functionality

4. **Commit changes**:
   ```bash
   git add . && git commit -m "Sprint 1.1: Add dashboard foundation and health status

   - Add migration 010 with 4 new dashboard tables
   - Implement DashboardService for health status aggregation
   - Create Admin Dashboard tab with health status display
   - Add component status cards for Database, Pattern Learning, Cache
   - Integrate with existing LearningSystemMonitor
   - Add comprehensive tests for dashboard functionality" && git push origin main
   ```

## IMPORTANT NOTES

- **Integration Focus**: Leverage existing `LearningSystemMonitor` and `CorrectionService`
- **Visual Design**: Professional appearance consistent with existing Panel app
- **Error Handling**: Graceful fallbacks when monitoring services fail
- **Performance**: Dashboard should load quickly without impacting existing functionality
- **Backward Compatibility**: All existing functionality must continue to work

## NEXT SPRINT PREVIEW

Sprint 1.2 will add:
- One-click health check execution
- Performance metrics display
- Auto-refresh functionality
- Basic alert notifications

---

**START IMPLEMENTING SPRINT 1.1 NOW** 