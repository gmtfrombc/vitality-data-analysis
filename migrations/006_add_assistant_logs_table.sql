CREATE TABLE IF NOT EXISTS assistant_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query            TEXT    NOT NULL,
    intent_json      TEXT,
    generated_code   TEXT,
    result_summary   TEXT,
    duration_ms      INTEGER,
    created_at       TEXT    DEFAULT CURRENT_TIMESTAMP
);

-- Index to quickly sort/filter by creation time
CREATE INDEX IF NOT EXISTS idx_assistant_logs_created_at
    ON assistant_logs(created_at); 