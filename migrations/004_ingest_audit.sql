-- 004_ingest_audit.sql – create audit table for each JSON ingest

CREATE TABLE IF NOT EXISTS ingest_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    patients INTEGER DEFAULT 0,
    vitals INTEGER DEFAULT 0,
    scores INTEGER DEFAULT 0,
    mental_health INTEGER DEFAULT 0,
    lab_results INTEGER DEFAULT 0,
    pmh INTEGER DEFAULT 0
); 