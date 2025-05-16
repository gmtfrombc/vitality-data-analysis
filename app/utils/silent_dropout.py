"""Silent Dropout Detection Utility

This module identifies patients who are still marked as active but haven't had
a provider visit in the last 90 days. These are potentially "silent dropouts" -
patients who have effectively stopped participating in the program but haven't
been officially marked as inactive.

Usage:
    from app.utils.silent_dropout import get_silent_dropout_report
    df = get_silent_dropout_report(threshold_days=90)
"""

from __future__ import annotations
from typing import Optional
import logging
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

from db_query import query_dataframe, get_db_path
from app.utils.date_helpers import format_date_for_display

logger = logging.getLogger(__name__)


def _check_column_exists(db_path: str, table: str, column: str) -> bool:
    """Check if a column exists in a table.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database
    table : str
        Table name to check
    column : str
        Column name to check

    Returns
    -------
    bool
        True if the column exists, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Query the pragma table for column info
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns
    except sqlite3.Error as e:
        logger.error(f"Error checking column existence: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_silent_dropout_report(
    threshold_days: int = 90,
    active_only: bool = True,
    db_path: Optional[str] = None,
) -> pd.DataFrame:
    """Identify active patients who haven't had a provider visit in over [threshold_days].

    Parameters
    ----------
    threshold_days : int, default 90
        Number of days without a visit to consider a patient a silent dropout
    active_only : bool, default True
        Whether to only include patients marked as active
    db_path : str, optional
        Path to SQLite database. Defaults to the active path resolved by db_query.

    Returns
    -------
    pandas.DataFrame
        Columns: patient_id, first_name, last_name, provider_visits,
                 last_visit_date, days_since_visit
    """
    # Calculate the cutoff date (today - threshold_days)
    cutoff_date = (datetime.now() - timedelta(days=threshold_days)).strftime("%Y-%m-%d")

    # Use default db_path if not provided
    if db_path is None:
        db_path = get_db_path()

    # Check if last_visit_date column exists
    has_last_visit_date = _check_column_exists(
        db_path, "patient_visit_metrics", "last_visit_date"
    )

    if not has_last_visit_date:
        logger.warning(
            "The last_visit_date column doesn't exist yet. "
            "Please apply migrations first by running 'python apply_migrations.py'"
        )

        # Simplified query without the last_visit_date column
        sql = """
        WITH 
        patient_basics AS (
            SELECT 
                p.id as patient_id,
                p.first_name,
                p.last_name,
                p.program_start_date,
                p.active
            FROM patients p
            WHERE 1=1
            {active_filter}
        )
        SELECT 
            pb.patient_id,
            pb.first_name,
            pb.last_name,
            pvm.provider_visits,
            NULL as last_visit_date,
            NULL as days_since_visit
        FROM patient_basics pb
        LEFT JOIN patient_visit_metrics pvm ON pb.patient_id = pvm.patient_id
        ORDER BY pvm.provider_visits DESC NULLS LAST
        """
    else:
        # Full query with last_visit_date column
        sql = """
        WITH 
        patient_basics AS (
            SELECT 
                p.id as patient_id,
                p.first_name,
                p.last_name,
                p.program_start_date,
                p.active
            FROM patients p
            WHERE 1=1
            {active_filter}
        )
        SELECT 
            pb.patient_id,
            pb.first_name,
            pb.last_name,
            pvm.provider_visits,
            pvm.last_visit_date,
            julianday('now') - julianday(pvm.last_visit_date) AS days_since_visit
        FROM patient_basics pb
        LEFT JOIN patient_visit_metrics pvm ON pb.patient_id = pvm.patient_id
        WHERE 
            (pvm.last_visit_date IS NULL OR pvm.last_visit_date < ?)
            OR pvm.last_visit_date IS NULL
        ORDER BY days_since_visit DESC NULLS FIRST
        """

    # Apply active filter if requested
    active_clause = " AND p.active = 1" if active_only else ""
    sql = sql.replace("{active_filter}", active_clause)

    logger.debug(
        "Executing silent dropout SQL with threshold of %d days", threshold_days
    )

    # Execute query with appropriate parameters
    # Make sure params is always passed, even for the simplified query
    df = query_dataframe(sql, params=(cutoff_date,), db_path=db_path)

    # Format dates for display if needed
    if not df.empty and "last_visit_date" in df.columns and has_last_visit_date:
        df["last_visit_date"] = df["last_visit_date"].apply(
            lambda d: (
                format_date_for_display(d, format_str="%b %d, %Y")
                if pd.notna(d)
                else "Never"
            )
        )

    # Replace NaN values in days_since_visit with a large number to sort properly
    if not df.empty and "days_since_visit" in df.columns and has_last_visit_date:
        # Use the recommended approach to avoid the FutureWarning
        df["days_since_visit"] = (
            df["days_since_visit"].fillna(float("inf")).infer_objects(copy=False)
        )
        # Round days to integers for cleaner display
        df["days_since_visit"] = df["days_since_visit"].apply(
            lambda x: int(x) if x != float("inf") else None
        )

    return df


def update_last_visit_date_for_patients(db_path: Optional[str] = None) -> int:
    """Update the last_visit_date field for all patients based on available data.

    This function should be called before first use of the report to ensure the
    last_visit_date field is populated. In a real system, this would be updated
    whenever a patient attends an appointment.

    Parameters
    ----------
    db_path : str, optional
        Path to SQLite database

    Returns
    -------
    int
        Number of records updated
    """
    if db_path is None:
        db_path = get_db_path()

    # Check if last_visit_date column exists
    if not _check_column_exists(db_path, "patient_visit_metrics", "last_visit_date"):
        logger.warning(
            "Cannot update last_visit_date because the column doesn't exist. "
            "Please apply migrations first by running 'python apply_migrations.py'"
        )
        return 0

    # For demonstration purposes, this generates simulated last visit dates
    # In a real system, this would pull from an appointments table
    sql = """
    UPDATE patient_visit_metrics
    SET last_visit_date = date(
        datetime('now', 
                 '-' || abs(random() % (provider_visits * 30)) || ' days')
    )
    WHERE provider_visits > 0
      AND last_visit_date IS NULL
    """

    # Execute the update directly with sqlite3
    conn = None
    rows_updated = 0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows_updated = cursor.rowcount
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

    return rows_updated


def mark_patient_as_inactive(patient_id: str, db_path: Optional[str] = None) -> bool:
    """Mark a patient as inactive in the database.

    Parameters
    ----------
    patient_id : str
        ID of the patient to mark as inactive
    db_path : str, optional
        Path to SQLite database

    Returns
    -------
    bool
        True if the update was successful, False otherwise
    """
    if db_path is None:
        db_path = get_db_path()

    sql = """
    UPDATE patients
    SET active = 0
    WHERE id = ?
    """

    # Execute the update directly with sqlite3
    conn = None
    success = False
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql, (patient_id,))
        success = cursor.rowcount > 0
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

    return success


def ensure_last_visit_date_column(db_path: Optional[str] = None) -> bool:
    """Ensure the last_visit_date column exists in patient_visit_metrics table.

    This function can be called before using the silent dropout features to make
    sure the necessary database schema is in place.

    Parameters
    ----------
    db_path : str, optional
        Path to SQLite database

    Returns
    -------
    bool
        True if the column exists or was successfully added, False otherwise
    """
    if db_path is None:
        db_path = get_db_path()

    # Check if column already exists
    if _check_column_exists(db_path, "patient_visit_metrics", "last_visit_date"):
        return True

    # Column doesn't exist, try to add it
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Add the column
        cursor.execute(
            "ALTER TABLE patient_visit_metrics ADD COLUMN last_visit_date TEXT"
        )

        # Create index for faster queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_patient_visit_metrics_last_visit_date ON patient_visit_metrics(last_visit_date)"
        )

        conn.commit()
        logger.info("Added last_visit_date column to patient_visit_metrics table")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error adding last_visit_date column: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def get_clinical_inactivity_report(
    inactivity_days: int = 90,
    minimum_activity_count: int = 2,
    active_only: bool = True,
    db_path: Optional[str] = None,
) -> pd.DataFrame:
    """Identify potentially inactive patients based on clinical data points.

    This approach looks at when patients last had lab tests, mental health screenings,
    or vital measurements recorded. A true "silent dropout" is identified as someone who:
    1. Has been active in the program (has some clinical data)
    2. Hasn't had any activity recently (inactivity_days threshold)
    3. Has multiple recorded activities (minimum_activity_count)

    Parameters
    ----------
    inactivity_days : int, default 90
        Number of days without clinical activity to flag a patient
    minimum_activity_count : int, default 2
        Minimum number of recorded clinical activities to consider a patient as "previously active"
    active_only : bool, default True
        Whether to only include patients marked as active in the system
    db_path : str, optional
        Path to SQLite database

    Returns
    -------
    pandas.DataFrame
        Columns: patient_id, first_name, last_name, last_lab_date,
                 last_mental_health_date, last_vitals_date, most_recent_activity,
                 days_since_activity, activity_count
    """
    if db_path is None:
        db_path = get_db_path()

    # Calculate the cutoff date (today - inactivity_days)
    cutoff_date = (datetime.now() - timedelta(days=inactivity_days)).strftime(
        "%Y-%m-%d"
    )

    # Build the active filter clause if needed
    active_clause = "WHERE p.active = 1" if active_only else ""

    # SQL query that finds the most recent clinical activity date for each patient
    sql = f"""
    WITH 
    patient_basics AS (
        SELECT 
            p.id as patient_id,
            p.first_name,
            p.last_name,
            p.active,
            p.program_start_date
        FROM patients p
        {active_clause}
    ),
    -- Get all lab records
    lab_records AS (
        SELECT
            patient_id,
            date as activity_date,
            'Lab Test' as activity_type
        FROM lab_results
    ),
    -- Get all mental health records
    mh_records AS (
        SELECT
            patient_id,
            date as activity_date,
            'Mental Health Screening' as activity_type
        FROM mental_health
    ),
    -- Get all vitals records
    vitals_records AS (
        SELECT
            patient_id,
            date as activity_date,
            'Vitals Measurement' as activity_type
        FROM vitals
    ),
    -- Combine all clinical activities
    all_activities AS (
        SELECT * FROM lab_records
        UNION ALL
        SELECT * FROM mh_records
        UNION ALL
        SELECT * FROM vitals_records
    ),
    -- Calculate summary metrics
    patient_activity AS (
        SELECT
            pb.patient_id,
            pb.first_name,
            pb.last_name,
            pb.program_start_date,
            MAX(CASE WHEN aa.activity_type = 'Lab Test' THEN aa.activity_date ELSE NULL END) as last_lab_date,
            MAX(CASE WHEN aa.activity_type = 'Mental Health Screening' THEN aa.activity_date ELSE NULL END) as last_mental_health_date,
            MAX(CASE WHEN aa.activity_type = 'Vitals Measurement' THEN aa.activity_date ELSE NULL END) as last_vitals_date,
            MAX(aa.activity_date) as most_recent_activity,
            COUNT(aa.activity_date) as activity_count,
            julianday('now') - julianday(MAX(aa.activity_date)) as days_since_activity,
            CASE 
                WHEN pb.program_start_date IS NULL THEN 999999
                ELSE julianday('now') - julianday(pb.program_start_date)
            END as days_enrolled
        FROM patient_basics pb
        LEFT JOIN all_activities aa ON pb.patient_id = aa.patient_id
        GROUP BY pb.patient_id, pb.first_name, pb.last_name, pb.program_start_date
    )
    SELECT *
    FROM patient_activity
    WHERE 
        -- Only include patients who have had clinical activity
        most_recent_activity IS NOT NULL
        -- And have had enough activities to be considered engaged
        AND activity_count >= ?
        -- And whose last activity was before the cutoff
        AND most_recent_activity < ?
        -- And have been enrolled long enough
        AND days_enrolled >= ?
    ORDER BY days_since_activity DESC
    """

    # Execute the query with appropriate parameters
    params = (minimum_activity_count, cutoff_date, inactivity_days)
    df = query_dataframe(sql, params=params, db_path=db_path)

    # Format dates for display
    date_columns = [
        "last_lab_date",
        "last_mental_health_date",
        "last_vitals_date",
        "most_recent_activity",
        "program_start_date",
    ]
    if not df.empty:
        for col in date_columns:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda d: (
                        format_date_for_display(d, format_str="%b %d, %Y")
                        if pd.notna(d)
                        else "Never"
                    )
                )

        # Round days to integers for cleaner display
        for col in ["days_since_activity", "days_enrolled"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)

    return df


__all__ = [
    "get_silent_dropout_report",
    "update_last_visit_date_for_patients",
    "mark_patient_as_inactive",
    "ensure_last_visit_date_column",
    "get_clinical_inactivity_report",
]
