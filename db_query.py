"""
Backend Query Module for Metabolic Health Data Analysis

This module provides functions to interact with the SQLite database,
including basic CRUD operations for the "patients" table and
utilities to execute SQL queries and return Pandas DataFrames.
"""

import sqlite3
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "patient_data.db"


def query_dataframe(query, params=None, db_path=DB_PATH):
    """
    Execute a SQL query and return the results as a Pandas DataFrame.

    Args:
        query (str): The SQL query to execute.
        params (tuple, optional): Parameters to pass with the query.
        db_path (str): Path to the SQLite database file.

    Returns:
        DataFrame: Query results.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        logger.debug(f"Executing query: {query} with params: {params}")
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except sqlite3.Error as e:
        logger.error(f"Database error in query: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def get_all_patients(db_path=DB_PATH):
    """
    Retrieve all patient records.

    Args:
        db_path (str): Path to the SQLite database file.

    Returns:
        DataFrame: All patients.
    """
    query = "SELECT * FROM patients;"
    return query_dataframe(query, db_path=db_path)


def get_patient_by_id(patient_id, db_path=DB_PATH):
    """
    Retrieve a patient record by ID.

    Args:
        patient_id (str or int): The ID of the patient.
        db_path (str): Path to the SQLite database file.

    Returns:
        DataFrame: Patient record.
    """
    # ID must be treated as TEXT
    patient_id = str(patient_id)
    query = "SELECT * FROM patients WHERE id = ?;"
    df = query_dataframe(query, params=(patient_id,), db_path=db_path)
    if df.empty:
        logger.warning(f"No patient found with ID: {patient_id}")
    return df


def validate_patient_data(data):
    """
    Validate patient data against the schema requirements.

    Args:
        data (dict): Patient data dictionary.

    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = [
        "first_name",
        "last_name",
        "birth_date",
        "gender"
    ]

    # Check required fields
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    return True, ""


def create_patient(data, db_path=DB_PATH):
    """
    Insert a new patient record with improved error handling.

    Args:
        data (dict): A dictionary where keys are column names and values are the corresponding values.
        db_path (str): Path to the SQLite database file.

    Returns:
        str: The ID of the newly inserted patient, or None if the operation failed.
    """
    # Validate data
    is_valid, error_msg = validate_patient_data(data)
    if not is_valid:
        logger.error(f"Invalid patient data: {error_msg}")
        return None

    # Make sure we have an ID and it's a string (TEXT)
    if 'id' not in data:
        # Get max ID from the database and increment
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT MAX(CAST(id AS INTEGER)) FROM patients")
        max_id = cur.fetchone()[0]
        conn.close()

        # Create new ID
        new_id = str(int(max_id) + 1) if max_id else "1"
        data['id'] = new_id
    else:
        # Ensure ID is stored as a string
        data['id'] = str(data['id'])

    columns = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    values = tuple(data.values())
    query = f"INSERT INTO patients ({columns}) VALUES ({placeholders});"

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        logger.debug(f"Executing insert: {query} with values: {values}")
        cur.execute(query, values)
        conn.commit()

        # Return the ID we inserted
        inserted_id = data['id']

        # Verify the insertion worked
        verification_query = "SELECT COUNT(*) FROM patients WHERE id = ?"
        cur.execute(verification_query, (inserted_id,))
        count = cur.fetchone()[0]

        if count == 0:
            logger.warning(f"Inserted ID {inserted_id} could not be verified")
            return None

        logger.info(f"Successfully inserted patient with ID: {inserted_id}")
        return inserted_id
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error during insert: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_patient(patient_id, updates, db_path=DB_PATH):
    """
    Update an existing patient record with improved error handling.

    Args:
        patient_id (str or int): The ID of the patient to update.
        updates (dict): A dictionary of columns to update with their new values.
        db_path (str): Path to the SQLite database file.

    Returns:
        bool: True if update was successful.
    """
    if not updates:
        logger.error("No update values provided")
        return False

    # Convert patient_id to string to match TEXT type
    patient_id = str(patient_id)

    # First check if patient exists
    check_df = get_patient_by_id(patient_id, db_path)
    if check_df.empty:
        logger.error(
            f"Cannot update patient {patient_id} - patient does not exist")
        return False

    set_clause = ", ".join(f"{column} = ?" for column in updates.keys())
    values = tuple(updates.values()) + (patient_id,)
    query = f"UPDATE patients SET {set_clause} WHERE id = ?;"

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        logger.debug(f"Executing update: {query} with values: {values}")
        cur.execute(query, values)
        rows_affected = cur.rowcount

        if rows_affected == 0:
            logger.warning(
                f"Update did not affect any rows for patient ID: {patient_id}")
            conn.rollback()
            return False

        conn.commit()
        logger.info(f"Successfully updated patient with ID: {patient_id}")
        return True
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error during update: {e}")
        return False
    finally:
        if conn:
            conn.close()


