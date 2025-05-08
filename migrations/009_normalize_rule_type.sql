-- Migration 009: Normalise rule_type values and add CHECK constraint
-- Run this after deploying categorical/not-null rule support.

-- 1) Canonicalise existing rule_type strings
UPDATE validation_rules
SET rule_type = CASE
    WHEN rule_type IN ('missing', 'missing_data_check', 'missing_data_rule') THEN 'missing_data'
    WHEN rule_type IN ('range', 'range_test', 'range_rule') THEN 'range_check'
    WHEN rule_type IN ('consistency', 'consistency_test') THEN 'consistency_check'
    WHEN rule_type IN ('categorical', 'categorical_test') THEN 'categorical_check'
    WHEN rule_type IN ('notnull', 'not_null_check') THEN 'not_null'
    ELSE rule_type
END;

-- 2) Add CHECK constraint to enforce canonical set
-- NOTE: SQLite allows adding a new column with constraint. We create a temp table, copy, drop, and rename.

PRAGMA foreign_keys = off;

CREATE TABLE IF NOT EXISTS validation_rules_new (
    rule_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN (
        'missing_data',
        'range_check',
        'consistency_check',
        'categorical_check',
        'not_null',
        'conditional_not_null'
    )),
    validation_logic TEXT NOT NULL,
    parameters TEXT NOT NULL,
    severity TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    is_active INTEGER
);

INSERT INTO validation_rules_new
SELECT * FROM validation_rules;

DROP TABLE validation_rules;
ALTER TABLE validation_rules_new RENAME TO validation_rules;

PRAGMA foreign_keys = on; 