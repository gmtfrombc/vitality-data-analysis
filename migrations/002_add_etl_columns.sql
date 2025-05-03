-- 002_add_etl_columns.sql
ALTER TABLE patients ADD COLUMN provider_id INTEGER;
ALTER TABLE patients ADD COLUMN health_coach_id INTEGER;
ALTER TABLE patients ADD COLUMN lesson_status TEXT;
ALTER TABLE patients ADD COLUMN lessons_completed INTEGER;
ALTER TABLE patients ADD COLUMN provider_visits INTEGER;
ALTER TABLE patients ADD COLUMN health_coach_visits INTEGER;
ALTER TABLE patients ADD COLUMN cancelled_visits INTEGER;
ALTER TABLE patients ADD COLUMN no_show_visits INTEGER;
ALTER TABLE patients ADD COLUMN rescheduled_visits INTEGER;
ALTER TABLE patients ADD COLUMN roles TEXT;

ALTER TABLE pmh ADD COLUMN code TEXT; 