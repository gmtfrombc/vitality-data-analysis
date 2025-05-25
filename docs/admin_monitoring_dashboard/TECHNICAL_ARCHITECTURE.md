# Admin Monitoring Dashboard - Technical Architecture

## System Architecture Overview

### High-Level Architecture

The Admin Monitoring Dashboard extends the existing AAA Panel application with a new monitoring interface that leverages current infrastructure while adding minimal complexity. The architecture follows a modular approach that integrates seamlessly with existing components.

```
┌─────────────────────────────────────────────────────────────┐
│                    AAA Panel Application                    │
├─────────────────────────────────────────────────────────────┤
│  Existing Tabs  │           New Admin Dashboard Tab         │
│  - Data Query   │  ┌─────────────────────────────────────┐  │
│  - Validation   │  │  Dashboard Components               │  │
│  - Learning     │  │  ├─ Health Overview                 │  │
│                 │  │  ├─ Performance Monitoring          │  │
│                 │  │  ├─ Learning Analytics              │  │
│                 │  │  ├─ Maintenance Tools               │  │
│                 │  │  └─ Alerts & Configuration          │  │
│                 │  └─────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Backend Services Layer                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Existing        │  │ Dashboard       │  │ Alert       │  │
│  │ Services        │  │ Service         │  │ Service     │  │
│  │ - Correction    │  │ - Metrics       │  │ - Threshold │  │
│  │ - Learning      │  │ - Health Check  │  │ - Notify    │  │
│  │ - Query         │  │ - Performance   │  │ - History   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Data Layer                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              SQLite Database                            │ │
│  │  ┌─────────────────┐  ┌─────────────────────────────┐   │ │
│  │  │ Existing Tables │  │ New Dashboard Tables        │   │ │
│  │  │ - Patients      │  │ - dashboard_metrics_history │   │ │
│  │  │ - Corrections   │  │ - alert_configurations      │   │ │
│  │  │ - Patterns      │  │ - dashboard_preferences     │   │ │
│  │  │ - Cache         │  │ - maintenance_logs          │   │ │
│  │  └─────────────────┘  └─────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

#### Frontend Layer (Panel/Bokeh)
- **Dashboard Container**: Main Panel tab containing all monitoring components
- **Health Status Widget**: Real-time system health visualization
- **Performance Charts**: Bokeh-based time-series visualizations
- **Control Panels**: Interactive widgets for configuration and actions
- **Alert Notifications**: Real-time alert display and management

#### Service Layer (Python)
- **Dashboard Service**: Core monitoring logic and data aggregation
- **Alert Service**: Threshold monitoring and notification management
- **Export Service**: Report generation and data export functionality
- **Cache Service**: Performance optimization and data caching

#### Data Layer (SQLite)
- **Extended Schema**: New tables for dashboard-specific data
- **Optimized Indexes**: Performance indexes for dashboard queries
- **Data Retention**: Automated cleanup of historical data

## Component Relationships and Data Flow

### Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Action   │───▶│  Dashboard UI   │───▶│ Backend Service │
│ (Click, Refresh)│    │   Component     │    │   (Process)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Visual        │◀───│   Data          │◀───│   Database      │
│  Presentation   │    │  Aggregation    │    │    Query        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Interactions

#### Health Monitoring Flow
1. **Dashboard Service** calls `LearningSystemMonitor.get_system_health()`
2. **Health data** aggregated from multiple sources (DB, cache, patterns)
3. **Status indicators** updated in real-time via Panel reactive parameters
4. **Alerts triggered** if thresholds exceeded

#### Performance Monitoring Flow
1. **Performance metrics** collected via `LearningSystemMonitor.get_comprehensive_metrics()`
2. **Historical data** retrieved from `dashboard_metrics_history` table
3. **Bokeh charts** updated with time-series data
4. **Export functionality** generates reports from aggregated data

#### Maintenance Operations Flow
1. **User triggers** maintenance action via dashboard button
2. **Dashboard Service** calls appropriate `CorrectionService` methods
3. **Operation status** tracked in `maintenance_logs` table
4. **UI feedback** provided via Panel notifications

## Database Schema Extensions

### New Tables

#### dashboard_metrics_history
```sql
CREATE TABLE dashboard_metrics_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metric_type VARCHAR(50) NOT NULL,  -- 'health', 'performance', 'learning'
    metric_name VARCHAR(100) NOT NULL,
    metric_value REAL,
    metric_unit VARCHAR(20),
    additional_data TEXT,  -- JSON for complex metrics
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_metrics_history_timestamp ON dashboard_metrics_history(timestamp DESC);
CREATE INDEX idx_metrics_history_type_name ON dashboard_metrics_history(metric_type, metric_name);
```

#### alert_configurations
```sql
CREATE TABLE alert_configurations (
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

CREATE UNIQUE INDEX idx_alert_config_metric_type ON alert_configurations(metric_name, threshold_type);
```

#### dashboard_preferences
```sql
CREATE TABLE dashboard_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) DEFAULT 'default',
    preference_key VARCHAR(100) NOT NULL,
    preference_value TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_dashboard_prefs_user_key ON dashboard_preferences(user_id, preference_key);
