CREATE TABLE IF NOT EXISTS assistant_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    metric_details TEXT,
    period_start TEXT,
    period_end TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(metric_type, metric_name, period_start, period_end)
);

-- Index to quickly filter by metric type and time period
CREATE INDEX IF NOT EXISTS idx_assistant_metrics_type_period
    ON assistant_metrics(metric_type, period_end);

-- Comment: This table is part of the WS-6 Assistant Evaluation Framework
-- It stores time-series metrics data about assistant performance across
-- several dimensions (satisfaction, response time, intent accuracy, etc.) 