import sqlite3
import pandas as pd

conn = sqlite3.connect("patient_data.db")

# Identify patients with weight loss by comparing first and last weights
query = """
WITH first_weights AS (
    SELECT patient_id, date, weight
    FROM vitals
    WHERE weight IS NOT NULL 
    AND date = (SELECT MIN(date) FROM vitals v2 
                WHERE v2.patient_id = vitals.patient_id
                AND v2.weight IS NOT NULL)
),
last_weights AS (
    SELECT patient_id, date, weight
    FROM vitals
    WHERE weight IS NOT NULL 
    AND date = (SELECT MAX(date) FROM vitals v2 
                WHERE v2.patient_id = vitals.patient_id
                AND v2.weight IS NOT NULL)
)
SELECT 
    p.id,
    p.first_name,
    p.last_name,
    p.active,
    p.program_start_date,
    p.program_end_date,
    fw.date as first_weight_date,
    fw.weight as first_weight,
    lw.date as last_weight_date,
    lw.weight as last_weight,
    julianday(lw.date) - julianday(fw.date) as days_between,
    (fw.weight - lw.weight) as weight_loss,
    (fw.weight - lw.weight) / fw.weight * 100 as percent_loss
FROM 
    patients p
JOIN 
    first_weights fw ON p.id = fw.patient_id
JOIN 
    last_weights lw ON p.id = lw.patient_id
WHERE 
    lw.weight < fw.weight
    AND julianday(lw.date) - julianday(fw.date) >= 180
    AND p.active = 1
ORDER BY 
    percent_loss DESC
LIMIT 20;
"""

# Execute and print the results
results = pd.read_sql_query(query, conn)
print(f"Found {len(results)} patients with weight loss over 6+ months:")
print(results.to_string())

# Check for patients with 10%+ weight loss
weight_loss_patients = results[results["percent_loss"] >= 10]
print(f"\nPatients with 10%+ weight loss: {len(weight_loss_patients)}")
if not weight_loss_patients.empty:
    print(weight_loss_patients[["id", "first_weight", "last_weight", "percent_loss"]])

conn.close()