```

#### maintenance_logs
```sql
CREATE TABLE maintenance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type VARCHAR(50) NOT NULL,  -- 'cache_cleanup', 'db_optimize', etc.
    operation_status VARCHAR(20) NOT NULL,  -- 'started', 'completed', 'failed'
    operation_details TEXT,  -- JSON with operation specifics
    duration_ms INTEGER,
    initiated_by VARCHAR(100) DEFAULT 'dashboard',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE INDEX idx_maintenance_logs_timestamp ON maintenance_logs(started_at DESC);
CREATE INDEX idx_maintenance_logs_type ON maintenance_logs(operation_type);
```

### Schema Migration Strategy

#### Migration Script
```python
def apply_dashboard_migrations(db_path: str):
    """Apply dashboard-specific database migrations."""
    migrations = [
        {
            'version': '1.0.0',
            'description': 'Create dashboard metrics history table',
            'sql': '''
                CREATE TABLE IF NOT EXISTS dashboard_metrics_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metric_type VARCHAR(50) NOT NULL,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value REAL,
                    metric_unit VARCHAR(20),
                    additional_data TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_metrics_history_timestamp 
                ON dashboard_metrics_history(timestamp DESC);
            '''
        },
        # Additional migrations...
    ]
    
    with sqlite3.connect(db_path) as conn:
        for migration in migrations:
            try:
                conn.executescript(migration['sql'])
                logger.info(f"Applied migration: {migration['description']}")
            except Exception as e:
                logger.error(f"Migration failed: {e}")
                raise
```

## API Design and Endpoints

### Dashboard Service API

#### Core Service Class
```python
class DashboardService:
    """Main service for dashboard operations."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_FILE
        self.monitor = LearningSystemMonitor(db_path)
        self.correction_service = CorrectionService(db_path)
        
    async def get_health_status(self) -> Dict[str, Any]:
        """Get current system health status."""
        
    async def get_performance_metrics(self, time_range: str) -> Dict[str, Any]:
        """Get performance metrics for specified time range."""
        
    async def get_learning_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get learning system analytics."""
        
    async def execute_maintenance_task(self, task_type: str) -> Dict[str, Any]:
        """Execute maintenance task and return status."""
        
    async def configure_alert(self, alert_config: Dict[str, Any]) -> bool:
        """Configure alert threshold and notification."""
        
    async def export_report(self, report_type: str, format: str) -> bytes:
        """Generate and export report in specified format."""
