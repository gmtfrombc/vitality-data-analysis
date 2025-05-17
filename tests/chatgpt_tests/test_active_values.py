from app.db_query import query_dataframe as qdf

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
