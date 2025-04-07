-- Add new columns to patients table
ALTER TABLE patients ADD COLUMN program_end_date TEXT;
ALTER TABLE patients ADD COLUMN active INTEGER DEFAULT 0;
ALTER TABLE patients ADD COLUMN etoh INTEGER DEFAULT 0;
ALTER TABLE patients ADD COLUMN tobacco INTEGER DEFAULT 0;
ALTER TABLE patients ADD COLUMN glp1_full INTEGER DEFAULT 0;

-- Create new patient_visit_metrics table
CREATE TABLE patient_visit_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    provider_visits INTEGER DEFAULT 0,
    health_coach_visits INTEGER DEFAULT 0,
    cancelled_visits INTEGER DEFAULT 0,
    no_show_visits INTEGER DEFAULT 0,
    rescheduled_visits INTEGER DEFAULT 0,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- Create index for faster lookups
CREATE INDEX idx_patient_visit_metrics_patient_id ON patient_visit_metrics(patient_id); 