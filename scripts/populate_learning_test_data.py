#!/usr/bin/env python3
"""
Populate Learning Test Data

This script populates the database with sample learning data for testing
the learning analytics dashboard in Sprint 2.2.
"""

import sqlite3
import json
from datetime import datetime, timedelta
import random
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent
db_path = project_root / "patient_data.db"


def populate_test_data():
    """Populate database with sample learning data."""

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Clear existing test data
        cursor.execute("DELETE FROM pattern_applications")
        cursor.execute("DELETE FROM user_feedback")

        # Add some sample intent patterns if they don't exist
        sample_patterns = [
            {
                "query_pattern": "average bmi active patients",
                "canonical_intent_json": json.dumps(
                    {
                        "analysis_type": "average",
                        "target_field": "bmi",
                        "filters": [{"field": "active", "operator": "=", "value": 1}],
                    }
                ),
                "confidence_boost": 0.15,
                "usage_count": 25,
                "success_rate": 0.88,
            },
            {
                "query_pattern": "count patients by age group",
                "canonical_intent_json": json.dumps(
                    {
                        "analysis_type": "count",
                        "target_field": "patients",
                        "group_by": ["age_group"],
                    }
                ),
                "confidence_boost": 0.12,
                "usage_count": 18,
                "success_rate": 0.94,
            },
            {
                "query_pattern": "blood pressure distribution",
                "canonical_intent_json": json.dumps(
                    {
                        "analysis_type": "distribution",
                        "target_field": "systolic_bp",
                        "filters": [],
                    }
                ),
                "confidence_boost": 0.10,
                "usage_count": 12,
                "success_rate": 0.75,
            },
        ]

        pattern_ids = []
        for pattern in sample_patterns:
            cursor.execute(
                """
                INSERT OR IGNORE INTO intent_patterns 
                (query_pattern, canonical_intent_json, confidence_boost, usage_count, success_rate, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    pattern["query_pattern"],
                    pattern["canonical_intent_json"],
                    pattern["confidence_boost"],
                    pattern["usage_count"],
                    pattern["success_rate"],
                    (
                        datetime.now() - timedelta(days=random.randint(1, 30))
                    ).isoformat(),
                ),
            )

            # Get the pattern ID
            cursor.execute(
                "SELECT id FROM intent_patterns WHERE query_pattern = ?",
                (pattern["query_pattern"],),
            )
            result = cursor.fetchone()
            if result:
                pattern_ids.append(result[0])

        # Generate pattern applications over the last 30 days
        now = datetime.now()
        for i in range(100):  # 100 pattern applications
            pattern_id = random.choice(pattern_ids)
            success = random.choice([True, True, True, False])  # 75% success rate
            confidence_score = random.uniform(0.6, 0.95)
            applied_at = now - timedelta(days=random.randint(0, 30))

            cursor.execute(
                """
                INSERT INTO pattern_applications 
                (pattern_id, success, confidence_score, applied_at, query_text, result_quality)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    str(pattern_id),
                    success,
                    confidence_score,
                    applied_at.isoformat(),
                    f"Sample query for pattern {pattern_id}",
                    random.randint(3, 5) if success else random.randint(1, 3),
                ),
            )

        # Generate some correction sessions
        correction_types = ["intent_fix", "code_fix", "logic_fix", "data_fix"]
        statuses = ["pending", "integrated", "validated", "rejected"]

        for i in range(20):  # 20 correction sessions
            created_at = now - timedelta(days=random.randint(0, 30))
            status = random.choice(statuses)

            cursor.execute(
                """
                INSERT INTO correction_sessions 
                (original_query, correction_type, status, created_at, reviewed_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    f"Sample query {i+1}",
                    random.choice(correction_types),
                    status,
                    created_at.isoformat(),
                    (
                        (
                            created_at + timedelta(hours=random.randint(1, 48))
                        ).isoformat()
                        if status in ["integrated", "validated", "rejected"]
                        else None
                    ),
                ),
            )

        # Generate user feedback
        feedback_types = [
            "pattern_effectiveness",
            "correction_quality",
            "system_accuracy",
        ]

        for i in range(50):  # 50 feedback entries
            created_at = now - timedelta(days=random.randint(0, 30))

            cursor.execute(
                """
                INSERT INTO user_feedback 
                (feedback_type, rating, comment, created_at, session_id)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    random.choice(feedback_types),
                    random.randint(1, 5),
                    f"Sample feedback comment {i+1}",
                    created_at.isoformat(),
                    f"session_{i+1}",
                ),
            )

        conn.commit()
        print("✅ Successfully populated learning test data")
        print(f"   - {len(sample_patterns)} intent patterns")
        print("   - 100 pattern applications")
        print("   - 20 correction sessions")
        print("   - 50 user feedback entries")

    except Exception as e:
        print(f"❌ Error populating test data: {e}")
        conn.rollback()

    finally:
        conn.close()


if __name__ == "__main__":
    populate_test_data()
