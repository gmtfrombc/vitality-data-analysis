"""
Data Service Module

This module centralizes all database access and query logic for the application.
"""

import sqlite3
import logging
import pandas as pd


def get_db_path():
    """Get the database path from app.db_query module to ensure consistent source."""
    import app.db_query as db_query  # Local import to avoid circular dependency

    return db_query.get_db_path()


def ensure_rules_exist(db_path):
    """Make sure validation rules exist in the database."""
    from app.utils.rule_loader import initialize_validation_rules

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM validation_rules")
        count = cursor.fetchone()[0]
        if count == 0:
            logging.info(
                "No validation rules found in database. Initializing from default file."
            )
            conn.close()
            initialize_validation_rules(db_path)
        else:
            logging.info(f"Found {count} validation rules in database.")
            conn.close()
    except Exception as e:
        logging.error(f"Error checking for existing rules: {e}")
        raise


def load_summary_data(db_path):
    """Load summary statistics for the dashboard."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get counts by status
        cursor.execute(
            "SELECT status, COUNT(*) FROM validation_results GROUP BY status"
        )
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        total_issues = sum(status_counts.values())

        # Get counts by severity
        cursor.execute(
            """
            SELECT vru.severity, COUNT(*) 
            FROM validation_results vr
            JOIN validation_rules vru ON vr.rule_id = vru.rule_id
            GROUP BY vru.severity
            """
        )
        severity_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Get counts by rule type
        cursor.execute(
            """
            SELECT vru.rule_type, COUNT(*) 
            FROM validation_results vr
            JOIN validation_rules vru ON vr.rule_id = vru.rule_id
            GROUP BY vru.rule_type
            """
        )
        rule_type_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Get patient count
        cursor.execute("SELECT COUNT(DISTINCT patient_id) FROM validation_results")
        patient_count = cursor.fetchone()[0]

        conn.close()
        return (
            status_counts,
            severity_counts,
            rule_type_counts,
            total_issues,
            patient_count,
        )
    except Exception as e:
        logging.error(f"Error loading summary data: {e}")
        return {}, {}, {}, 0, 0


def load_quality_metrics(db_path):
    """Load aggregated issue counts by field and over time (daily)."""
    try:
        conn = sqlite3.connect(db_path)
        query = """
            SELECT vr.field_name            AS field,
                   date(vr.detected_at)     AS dt,
                   vru.severity             AS severity,
                   COUNT(*)                 AS n
            FROM validation_results vr
            JOIN validation_rules vru ON vr.rule_id = vru.rule_id
            WHERE vr.field_name IS NOT NULL
            GROUP BY field, dt, severity
            """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # Pivot for field summary (rows = field, cols = severity)
        field_summary = df.groupby(["field", "severity"], as_index=False)["n"].sum()
        quality_field_df = (
            field_summary.pivot(index="field", columns="severity", values="n")
            .fillna(0)
            .reset_index()
        )

        # Daily summary (rows = date, cols = severity)
        date_summary = df.groupby(["dt", "severity"], as_index=False)["n"].sum()
        quality_date_df = (
            date_summary.pivot(index="dt", columns="severity", values="n")
            .fillna(0)
            .reset_index()
        )
        return quality_field_df, quality_date_df
    except Exception as exc:
        logging.error("Error loading quality metrics: %s", exc)
        return pd.DataFrame(), pd.DataFrame()


def load_patient_list(
    db_path, filter_status_value, filter_severity_value, filter_type_value
):
    """Load list of patients with validation issues, filtered by status, severity, and type."""
    try:
        conn = sqlite3.connect(db_path)
        query = """
            SELECT vr.patient_id, p.first_name, p.last_name, 
                   COUNT(DISTINCT vr.rule_id) as issue_count,
                   COUNT(DISTINCT CASE WHEN vr.status = 'open' THEN vr.rule_id END) as open_count,
                   MAX(CASE WHEN vru.severity = 'error' THEN 1 ELSE 0 END) as has_errors
            FROM validation_results vr
            JOIN patients p ON vr.patient_id = p.id
            JOIN validation_rules vru ON vr.rule_id = vru.rule_id
            WHERE 1=1
        """
        params = []
        if filter_status_value != "all":
            query += " AND vr.status = ?"
            params.append(filter_status_value)
        if filter_severity_value != "all":
            query += " AND vru.severity = ?"
            params.append(filter_severity_value)
        if filter_type_value != "all":
            query += " AND vru.rule_type = ?"
            params.append(filter_type_value)
        query += """
            GROUP BY vr.patient_id, p.first_name, p.last_name
            ORDER BY open_count DESC, has_errors DESC, issue_count DESC
        """
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        logging.error(f"Error loading patient list: {e}")
        return pd.DataFrame(
            columns=[
                "patient_id",
                "first_name",
                "last_name",
                "issue_count",
                "open_count",
                "has_errors",
            ]
        )


def submit_correction_db(db_path, result_id, correction_value, correction_reason):
    """Submit a correction for an issue."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Get information about the issue
        cursor.execute(
            """
            SELECT vr.patient_id, vr.field_name, vr.rule_id
            FROM validation_results vr
            WHERE vr.result_id = ?
            """,
            (result_id,),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        patient_id, field_name, rule_id = row
        # Insert correction
        cursor.execute(
            """
            INSERT INTO data_corrections 
            (result_id, patient_id, field_name, table_name, record_id, new_value, applied_by)
            VALUES (?, ?, ?, 'vitals', 0, ?, 'current_user')
            """,
            (result_id, patient_id, field_name, correction_value),
        )
        correction_id = cursor.lastrowid
        # Add audit record
        cursor.execute(
            """
            INSERT INTO correction_audit 
            (correction_id, result_id, action_type, action_reason, action_by)
            VALUES (?, ?, 'correction', ?, 'current_user')
            """,
            (correction_id, result_id, correction_reason),
        )
        # Update issue status
        cursor.execute(
            """
            UPDATE validation_results
            SET status = 'corrected'
            WHERE result_id = ?
            """,
            (result_id,),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error submitting correction: {e}")
        return False


def mark_as_reviewed_db(db_path, result_id, reason):
    """Mark an issue as reviewed."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Add audit record
        cursor.execute(
            """
            INSERT INTO correction_audit 
            (result_id, action_type, action_reason, action_by)
            VALUES (?, 'review', ?, 'current_user')
            """,
            (result_id, reason),
        )
        # Update issue status
        cursor.execute(
            """
            UPDATE validation_results
            SET status = 'reviewed'
            WHERE result_id = ?
            """,
            (result_id,),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error marking as reviewed: {e}")
        return False


def validate_patient_db_ops(db_path, patient_id=None):
    """Delete previous validation results for a patient or all patients."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        if patient_id:
            cursor.execute(
                "DELETE FROM validation_results WHERE patient_id = ?", (patient_id,)
            )
            logging.info(
                f"Cleared previous validation results for patient {patient_id}"
            )
        else:
            cursor.execute("DELETE FROM validation_results")
            logging.info("Cleared all previous validation results")
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error purging validation results: {e}")


def compute_record_quality_db(db_path, patient_id):
    """Compute blocking-rule pass-rate and return (ratio, colour_key)."""
    try:
        conn = sqlite3.connect(db_path)
        # Total active blocking rules (severity == 'error')
        total_blocking = conn.execute(
            "SELECT COUNT(*) FROM validation_rules WHERE severity = 'error' AND is_active = 1"
        ).fetchone()[0]
        # Distinct blocking rules that currently have *open* issues for this patient
        failing = conn.execute(
            """
            SELECT COUNT(DISTINCT vr.rule_id)
            FROM validation_results vr
            JOIN validation_rules vru ON vr.rule_id = vru.rule_id
            WHERE vr.patient_id = ? AND vru.severity = 'error' AND vr.status IN ('open', 'reviewed')
            """,
            (str(patient_id),),
        ).fetchone()[0]
        conn.close()
        if total_blocking == 0:
            return 1.0, "success"
        passed = max(total_blocking - failing, 0)
        ratio = passed / total_blocking
        if ratio >= 0.95:
            colour = "success"  # green
        elif ratio >= 0.80:
            colour = "warning"  # amber
        else:
            colour = "danger"  # red
        return ratio, colour
    except Exception as exc:
        logging.error("Error computing record quality: %s", exc)
        return 0.0, "danger"


def mark_patient_as_verified_db(db_path, patient_id, reason):
    """Mark all validation_results for patient_id as verified."""
    try:
        if not patient_id:
            return {"success": False, "message": "No patient_id provided"}
        logging.info(f"Marking patient {patient_id} as verified")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Get *all* result_ids for this patient (independent of current status)
        cursor.execute(
            "SELECT result_id FROM validation_results WHERE patient_id = ?",
            (patient_id,),
        )
        result_ids = [row[0] for row in cursor.fetchall()]
        if not result_ids:
            conn.close()
            return {
                "success": False,
                "message": "No validation results found for this patient",
            }
        # Audit table entries (one per result)
        audit_rows = [(rid, "verify", reason, "current_user") for rid in result_ids]
        cursor.executemany(
            """
            INSERT INTO correction_audit (result_id, action_type, action_reason, action_by)
            VALUES (?, ?, ?, ?)
            """,
            audit_rows,
        )
        # Update all results to status = 'verified'
        cursor.execute(
            "UPDATE validation_results SET status = 'verified' WHERE patient_id = ?",
            (patient_id,),
        )
        conn.commit()
        conn.close()
        return {
            "success": True,
            "message": f"Patient {patient_id} verified (\u2713 {len(result_ids)} issues).",
        }
    except Exception as exc:
        logging.error("Error marking patient as verified: %s", exc)
        return {"success": False, "message": "Failed to verify patient – check logs"}