def delete_patient(patient_id, db_path=DB_PATH):
    """
    Delete a patient record based on ID with improved error handling.

    Args:
        patient_id (str or int): The ID of the patient to delete.
        db_path (str): Path to the SQLite database file.

    Returns:
        bool: True if deletion was successful.
    """
    # Convert patient_id to string to match TEXT type
    patient_id = str(patient_id)

    # First check if patient exists
    check_df = get_patient_by_id(patient_id, db_path)
    if check_df.empty:
        logger.error(
            f"Cannot delete patient {patient_id} - patient does not exist")
        return False

    query = "DELETE FROM patients WHERE id = ?;"

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        logger.debug(
            f"Executing delete: {query} with patient_id: {patient_id}")
        cur.execute(query, (patient_id,))
        rows_affected = cur.rowcount

        if rows_affected == 0:
            logger.warning(
                f"Delete did not affect any rows for patient ID: {patient_id}")
            conn.rollback()
            return False

        conn.commit()
        logger.info(f"Successfully deleted patient with ID: {patient_id}")
        return True
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error during delete: {e}")
        return False
    finally:
        if conn:
            conn.close()


# Example usage (you can remove or modify these when integrating with your app)
if __name__ == "__main__":
    # Set logging level to INFO for script execution
    logger.setLevel(logging.INFO)

    # Get all patients
    patients_df = get_all_patients()
    print("\nAll Patients (first 5):")
    print(patients_df.head())
    print(f"Total patients: {len(patients_df)}")

    # Get table schema - useful for debugging
    print("\nGetting database schema...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(patients)")
    columns = cursor.fetchall()
    print("Patients table schema:")
    for col in columns:
        print(f"  {col[1]} ({col[2]}){' PRIMARY KEY' if col[5] else ''}")
    conn.close()

    # Test inserting a patient
    print("\nInserting a test patient...")
    try:
        # Get max ID and create a new one
        max_id_conn = sqlite3.connect(DB_PATH)
        max_id_cur = max_id_conn.cursor()
        max_id_cur.execute("SELECT MAX(CAST(id AS INTEGER)) FROM patients")
        max_id = max_id_cur.fetchone()[0]
        new_id = str(int(max_id) + 1)
        max_id_conn.close()

        print(f"Using new ID: {new_id}")

        # Insert a new patient with explicitly structured ID
        new_patient = {
            "id": new_id,  # Explicitly assign as string
            "first_name": "Test",
            "last_name": "User",
            "birth_date": "1990-01-01 00:00:00",
            "gender": "M",
            "ethnicity": "Not Hispanic or Latino",
            "engagement_score": 85,
            "program_start_date": "2023-04-01 00:00:00"
        }
        inserted_id = create_patient(new_patient)

        if inserted_id:
            print(f"Successfully inserted patient with ID: {inserted_id}")

            # Retrieve the new patient
            patient_df = get_patient_by_id(inserted_id)
            print("\nNew Patient Record:")
            print(patient_df)

            # Update the patient record
            print("\nUpdating patient...")
            update_status = update_patient(
                inserted_id, {"engagement_score": 90})
            print(f"Update Successful: {update_status}")

            if update_status:
                # Retrieve the updated patient record
                updated_patient_df = get_patient_by_id(inserted_id)
                print("\nUpdated Patient Record:")
                print(updated_patient_df)

            # Delete the patient record
            print("\nDeleting patient...")
            delete_status = delete_patient(inserted_id)
            print(f"Deletion Successful: {delete_status}")

            # Verify the patient is deleted
            if delete_status:
                verify_df = get_patient_by_id(inserted_id)
                if verify_df.empty:
                    print(
                        f"Confirmed: Patient {inserted_id} no longer exists in the database")
        else:
            print("Failed to insert new patient")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# ----- AGGREGATION FUNCTIONS -----


