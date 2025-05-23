-- Migration 009: Correction Learning System Tables
-- Extends the feedback system to capture and learn from corrections

-- Extended correction sessions for detailed tracking
CREATE TABLE IF NOT EXISTS correction_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER,
    original_query TEXT NOT NULL,
    original_intent_json TEXT,
    original_code TEXT,
    original_results TEXT,
    human_correct_answer TEXT,
    correction_type TEXT CHECK(correction_type IN ('intent_fix', 'code_fix', 'logic_fix', 'data_fix')),
    error_category TEXT, -- 'ambiguous_intent', 'wrong_aggregation', 'missing_filter', etc.
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'integrated', 'validated', 'rejected')),
    reviewed_by TEXT,
    reviewed_at TEXT,
    FOREIGN KEY (feedback_id) REFERENCES assistant_feedback(id)
);

-- Intent patterns learned from corrections
CREATE TABLE IF NOT EXISTS intent_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_pattern TEXT NOT NULL,
    canonical_intent_json TEXT NOT NULL,
    confidence_boost REAL DEFAULT 0.1,
    usage_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 1.0,
    created_from_session_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_used_at TEXT,
    FOREIGN KEY (created_from_session_id) REFERENCES correction_sessions(id)
);

-- Code templates for deterministic generation
CREATE TABLE IF NOT EXISTS code_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_signature TEXT NOT NULL, -- JSON schema pattern for intent matching
    template_code TEXT NOT NULL,
    template_description TEXT,
    success_rate REAL DEFAULT 1.0,
    usage_count INTEGER DEFAULT 0,
    created_from_session_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_used_at TEXT,
    FOREIGN KEY (created_from_session_id) REFERENCES correction_sessions(id)
);

-- Query similarity cache for faster pattern matching
CREATE TABLE IF NOT EXISTS query_similarity_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT NOT NULL UNIQUE, -- Hash of normalized query
    similar_patterns TEXT, -- JSON array of similar pattern IDs
    computed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Performance metrics for learning system
CREATE TABLE IF NOT EXISTS learning_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_date DATE NOT NULL,
    total_queries INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    pattern_matches INTEGER DEFAULT 0,
    template_matches INTEGER DEFAULT 0,
    correction_applied INTEGER DEFAULT 0,
    accuracy_rate REAL DEFAULT 0.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_correction_sessions_feedback_id ON correction_sessions(feedback_id);
CREATE INDEX IF NOT EXISTS idx_correction_sessions_status ON correction_sessions(status);
CREATE INDEX IF NOT EXISTS idx_intent_patterns_usage_count ON intent_patterns(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_code_templates_usage_count ON code_templates(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_query_similarity_cache_hash ON query_similarity_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_learning_metrics_date ON learning_metrics(metric_date DESC); 