```

#### Key Methods

##### Health Status API
```python
async def get_health_status(self) -> Dict[str, Any]:
    """Get comprehensive health status with real-time metrics."""
    health = self.monitor.get_system_health()
    
    # Add real-time metrics
    current_metrics = await self._get_current_metrics()
    
    return {
        'overall_status': health.overall_status,
        'components': {
            'database': {
                'status': 'connected' if health.database_connected else 'disconnected',
                'response_time_ms': current_metrics.get('db_response_time', 0)
            },
            'pattern_learning': {
                'status': 'active' if health.pattern_learning_active else 'inactive',
                'active_patterns': current_metrics.get('active_patterns', 0)
            },
            'cache': {
                'performance': health.cache_performance,
                'hit_rate': current_metrics.get('cache_hit_rate', 0)
            }
        },
        'metrics': {
            'error_rate': health.recent_error_rate,
            'response_time_ms': current_metrics.get('avg_response_time', 0),
            'uptime_hours': current_metrics.get('uptime_hours', 0)
        },
        'recommendations': health.recommendations,
        'last_updated': datetime.now().isoformat()
    }
```

##### Performance Metrics API
```python
async def get_performance_metrics(self, time_range: str = '24h') -> Dict[str, Any]:
    """Get performance metrics with historical trends."""
    
    # Parse time range
    hours = self._parse_time_range(time_range)
    
    # Get historical data
    historical_data = await self._get_historical_metrics(hours)
    
    # Get current benchmarks
    current_performance = self.monitor.get_comprehensive_metrics()
    
    return {
        'current': {
            'response_time_ms': current_performance.performance_metrics.get('average_response_time_ms', 0),
            'pattern_lookup_ms': current_performance.performance_metrics.get('pattern_lookup_ms', 0),
            'cache_hit_rate': current_performance.performance_metrics.get('cache_hit_rate', 0)
        },
        'trends': {
            'response_time': historical_data.get('response_time_trend', []),
            'error_rate': historical_data.get('error_rate_trend', []),
            'cache_performance': historical_data.get('cache_performance_trend', [])
        },
        'benchmarks': await self._run_performance_benchmark(),
        'time_range': time_range,
        'last_updated': datetime.now().isoformat()
    }
```

### Real-time Update Mechanism

#### Polling Strategy
```python
class DashboardUpdater:
    """Handles real-time dashboard updates."""
    
    def __init__(self, dashboard_service: DashboardService):
        self.service = dashboard_service
        self.update_interval = 30  # seconds
        self.is_running = False
        
    async def start_updates(self):
        """Start periodic dashboard updates."""
        self.is_running = True
        while self.is_running:
            try:
                # Update health status
                health_data = await self.service.get_health_status()
                self._update_health_widgets(health_data)
                
                # Update performance metrics
                perf_data = await self.service.get_performance_metrics('1h')
                self._update_performance_charts(perf_data)
                
                # Check for alerts
                await self._check_and_trigger_alerts(health_data)
                
            except Exception as e:
                logger.error(f"Dashboard update failed: {e}")
                
            await asyncio.sleep(self.update_interval)
```

## Security and Authentication Considerations

### Authentication Integration
- **Leverage Existing Auth**: Integrate with current Panel application authentication
- **Role-based Access**: Admin-only access to dashboard functionality
- **Session Management**: Maintain secure session state for dashboard users

### Data Security
- **Local Data Only**: All monitoring data remains on local system
- **Encrypted Storage**: Sensitive configuration data encrypted at rest
- **Audit Logging**: Track all administrative actions and configuration changes

### Access Control
```python
class DashboardAuth:
    """Authentication and authorization for dashboard access."""
    
    def __init__(self):
        self.admin_roles = ['admin', 'system_admin', 'healthcare_admin']
        
    def check_dashboard_access(self, user_role: str) -> bool:
        """Check if user has dashboard access."""
        return user_role in self.admin_roles
        
    def check_maintenance_access(self, user_role: str) -> bool:
        """Check if user can perform maintenance tasks."""
        return user_role in ['admin', 'system_admin']
        
    def log_admin_action(self, user_id: str, action: str, details: Dict):
        """Log administrative actions for audit trail."""
        # Implementation for audit logging
