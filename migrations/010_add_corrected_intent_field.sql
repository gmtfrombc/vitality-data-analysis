-- Migration 010: Add corrected_intent_json field to correction_sessions table
-- This field is needed for Sprint 4 pattern learning functionality

ALTER TABLE correction_sessions ADD COLUMN corrected_intent_json TEXT;

-- Create index for faster queries on this field
CREATE INDEX IF NOT EXISTS idx_correction_sessions_corrected_intent ON correction_sessions(corrected_intent_json); 