def get_program_stats(db_path=DB_PATH):
    """
    Get aggregated statistics about the patient population.

    Args:
        db_path (str): Path to the SQLite database file

    Returns:
        dict: Statistics about the program
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    stats = {}

    try:
        # Total patients
        cursor.execute("SELECT COUNT(*) FROM patients")
        stats['total_patients'] = cursor.fetchone()[0]

        # Gender distribution
        cursor.execute("""
            SELECT gender, COUNT(*) as count 
            FROM patients 
            GROUP BY gender
        """)
        stats['gender_distribution'] = {row[0]: row[1]
                                        for row in cursor.fetchall()}

        # Ethnicity distribution
        cursor.execute("""
            SELECT ethnicity, COUNT(*) as count 
            FROM patients 
            GROUP BY ethnicity
        """)
        stats['ethnicity_distribution'] = {
            row[0]: row[1] for row in cursor.fetchall()}

        # Engagement score statistics
        cursor.execute("""
            SELECT 
                AVG(engagement_score) as avg_score,
                MIN(engagement_score) as min_score,
                MAX(engagement_score) as max_score
            FROM patients
            WHERE engagement_score IS NOT NULL
        """)
        row = cursor.fetchone()
        stats['engagement_scores'] = {
            'avg': row[0],
            'min': row[1],
            'max': row[2]
        }

        # Vital sign averages
        cursor.execute("""
            SELECT 
                AVG(weight) as avg_weight,
                AVG(bmi) as avg_bmi,
                AVG(sbp) as avg_sbp,
                AVG(dbp) as avg_dbp
            FROM vitals
        """)
        row = cursor.fetchone()
        stats['vitals_averages'] = {
            'weight': row[0],
            'bmi': row[1],
            'sbp': row[2],
            'dbp': row[3]
        }

        # Mental health averages by assessment type
        cursor.execute("""
            SELECT 
                assessment_type, AVG(score) as avg_score
            FROM mental_health
            GROUP BY assessment_type
        """)
        stats['mental_health_averages'] = {
            row[0]: row[1] for row in cursor.fetchall()}

    except sqlite3.Error as e:
        logger.error(f"Error getting program stats: {e}")
    finally:
        conn.close()

    return stats


def get_patient_overview(patient_id, db_path=DB_PATH):
    """
    Get a comprehensive overview of a patient including demographics, 
    vitals, mental health, and lab results.

    Args:
        patient_id (str or int): Patient ID
        db_path (str): Path to the SQLite database file

    Returns:
        dict: Overview data for the patient
    """
    patient_id = str(patient_id)
    overview = {}

    try:
        # Get patient demographics
        patient_df = get_patient_by_id(patient_id, db_path)
        if patient_df.empty:
            logger.warning(f"No patient found with ID: {patient_id}")
            return overview

        overview['demographics'] = patient_df.iloc[0].to_dict()

        # Get most recent vitals
        vitals_df = get_patient_vitals(patient_id, db_path=db_path)
        if not vitals_df.empty:
            overview['latest_vitals'] = vitals_df.iloc[0].to_dict()

        # Get most recent mental health assessments (one of each type)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM mental_health t1
            INNER JOIN (
                SELECT assessment_type, MAX(date) as max_date
                FROM mental_health
                WHERE patient_id = ?
                GROUP BY assessment_type
            ) t2 ON t1.assessment_type = t2.assessment_type AND t1.date = t2.max_date
            WHERE t1.patient_id = ?
        """, (patient_id, patient_id))

        columns = [desc[0] for desc in cursor.description]
        mh_results = cursor.fetchall()
        conn.close()

        if mh_results:
            overview['mental_health'] = [
                dict(zip(columns, row)) for row in mh_results]

        # Get most recent lab results
        labs_df = get_most_recent_labs(patient_id, db_path=db_path)
        if not labs_df.empty:
            overview['latest_labs'] = labs_df.to_dict('records')

    except Exception as e:
        logger.error(f"Error getting patient overview: {e}")

    return overview


