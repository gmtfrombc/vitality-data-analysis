"""Build a reusable mock-validation SQLite database.

Creates (or overwrites) a small SQLite file with eight patients: one clean
record and seven with deliberately bad or edge-case data so that the
ValidationEngine should flag them.  The schema is the same minimal subset
used by the unit-test fixture, and the current validation-rule catalogue is
seeded.

Usage (from repo root):

    python scripts/build_mock_validation_db.py [--out data/mock_validation.db]

Then point the application at it:

    export DATA_DB_PATH=data/mock_validation.db
    panel serve run.py
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Dict, List

from app.utils.rule_loader import initialize_validation_rules

# ---------------------------------------------------------------------------
# Patient + vitals sample data
# ---------------------------------------------------------------------------

PATIENTS: List[Dict] = [
    # 1 – clean baseline patient
    {
        "id": 1,
        "first_name": "Clean",
        "last_name": "Patient",
        "program_start_date": "2025-01-01",
        "program_end_date": "2025-04-01",
        "active": 1,
        "provider_visit_count": 3,
        "bmi": 24.0,
        "weight": 160.0,
        "provider": "Dr. Clean",
        "health_coach": "Coach Clean",
    },
    # 2 – missing program_start_date (NOT-NULL rule)
    {
        "id": 2,
        "first_name": "Missing",
        "last_name": "StartDate",
        "program_start_date": None,
        "program_end_date": "2025-04-01",
        "active": 1,
        "provider_visit_count": 3,
        "bmi": 25.0,
        "weight": 170.0,
        "provider": "Dr. Missing",
        "health_coach": "Coach Missing",
    },
    # 3 – BMI way too high (RANGE rule)
    {
        "id": 3,
        "first_name": "High",
        "last_name": "BMI",
        "program_start_date": "2025-01-01",
        "program_end_date": None,
        "active": 0,
        "provider_visit_count": 3,
        "bmi": 85.0,
        "weight": 400.0,
        "provider": "Dr. High",
        "health_coach": "Coach High",
    },
    # 4 – Weight extremely high (RANGE rule)
    {
        "id": 4,
        "first_name": "Heavy",
        "last_name": "Weight",
        "program_start_date": "2025-01-01",
        "program_end_date": None,
        "active": 1,
        "provider_visit_count": 7,
        "bmi": 35.0,
        "weight": 600.0,
        "provider": "Dr. Heavy",
        "health_coach": "Coach Heavy",
    },
    # 5 – Inactive AND ≥7 visits but missing program_end_date (Conditional NOT-NULL rule)
    {
        "id": 5,
        "first_name": "No",
        "last_name": "EndDate",
        "program_start_date": "2024-06-01",
        "program_end_date": None,
        "active": 0,
        "provider_visit_count": 10,
        "bmi": 28.0,
        "weight": 190.0,
        "provider": "Dr. Inactive",
        "health_coach": "Coach Inactive",
    },
    # 6 – Blood-pressure out of plausible range (RANGE rule on vitals)
    {
        "id": 6,
        "first_name": "High",
        "last_name": "BP",
        "program_start_date": "2025-01-01",
        "program_end_date": None,
        "active": 1,
        "provider_visit_count": 4,
        "bmi": 26.0,
        "weight": 175.0,
        "provider": "Dr. Pressure",
        "health_coach": "Coach Pressure",
    },
    # 7 – Invalid categorical value for provider (ALLOWED-VALUES rule once implemented)
    {
        "id": 7,
        "first_name": "Bad",
        "last_name": "Category",
        "program_start_date": "2025-01-01",
        "program_end_date": None,
        "active": 1,
        "provider_visit_count": 2,
        "bmi": 23.0,
        "weight": 150.0,
        "provider": "ZZUnknown",  # not in allowed list
        "health_coach": "Coach Cat",
    },
    # 8 – Missing provider altogether (NOT-NULL on categorical field)
    {
        "id": 8,
        "first_name": "No",
        "last_name": "Provider",
        "program_start_date": "2025-01-01",
        "program_end_date": None,
        "active": 1,
        "provider_visit_count": 2,
        "bmi": 25.0,
        "weight": 155.0,
        "provider": None,
        "health_coach": "Coach NP",
    },
]

VITALS_ROWS = [
    # id, patient_id, date, weight, bmi, systolic, diastolic
    (1, 1, "2025-04-15", 160.0, 24.0, 120, 80),
    (2, 2, "2025-04-15", 170.0, 25.0, 118, 78),
    (3, 3, "2025-04-15", 400.0, 85.0, 130, 88),
    (4, 4, "2025-04-15", 600.0, 35.0, 140, 90),
    (5, 5, "2025-04-15", 190.0, 28.0, 126, 82),
    (6, 6, "2025-04-15", 175.0, 26.0, 300, 200),  # absurd BP
    (7, 7, "2025-04-15", 150.0, 23.0, 118, 78),
    (8, 8, "2025-04-15", 155.0, 25.0, 119, 79),
]

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE patients (
    id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    program_start_date TEXT,
    program_end_date TEXT,
    active INTEGER,
    provider_visit_count INTEGER,
    bmi REAL,
    weight REAL,
    provider TEXT,
    health_coach TEXT
);

CREATE TABLE vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    date TEXT,
    weight REAL,
    bmi REAL,
    systolic_pressure REAL,
    diastolic_pressure REAL
);

-- Validation tables (same as production subset)
CREATE TABLE validation_rules (
    rule_id TEXT PRIMARY KEY,
    description TEXT,
    rule_type TEXT,
    validation_logic TEXT,
    parameters TEXT,
    severity TEXT,
    is_active INTEGER DEFAULT 1,
    updated_at TEXT
);

CREATE TABLE validation_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT,
    patient_id TEXT,
    field_name TEXT,
    issue_description TEXT,
    status TEXT,
    detected_at TEXT
);
"""


def build_db(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()  # overwrite

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript(SCHEMA_SQL)

    # Seed patient + vitals
    cursor.executemany(
        """
        INSERT INTO patients (id, first_name, last_name, program_start_date, program_end_date, active, provider_visit_count, bmi, weight, provider, health_coach)
        VALUES (:id, :first_name, :last_name, :program_start_date, :program_end_date, :active, :provider_visit_count, :bmi, :weight, :provider, :health_coach)
        """,
        PATIENTS,
    )

    cursor.executemany(
        """
        INSERT INTO vitals (id, patient_id, date, weight, bmi, systolic_pressure, diastolic_pressure)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        VITALS_ROWS,
    )

    conn.commit()
    conn.close()

    # Load validation rules using existing helper (creates its own connection)
    initialize_validation_rules(str(db_path))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(out_path: str) -> None:
    path = Path(out_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    build_db(path)
    print(f"Mock validation DB written to {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build mock validation SQLite DB")
    parser.add_argument(
        "--out", default="data/mock_validation.db", help="Output path for SQLite file"
    )
    args = parser.parse_args()

    main(args.out)
