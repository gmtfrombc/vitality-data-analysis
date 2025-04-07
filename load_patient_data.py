import json
import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_patient_data(json_file="deidentified_patients.json", db_file="patient_data.db"):
    """
    Load patient data from JSON file into SQLite database with the new schema.
    For existing patients table: Updates only the new fields
    For patient_visit_metrics: Clears table and inserts fresh data

    Args:
        json_file (str): Path to the JSON file containing patient data
        db_file (str): Path to the SQLite database
    """
    try:
        # Read JSON data
        with open(json_file, 'r') as f:
            patients = json.load(f)

        logger.info(f"Loaded {len(patients)} records from {json_file}")

        # Connect to database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Start transaction
        cursor.execute("BEGIN TRANSACTION")

        try:
            # First, clear the patient_visit_metrics table
            cursor.execute("DELETE FROM patient_visit_metrics")
            logger.info("Cleared patient_visit_metrics table")

            # Update patients table with new fields
            patient_update_sql = """
                UPDATE patients 
                SET program_end_date = ?,
                    active = ?,
                    etoh = ?,
                    tobacco = ?,
                    glp1_full = ?
                WHERE id = ?
            """

            # Insert into patient_visit_metrics
            visit_metrics_sql = """
                INSERT INTO patient_visit_metrics (
                    patient_id,
                    provider_visits,
                    health_coach_visits,
                    cancelled_visits,
                    no_show_visits,
                    rescheduled_visits,
                    last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """

            patients_updated = 0
            metrics_inserted = 0

            for patient in patients:
                patient_id = patient.get('id')
                if not patient_id:
                    logger.warning(
                        f"Skipping record - no patient ID found: {patient}")
                    continue

                # Update patient record with new fields
                cursor.execute(patient_update_sql, (
                    patient.get('program_end_date'),
                    patient.get('active', 0),
                    patient.get('etoh', 0),
                    patient.get('tobacco', 0),
                    patient.get('glp1_full', 0),
                    patient_id
                ))
                if cursor.rowcount > 0:
                    patients_updated += 1

                # Insert visit metrics
                cursor.execute(visit_metrics_sql, (
                    patient_id,
                    patient.get('provider_visits', 0),
                    patient.get('health_coach_visits', 0),
                    patient.get('cancelled_visits', 0),
                    patient.get('no_show_visits', 0),
                    patient.get('rescheduled_visits', 0)
                ))
                metrics_inserted += 1

            # Commit transaction
            conn.commit()
            logger.info(
                f"Successfully updated {patients_updated} patient records with new fields")
            logger.info(
                f"Successfully inserted {metrics_inserted} visit metric records")

        except Exception as e:
            conn.rollback()
            logger.error(f"Error during data load, rolling back: {str(e)}")
            raise

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error loading patient data: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        load_patient_data()
        logger.info("Data loading completed successfully")
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        exit(1)
