-- 001_initial.sql
-- Baseline schema for Metabolic Health Program data warehouse

-- Patients
CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    birth_date TEXT,
    gender TEXT,
    ethnicity TEXT,
    engagement_score INTEGER,
    program_start_date TEXT,
    program_end_date TEXT,
    active INTEGER DEFAULT 0,
    etoh INTEGER DEFAULT 0,
    tobacco INTEGER DEFAULT 0,
    glp1_full INTEGER DEFAULT 0
);

-- Vitals
CREATE TABLE IF NOT EXISTS vitals (
    vital_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    date TEXT,
    weight REAL,
    height INTEGER,
    bmi REAL,
    sbp INTEGER,
    dbp INTEGER,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

-- Scores (PHQ, GAD, etc.)
CREATE TABLE IF NOT EXISTS scores (
    score_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    date TEXT,
    score_type TEXT,
    score_value INTEGER,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

-- Mental Health assessments
CREATE TABLE IF NOT EXISTS mental_health (
    mh_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    date TEXT,
    assessment_type TEXT,
    score INTEGER,
    risk_level TEXT,
    notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

-- Lab results
CREATE TABLE IF NOT EXISTS lab_results (
    lab_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    date TEXT,
    test_name TEXT,
    value REAL,
    unit TEXT,
    reference_range TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

-- Past Medical History (PMH)
CREATE TABLE IF NOT EXISTS pmh (
    pmh_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    condition TEXT,
    onset_date TEXT,
    status TEXT,
    notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

-- Patient visit metrics
CREATE TABLE IF NOT EXISTS patient_visit_metrics (
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
CREATE INDEX IF NOT EXISTS idx_patient_visit_metrics_patient_id ON patient_visit_metrics(patient_id);

-- Saved questions (already managed elsewhere, but include for completeness)
CREATE TABLE IF NOT EXISTS saved_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    query TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
); 