```

## Performance and Scalability Planning

### Performance Optimization

#### Database Query Optimization
- **Efficient Indexes**: Optimized indexes for dashboard queries
- **Query Caching**: Cache frequently accessed metrics data
- **Batch Operations**: Batch database operations for better performance
- **Connection Pooling**: Efficient database connection management

#### Frontend Performance
- **Lazy Loading**: Load dashboard components on demand
- **Data Pagination**: Paginate large datasets for better responsiveness
- **Chart Optimization**: Efficient Bokeh chart rendering with data sampling
- **Caching Strategy**: Client-side caching of static dashboard data

#### Memory Management
```python
class DashboardCache:
    """Efficient caching for dashboard data."""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_times = {}
        
    def get_cached_metrics(self, key: str, max_age_seconds: int = 300) -> Optional[Dict]:
        """Get cached metrics if still valid."""
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if (datetime.now() - timestamp).seconds < max_age_seconds:
                self.access_times[key] = datetime.now()
                return cached_data
        return None
        
    def cache_metrics(self, key: str, data: Dict):
        """Cache metrics data with LRU eviction."""
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        self.cache[key] = (data, datetime.now())
        self.access_times[key] = datetime.now()
```

### Scalability Considerations

#### Data Growth Management
- **Automated Cleanup**: Scheduled cleanup of old metrics data
- **Data Archiving**: Archive historical data to separate storage
- **Retention Policies**: Configurable data retention periods
- **Storage Monitoring**: Track database size and growth trends

#### Future Enhancement Support
- **Modular Architecture**: Easy addition of new dashboard components
- **Plugin System**: Support for custom monitoring modules
- **API Extensibility**: RESTful API for external integrations
- **Configuration Management**: Flexible configuration system

## Error Handling and Resilience

### Error Handling Strategy
```python
class DashboardErrorHandler:
    """Centralized error handling for dashboard operations."""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.last_errors = {}
        
    async def handle_service_error(self, operation: str, error: Exception) -> Dict[str, Any]:
        """Handle service errors with appropriate fallbacks."""
        self.error_counts[operation] += 1
        self.last_errors[operation] = {
            'error': str(error),
            'timestamp': datetime.now().isoformat(),
            'count': self.error_counts[operation]
        }
        
        # Provide fallback data
        if operation == 'health_check':
            return self._get_fallback_health_status()
        elif operation == 'performance_metrics':
            return self._get_fallback_performance_data()
            
        return {'error': str(error), 'fallback_data': True}
```

### Resilience Features
- **Graceful Degradation**: Dashboard continues functioning with limited data
- **Automatic Recovery**: Retry failed operations with exponential backoff
- **Fallback Data**: Provide cached or default data when services unavailable
- **Error Notifications**: Alert users to system issues without breaking UI

## Deployment and Maintenance

### Deployment Strategy
1. **Database Migration**: Apply new schema changes
2. **Code Deployment**: Deploy dashboard components to existing Panel app
3. **Configuration Setup**: Initialize default dashboard settings
4. **User Training**: Provide training materials and documentation
5. **Gradual Rollout**: Phase deployment to minimize disruption

### Maintenance Procedures
- **Regular Updates**: Scheduled updates to dashboard components
- **Performance Monitoring**: Monitor dashboard performance and optimize
- **Data Cleanup**: Automated cleanup of old metrics and logs
- **Security Updates**: Regular security patches and updates
- **Backup Procedures**: Regular backup of dashboard configuration and data

## Conclusion

The technical architecture for the Admin Monitoring Dashboard leverages existing AAA system infrastructure while adding minimal complexity. The modular design ensures easy maintenance and future enhancement while providing robust monitoring capabilities through an intuitive web interface.

The architecture prioritizes performance, security, and scalability while maintaining compatibility with the existing Panel application framework. This approach minimizes development risk while maximizing the value delivered to healthcare administrators. 