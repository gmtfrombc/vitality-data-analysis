-- Migration 010: Feedback Analytics Tables
-- Adds tables for tracking smart feedback system performance

CREATE TABLE IF NOT EXISTS feedback_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    priority_level TEXT NOT NULL,
    requested BOOLEAN NOT NULL,
    user_id TEXT DEFAULT 'anon',
    confidence_score REAL,
    novelty_score REAL,
    learning_value_score REAL,
    fatigue_detected BOOLEAN DEFAULT FALSE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_requests_created_at 
ON feedback_requests(created_at);

CREATE INDEX IF NOT EXISTS idx_feedback_requests_priority 
ON feedback_requests(priority_level);

CREATE INDEX IF NOT EXISTS idx_feedback_requests_user_id 
ON feedback_requests(user_id); 