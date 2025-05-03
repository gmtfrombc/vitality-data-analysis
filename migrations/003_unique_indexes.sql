-- 003_unique_indexes.sql
-- Add unique constraints required for idempotent ETL upserts

CREATE UNIQUE INDEX IF NOT EXISTS uq_vitals_patient_date
    ON vitals(patient_id, date);

CREATE UNIQUE INDEX IF NOT EXISTS uq_scores_patient_date_type
    ON scores(patient_id, date, score_type);

CREATE UNIQUE INDEX IF NOT EXISTS uq_mh_patient_date_type
    ON mental_health(patient_id, date, assessment_type);

CREATE UNIQUE INDEX IF NOT EXISTS uq_lab_patient_date_test
    ON lab_results(patient_id, date, test_name); 