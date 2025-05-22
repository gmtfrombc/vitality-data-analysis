from app.db_query import query_dataframe as qdf
import sqlite3

# Ensure 'active' column exists in patients table
conn = sqlite3.connect("patient_data.db")
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE patients ADD COLUMN active INTEGER DEFAULT 0")
except sqlite3.OperationalError as e:
    if "duplicate column name" not in str(e):
        raise
conn.commit()
conn.close()

# Ensure 'bmi' column exists in vitals table
conn = sqlite3.connect("patient_data.db")
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE vitals ADD COLUMN bmi REAL DEFAULT NULL")
except sqlite3.OperationalError as e:
    if "duplicate column name" not in str(e):
        raise
conn.commit()
conn.close()

print("\n1. Distinct values in patients.active column:")
print(qdf("SELECT DISTINCT active FROM patients"))

print("\n2. Patient count with BMI > 30 (no active filter):")
print(
    qdf(
        """
    SELECT COUNT(DISTINCT patients.id) AS patient_count
    FROM patients
    INNER JOIN vitals ON patients.id = vitals.patient_id
    WHERE vitals.bmi > 30
"""
    )
)
