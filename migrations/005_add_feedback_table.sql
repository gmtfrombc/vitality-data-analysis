-- WS-6-A: Add assistant feedback table
-- Part of Continuous Feedback & Evaluation work stream
-- Stores user feedback about assistant answers

CREATE TABLE IF NOT EXISTS assistant_feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT    DEFAULT 'anon',
    question    TEXT    NOT NULL,
    rating      TEXT    CHECK(rating IN ('up','down')) NOT NULL,
    comment     TEXT,
    created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON assistant_feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON assistant_feedback(rating); 