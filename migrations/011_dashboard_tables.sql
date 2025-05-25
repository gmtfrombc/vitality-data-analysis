-- Dashboard tables migration for Admin Monitoring Dashboard
-- Sprint 1.1: Dashboard Foundation & Health Status

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