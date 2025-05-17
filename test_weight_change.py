from app.utils.query_intent import QueryIntent, Filter
from app.ai_helper import _generate_relative_change_analysis_code
from app.utils.sandbox import run_snippet
import sqlite3
import pandas as pd

# Create a test intent for weight loss calculation
intent = QueryIntent(
    analysis_type="change",
    target_field="weight",
    filters=[Filter(field="gender", value="F"), Filter(field="active", value=1)],
    parameters={
        "relative_date_filters": [
            {
                "window": "baseline",
                "start_expr": "program_start_date - 30 days",
                "end_expr": "program_start_date + 30 days",
            },
            {
                "window": "follow_up",
                "start_expr": "program_start_date + 5 months",
                "end_expr": "program_start_date + 7 months",
            },
        ]
    },
)

# Generate the code
code = _generate_relative_change_analysis_code(intent)
print("Generated code:")
print(code)

# Execute the code using the sandbox
print("\nExecuting code...")
results = run_snippet(code)

print("\nResults:")
print(results)

# Manually calculate weight change from SQL for verification
conn = sqlite3.connect("mock_patient_data.db")

print("\nVerifying database contents:")
print(
    f"Total active female patients: {pd.read_sql('SELECT COUNT(*) as count FROM patients WHERE gender = \"F\" AND active = 1', conn)['count'].iloc[0]}"
)
print(
    f"Total weight measurements: {pd.read_sql('SELECT COUNT(*) as count FROM vitals', conn)['count'].iloc[0]}"
)
print(
    f"Female patient weight measurements: {pd.read_sql('SELECT COUNT(*) as count FROM vitals v JOIN patients p ON v.patient_id = p.id WHERE p.gender = \"F\" AND p.active = 1', conn)['count'].iloc[0]}"
)

# Get weights at program start (±30 days)
baseline_sql = """
SELECT 
    p.id AS patient_id, 
    p.program_start_date, 
    v.date AS obs_date, 
    v.weight
FROM patients p
JOIN vitals v ON p.id = v.patient_id
WHERE p.gender = 'F' AND p.active = 1
ORDER BY p.id, v.date
"""

df = pd.read_sql(baseline_sql, conn)
print(
    f"\nRaw SQL query results: {len(df)} rows, {df['patient_id'].nunique()} unique patients"
)

df["program_start_date"] = pd.to_datetime(
    df["program_start_date"], errors="coerce", utc=True
)
df["obs_date"] = pd.to_datetime(df["obs_date"], errors="coerce", utc=True)
# Drop any rows where date parsing failed
df = df.dropna(subset=["program_start_date", "obs_date"])
# Convert to naive timestamps for consistent calculations
df["program_start_date"] = df["program_start_date"].dt.tz_localize(None)
df["obs_date"] = df["obs_date"].dt.tz_localize(None)
df["days_from_start"] = (df["obs_date"] - df["program_start_date"]).dt.days

print(f"After date parsing: {len(df)} rows with valid dates")

# Get baseline weights (program start ±30 days)
baseline_df = df[df["days_from_start"].between(-30, 30)]
print(
    f"\nBaseline data (±30 days from program start): {len(baseline_df)} rows, {baseline_df['patient_id'].nunique()} unique patients"
)
baseline = (
    baseline_df.sort_values("obs_date")
    .groupby("patient_id", as_index=False)
    .first()[["patient_id", "weight"]]
    .rename(columns={"weight": "baseline"})
)
print(f"After taking first measurement per patient: {len(baseline)} rows")

# Get follow-up weights (5-7 months)
follow_df = df[df["days_from_start"].between(150, 210)]
print(
    f"\nFollow-up data (5-7 months from program start): {len(follow_df)} rows, {follow_df['patient_id'].nunique()} unique patients"
)
follow = (
    follow_df.sort_values("obs_date")
    .groupby("patient_id", as_index=False)
    .first()[["patient_id", "weight"]]
    .rename(columns={"weight": "follow_up"})
)
print(f"After taking first measurement per patient: {len(follow)} rows")

# Calculate weight change
merged = baseline.merge(follow, on="patient_id")
print(f"\nPatients with both baseline and follow-up measurements: {len(merged)} rows")
merged["change"] = merged["baseline"] - merged["follow_up"]  # Weight loss is positive

print("\nManual verification:")
print(f"Average weight change: {merged['change'].mean()}")
print(f"Number of patients: {len(merged)}")
print("First few patients:")
print(merged.head())
