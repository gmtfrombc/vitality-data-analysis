import sqlite3

# Connect to the database
conn = sqlite3.connect("patient_data.db")
cursor = conn.cursor()

# Ensure 'scores' table exists with correct schema
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS scores (
        score_id INTEGER PRIMARY KEY,
        patient_id TEXT NOT NULL,
        date TEXT,
        score_type TEXT,
        score_value INTEGER
    )
"""
)
conn.commit()

# Seed scores table if empty
cursor.execute("SELECT COUNT(*) FROM scores")
if cursor.fetchone()[0] == 0:
    cursor.execute(
        "INSERT INTO scores (patient_id, date, score_type, score_value) VALUES ('1', '2024-01-01', 'PHQ', 10)"
    )
    cursor.execute(
        "INSERT INTO scores (patient_id, date, score_type, score_value) VALUES ('2', '2024-01-02', 'GAD', 8)"
    )
    cursor.execute(
        "INSERT INTO scores (patient_id, date, score_type, score_value) VALUES ('2', '2024-01-03', 'PHQ', 12)"
    )
    conn.commit()

# Get sample score data
print("Sample data from scores table:")
cursor.execute("SELECT * FROM scores LIMIT 10")
scores = cursor.fetchall()
cursor.execute("PRAGMA table_info(scores)")
columns = [col[1] for col in cursor.fetchall()]
print(f"Columns: {columns}")
for score in scores:
    print(score)

# Check distinct score types
print("\nDistinct score types:")
cursor.execute("SELECT DISTINCT score_type FROM scores")
score_types = cursor.fetchall()
for score_type in score_types:
    print(f"  {score_type[0]}")

# Get sample for specific patient
print("\nSample scores for patient ID 2:")
cursor.execute("SELECT * FROM scores WHERE patient_id = '2' LIMIT 5")
patient_scores = cursor.fetchall()
for score in patient_scores:
    print(score)

conn.close()
