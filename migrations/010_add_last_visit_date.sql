-- 010_add_last_visit_date.sql
-- Add last_visit_date column to patient_visit_metrics for tracking most recent provider appointments

-- Add the column to store the date of the most recent provider visit
ALTER TABLE patient_visit_metrics ADD COLUMN last_visit_date TEXT;

-- Create index for faster querying by last_visit_date
CREATE INDEX idx_patient_visit_metrics_last_visit_date ON patient_visit_metrics(last_visit_date); 