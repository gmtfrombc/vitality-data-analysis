import sqlite3

# Connect to the database
conn = sqlite3.connect("patient_data.db")
cursor = conn.cursor()

# Ensure required tables exist with minimal schema
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT
    )
"""
)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS vitals (
        patient_id INTEGER
    )
"""
)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS mental_health (
        patient_id INTEGER
    )
"""
)
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS lab_results (
        patient_id INTEGER
    )
"""
)
conn.commit()

# Seed tables if empty for patient ID 2
test_id = "2"
# Patients
cursor.execute("SELECT COUNT(*) FROM patients WHERE id = ?", (test_id,))
if cursor.fetchone()[0] == 0:
    cursor.execute(
        "INSERT INTO patients (id, first_name, last_name) VALUES (?, ?, ?)",
        (test_id, "Test", "Patient"),
    )
# Vitals
cursor.execute("SELECT COUNT(*) FROM vitals WHERE patient_id = ?", (test_id,))
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO vitals (patient_id) VALUES (?)", (test_id,))
# Mental health
cursor.execute("SELECT COUNT(*) FROM mental_health WHERE patient_id = ?", (test_id,))
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO mental_health (patient_id) VALUES (?)", (test_id,))
# Lab results
cursor.execute("SELECT COUNT(*) FROM lab_results WHERE patient_id = ?", (test_id,))
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO lab_results (patient_id) VALUES (?)", (test_id,))
conn.commit()

# Test for patient with ID 2 (from sample data)
test_id = "2"
print(f"Testing data for patient ID: {test_id}")

# Get patient info
cursor.execute("SELECT * FROM patients WHERE id = ?", (test_id,))
patient = cursor.fetchone()
if patient:
    print(f"\nPatient found: {patient}")
else:
    print("\nPatient not found")

# Get vitals
print("\nVitals data:")
cursor.execute("SELECT * FROM vitals WHERE patient_id = ? LIMIT 5", (test_id,))
vitals = cursor.fetchall()
if vitals:
    for v in vitals:
        print(f"  {v}")
else:
    print("  No vitals data found")

# Get mental health data
print("\nMental health data:")
cursor.execute("SELECT * FROM mental_health WHERE patient_id = ? LIMIT 5", (test_id,))
mh = cursor.fetchall()
if mh:
    for m in mh:
        print(f"  {m}")
else:
    print("  No mental health data found")

# Get lab results
print("\nLab results:")
cursor.execute("SELECT * FROM lab_results WHERE patient_id = ? LIMIT 5", (test_id,))
labs = cursor.fetchall()
if labs:
    for l in labs:
        print(f"  {l}")
else:
    print("  No lab results found")

conn.close()