def find_patients_with_abnormal_values(db_path=DB_PATH):
    """
    Find patients with abnormal lab or vital values.

    Args:
        db_path (str): Path to the SQLite database file

    Returns:
        pandas.DataFrame: DataFrame containing patients with abnormal values
    """
    conn = sqlite3.connect(db_path)

    # Define normal ranges for different measurements
    normal_ranges = {
        'glucose_level': (70, 99),   # mg/dL
        'a1c': (4.0, 5.6),           # %
        'total_cholesterol': (0, 200),  # mg/dL
        'ldl': (0, 100),             # mg/dL
        'hdl': (40, 999),            # mg/dL (higher is better)
        'triglycerides': (0, 150),   # mg/dL
        'sbp': (90, 120),            # mmHg
        'dbp': (60, 80),             # mmHg
        'bmi': (18.5, 24.9)          # kg/m²
    }

    try:
        # Construct query parts for lab results outside normal ranges
        lab_conditions = []
        lab_columns = []

        for measure, (low, high) in normal_ranges.items():
            if measure in ['sbp', 'dbp', 'bmi']:  # These are in vitals table
                continue

            lab_conditions.append(
                f"(lab_results.test_name = '{measure}' AND (lab_results.value < {low} OR lab_results.value > {high}))")
            lab_columns.append(
                f"MAX(CASE WHEN lab_results.test_name = '{measure}' THEN lab_results.value END) AS {measure}")

        # Construct query parts for vital signs outside normal ranges
        vital_conditions = []
        vital_columns = []

        for measure, (low, high) in normal_ranges.items():
            if measure in ['sbp', 'dbp', 'bmi']:
                vital_conditions.append(
                    f"(vitals.{measure} < {low} OR vitals.{measure} > {high})")
                vital_columns.append(f"vitals.{measure}")

        # Build query for abnormal lab values
        lab_query = f"""
        SELECT 
            patients.id as patient_id,
            patients.first_name,
            patients.last_name,
            patients.gender,
            CAST(strftime('%Y', 'now') - strftime('%Y', patients.birth_date) AS INTEGER) as age,
            {', '.join(lab_columns)}
        FROM 
            patients
        JOIN 
            lab_results ON patients.id = lab_results.patient_id
        WHERE 
            {' OR '.join(lab_conditions)}
        GROUP BY 
            patients.id
        """

        # Build query for abnormal vital values
        vital_query = f"""
        SELECT 
            patients.id as patient_id,
            patients.first_name,
            patients.last_name,
            patients.gender,
            CAST(strftime('%Y', 'now') - strftime('%Y', patients.birth_date) AS INTEGER) as age,
            {', '.join(vital_columns)}
        FROM 
            patients
        JOIN 
            vitals ON patients.id = vitals.patient_id
        WHERE 
            {' OR '.join(vital_conditions)}
        GROUP BY 
            patients.id
        """

        # Execute queries
        lab_df = pd.read_sql_query(lab_query, conn)
        vital_df = pd.read_sql_query(vital_query, conn)

        # Merge the two dataframes
        if lab_df.empty and vital_df.empty:
            return pd.DataFrame()
        elif lab_df.empty:
            return vital_df
        elif vital_df.empty:
            return lab_df
        else:
            # Merge on patient_id, keeping all rows from both dataframes
            result_df = pd.merge(lab_df, vital_df, on=[
                                 'patient_id', 'first_name', 'last_name', 'gender', 'age'], how='outer')
            return result_df

    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error(f"Error finding patients with abnormal values: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_patient_vitals(patient_id, start_date=None, end_date=None, db_path=DB_PATH):
    """
    Get vital signs for a specific patient, optionally filtered by date range.

    Args:
        patient_id (str or int): Patient ID
        start_date (str, optional): Start date for filtering (YYYY-MM-DD)
        end_date (str, optional): End date for filtering (YYYY-MM-DD)
        db_path (str): Path to the SQLite database file

    Returns:
        DataFrame: Patient vitals data, ordered by date descending
    """
    patient_id = str(patient_id)
    print(f"Debug: get_patient_vitals querying for patient_id: '{patient_id}'")

    query = "SELECT * FROM vitals WHERE patient_id = ?"
    params = [patient_id]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    df = query_dataframe(query, params=tuple(params), db_path=db_path)
    print(f"Debug: get_patient_vitals returned {len(df)} rows")
    return df


def get_patient_mental_health(patient_id, start_date=None, end_date=None, db_path=DB_PATH):
    """
    Get mental health assessments for a specific patient, optionally filtered by date range.

    Args:
        patient_id (str or int): Patient ID
        start_date (str, optional): Start date for filtering (YYYY-MM-DD)
        end_date (str, optional): End date for filtering (YYYY-MM-DD)
        db_path (str): Path to the SQLite database file

    Returns:
        DataFrame: Patient mental health data, ordered by date descending
    """
    patient_id = str(patient_id)

    query = "SELECT * FROM mental_health WHERE patient_id = ?"
    params = [patient_id]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    return query_dataframe(query, params=tuple(params), db_path=db_path)


def get_patient_labs(patient_id, start_date=None, end_date=None, db_path=DB_PATH):
    """
    Get lab results for a specific patient, optionally filtered by date range.

    Args:
        patient_id (str or int): Patient ID
        start_date (str, optional): Start date for filtering (YYYY-MM-DD)
        end_date (str, optional): End date for filtering (YYYY-MM-DD)
        db_path (str): Path to the SQLite database file

    Returns:
        DataFrame: Patient lab results, ordered by date descending
    """
    patient_id = str(patient_id)

    query = "SELECT * FROM lab_results WHERE patient_id = ?"
    params = [patient_id]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    return query_dataframe(query, params=tuple(params), db_path=db_path)


def get_most_recent_labs(patient_id, db_path=DB_PATH):
    """
    Get the most recent lab results for each test type for a specific patient.

    Args:
        patient_id (str or int): Patient ID
        db_path (str): Path to the SQLite database file

    Returns:
        DataFrame: Most recent lab results for each test type
    """
    patient_id = str(patient_id)

    query = """
    SELECT 
        t1.lab_id,
        t1.patient_id,
        t1.date,
        t1.test_name,
        t1.value,
        t1.unit,
        t1.reference_range
    FROM lab_results t1
    INNER JOIN (
        SELECT test_name, MAX(date) as max_date
        FROM lab_results
        WHERE patient_id = ?
        GROUP BY test_name
    ) t2 ON t1.test_name = t2.test_name AND t1.date = t2.max_date
    WHERE t1.patient_id = ?
    ORDER BY t1.test_name
    """

    return query_dataframe(query, params=(patient_id, patient_id), db_path=db_path)


def get_patient_scores(patient_id, start_date=None, end_date=None, db_path=DB_PATH):
    """
    Get metabolic health scores (vitality_score and heart_fit_score) for a specific patient, 
    optionally filtered by date range.

    Args:
        patient_id (str or int): Patient ID
        start_date (str, optional): Start date for filtering (YYYY-MM-DD)
        end_date (str, optional): End date for filtering (YYYY-MM-DD)
        db_path (str): Path to the SQLite database file

    Returns:
        DataFrame: Patient scores data, ordered by date descending
    """
    patient_id = str(patient_id)

    query = "SELECT * FROM scores WHERE patient_id = ?"
    params = [patient_id]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    return query_dataframe(query, params=tuple(params), db_path=db_path)
