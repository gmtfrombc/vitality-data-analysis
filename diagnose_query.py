import sqlite3
import pandas as pd

conn = sqlite3.connect("patient_data.db")

# Original problematic query (simplified)
original_query = """
SELECT COUNT(p.id) as lost_weight_count
FROM patients p
JOIN vitals v ON p.id = v.patient_id
WHERE p.active = 1 
AND date(v.date) BETWEEN date(p.program_start_date, '+6 months') AND p.program_end_date
AND ((p.program_start_date IS NOT NULL AND p.program_end_date IS NOT NULL) 
    AND ((p.program_end_date - p.program_start_date) >= 180) 
    AND ((v.weight / (SELECT weight FROM vitals WHERE patient_id = p.id ORDER BY date DESC LIMIT 1)) <= 0.9))
"""

print("DIAGNOSING ISSUES IN ORIGINAL QUERY:")

# Issue 1: How many active patients have both program_start_date AND program_end_date?
q1 = """
SELECT COUNT(*) FROM patients 
WHERE active = 1 
AND program_start_date IS NOT NULL 
AND program_end_date IS NOT NULL
"""
result1 = pd.read_sql_query(q1, conn)
print(f"\n1. Patients with both start and end dates: {result1.iloc[0, 0]}")

# Issue 2: How many dates fall between program_start_date+6months and program_end_date?
q2 = """
SELECT COUNT(*) FROM patients p
JOIN vitals v ON p.id = v.patient_id
WHERE p.active = 1
AND p.program_start_date IS NOT NULL
AND p.program_end_date IS NOT NULL
AND date(v.date) BETWEEN date(p.program_start_date, '+6 months') AND p.program_end_date
"""
result2 = pd.read_sql_query(q2, conn)
print(
    f"\n2. Vital records falling between start+6months and end date: {result2.iloc[0, 0]}"
)

# Issue 3: How many patients have weight ratio <= 0.9 using the original calculation?
q3 = """
SELECT COUNT(*) FROM patients p
JOIN vitals v ON p.id = v.patient_id
WHERE p.active = 1
AND p.program_start_date IS NOT NULL
AND (v.weight / (SELECT weight FROM vitals WHERE patient_id = p.id ORDER BY date DESC LIMIT 1)) <= 0.9
"""
result3 = pd.read_sql_query(q3, conn)
print(
    f"\n3. Patients with original weight ratio calculation <= 0.9: {result3.iloc[0, 0]}"
)

# Issue 4: How many patients have the correct weight ratio (final/initial) <= 0.9 ?
q4 = """
WITH first_weights AS (
    SELECT patient_id, MIN(date) as date, weight
    FROM vitals
    WHERE weight IS NOT NULL
    GROUP BY patient_id
),
last_weights AS (
    SELECT patient_id, MAX(date) as date, weight
    FROM vitals
    WHERE weight IS NOT NULL
    GROUP BY patient_id
)
SELECT COUNT(*) FROM patients p
JOIN first_weights fw ON p.id = fw.patient_id
JOIN last_weights lw ON p.id = lw.patient_id
WHERE p.active = 1
AND p.program_start_date IS NOT NULL
AND (lw.weight / fw.weight) <= 0.9
"""
result4 = pd.read_sql_query(q4, conn)
print(
    f"\n4. Patients with correct weight ratio (final/initial) <= 0.9: {result4.iloc[0, 0]}"
)

print("\nCORRECTED QUERY:")
corrected_query = """
WITH first_weights AS (
    SELECT patient_id, MIN(date) as date, weight
    FROM vitals
    WHERE weight IS NOT NULL
    GROUP BY patient_id
),
last_weights AS (
    SELECT patient_id, MAX(date) as date, weight
    FROM vitals
    WHERE weight IS NOT NULL
    GROUP BY patient_id
)
SELECT COUNT(*) FROM patients p
JOIN first_weights fw ON p.id = fw.patient_id
JOIN last_weights lw ON p.id = lw.patient_id
WHERE p.active = 1
AND p.program_start_date IS NOT NULL
AND julianday(lw.date) - julianday(fw.date) >= 180
AND (lw.weight / fw.weight) <= 0.9
"""
result5 = pd.read_sql_query(corrected_query, conn)
print(
    f"\n5. Patients who lost 10%+ weight over 6+ months (corrected query): {result5.iloc[0, 0]}"
)

conn.close()
