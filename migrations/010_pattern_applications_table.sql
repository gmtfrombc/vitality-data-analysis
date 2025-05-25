-- Migration 010: Pattern Applications Table
-- Adds table to track pattern usage and success rates for learning analytics

CREATE TABLE IF NOT EXISTS pattern_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    confidence_score REAL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    query_text TEXT,
    result_quality INTEGER, -- 1-5 rating
    FOREIGN KEY (pattern_id) REFERENCES intent_patterns(id)
);

-- Add user_feedback table for feedback analytics
CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_type TEXT NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT,
    pattern_id TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pattern_applications_pattern_id ON pattern_applications(pattern_id);
CREATE INDEX IF NOT EXISTS idx_pattern_applications_applied_at ON pattern_applications(applied_at DESC);
CREATE INDEX IF NOT EXISTS idx_pattern_applications_success ON pattern_applications(success);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_feedback_feedback_type ON user_feedback(feedback_type); 