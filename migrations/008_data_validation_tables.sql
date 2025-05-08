-- Migration 008: Add Data Validation Tables
-- This migration adds tables for the data validation and correction system

-- Table to store validation rules
CREATE TABLE IF NOT EXISTS validation_rules (
    rule_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    rule_type TEXT NOT NULL, -- 'missing_data', 'range_check', 'consistency_check'
    validation_logic TEXT NOT NULL,
    parameters TEXT NOT NULL, -- JSON string containing rule parameters
    severity TEXT NOT NULL, -- 'info', 'warning', 'error'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- Table to store validation results (issues found)
CREATE TABLE IF NOT EXISTS validation_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    field_name TEXT,
    issue_description TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'open', -- 'open', 'reviewed', 'corrected', 'ignored'
    FOREIGN KEY (rule_id) REFERENCES validation_rules(rule_id)
);

-- Table to store data corrections made
CREATE TABLE IF NOT EXISTS data_corrections (
    correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER,
    patient_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL, -- ID of the record being corrected
    original_value TEXT,
    new_value TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by TEXT, -- User who made the correction
    FOREIGN KEY (result_id) REFERENCES validation_results(result_id)
);

-- Table for auditing the correction process
CREATE TABLE IF NOT EXISTS correction_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    correction_id INTEGER,
    result_id INTEGER,
    action_type TEXT NOT NULL, -- 'correction', 'review', 'ignore'
    action_reason TEXT,
    action_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_by TEXT, -- User who performed the action
    FOREIGN KEY (correction_id) REFERENCES data_corrections(correction_id),
    FOREIGN KEY (result_id) REFERENCES validation_results(result_id)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_validation_results_patient_id ON validation_results(patient_id);
CREATE INDEX IF NOT EXISTS idx_validation_results_status ON validation_results(status);
CREATE INDEX IF NOT EXISTS idx_data_corrections_patient_id ON data_corrections(patient_id); 