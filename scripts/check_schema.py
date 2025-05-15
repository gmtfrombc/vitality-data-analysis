import sqlite3

# Connect to the database
conn = sqlite3.connect("patient_data.db")

# Check patients table schema
print("Patients Table Schema:")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(patients)")
patients_columns = cursor.fetchall()
for col in patients_columns:
    print(f"  {col[1]} ({col[2]})")

# Check vitals table schema
print("\nVitals Table Schema:")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(vitals)")
vitals_columns = cursor.fetchall()
for col in vitals_columns:
    print(f"  {col[1]} ({col[2]})")

# Check mental_health table schema
print("\nMental Health Table Schema:")
cursor.execute("PRAGMA table_info(mental_health)")
mh_columns = cursor.fetchall()
for col in mh_columns:
    print(f"  {col[1]} ({col[2]})")

# Check lab_results table schema
print("\nLab Results Table Schema:")
cursor.execute("PRAGMA table_info(lab_results)")
lab_columns = cursor.fetchall()
for col in lab_columns:
    print(f"  {col[1]} ({col[2]})")

# Check scores table schema
print("\nScores Table Schema:")
cursor.execute("PRAGMA table_info(scores)")
scores_columns = cursor.fetchall()
for col in scores_columns:
    print(f"  {col[1]} ({col[2]})")

# Check for sample data
print("\n=== SAMPLE DATA CHECK ===")

# Show first 5 patients
print("\nSample Patients:")
cursor.execute("SELECT id, first_name, last_name FROM patients LIMIT 5")
patients = cursor.fetchall()
for p in patients:
    print(f"  ID: {p[0]}, Name: {p[1]} {p[2]}")

# Check if patient 1 exists
print("\nPatient with ID 1:")
cursor.execute("SELECT * FROM patients WHERE id = '1'")
patient1 = cursor.fetchone()
if patient1:
    print(f"  Found: {patient1}")
else:
    print("  Not found")

# Check if patient has vitals
if patient1:
    print("\nVitals for Patient ID 1:")
    cursor.execute("SELECT * FROM vitals WHERE patient_id = '1' LIMIT 3")
    vitals = cursor.fetchall()
    if vitals:
        for v in vitals:
            print(f"  {v}")
    else:
        print("  No vitals data found")

# Show sample from each table
cursor.execute("SELECT COUNT(*) FROM patients")
print(f"\nTotal Patients: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM vitals")
print(f"Total Vitals Records: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM mental_health")
print(f"Total Mental Health Records: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM lab_results")
print(f"Total Lab Result Records: {cursor.fetchone()[0]}")

conn.close()
