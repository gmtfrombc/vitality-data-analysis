#!/usr/bin/env python3
"""
Debug script to test pattern matching similarity calculation.
"""

from app.utils.feedback_db import insert_feedback
from app.services.correction_service import CorrectionService
import sqlite3
import tempfile
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Create temp db
with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
    temp_db = f.name

print(f"Using temp db: {temp_db}")

# Create service
cs = CorrectionService(db_path=temp_db)

# Create feedback
insert_feedback(question="How many patients?", rating="down", db_file=temp_db)

# Get feedback ID
with sqlite3.connect(temp_db) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
    feedback_id = cursor.fetchone()[0]

print(f"Created feedback with ID: {feedback_id}")

# Create session
session_id = cs.capture_correction_session(
    feedback_id=feedback_id,
    original_query="How many patients?",
    human_correct_answer="Should count only active patients",
)

print(f"Created session with ID: {session_id}")

# Get session
session = cs.get_correction_session(session_id)
print(f"Retrieved session: {session}")

# Create suggestion
suggestion = {
    "action_type": "intent_modification",
    "corrected_intent": '{"analysis_type": "count", "target_field": "patients", "filters": [{"field": "active", "value": 1}]}',
    "type": "intent_fix",
}

print(f"Suggestion: {suggestion}")

# Learn from correction
cs._learn_from_correction(session, suggestion)

# Check patterns
patterns = cs.find_similar_patterns("how many patients")
print(f"Found {len(patterns)} patterns")

# Check database directly
with sqlite3.connect(temp_db) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM intent_patterns")
    rows = cursor.fetchall()
    print(f"Database has {len(rows)} patterns")
    for row in rows:
        print(f"Pattern ID: {row[0]}, Query Pattern: {row[1]}, Intent JSON: {row[2]}")
        print(f"Usage Count: {row[4]}, Success Rate: {row[5]}")

# Test normalization
normalized = cs._normalize_query("How many patients?")
print(f'Normalized query: "{normalized}"')

# Test normalization of search query
search_normalized = cs._normalize_query("how many patients")
print(f'Search normalized: "{search_normalized}"')

# Test similarity between the two
similarity = cs._calculate_query_similarity(normalized, search_normalized)
print(f'Similarity between "{normalized}" and "{search_normalized}": {similarity}')


def test_similarity_calculation():
    """Test the similarity calculation that's causing the weight/BMI mix-up."""
    print("=== Testing Similarity Calculation ===")

    cs = CorrectionService()

    # Test the exact case that's causing the issue
    query = "What is the average weight of patients?"
    pattern = "average bmi active patients"

    # Normalize both
    normalized_query = cs._normalize_query(query)
    print(f"Original query: '{query}'")
    print(f"Normalized query: '{normalized_query}'")
    print(f"Pattern: '{pattern}'")

    # Calculate similarity
    similarity = cs._calculate_query_similarity(normalized_query, pattern)
    print(f"Similarity: {similarity:.3f}")

    # Break down the calculation
    words1 = set(normalized_query.split())
    words2 = set(pattern.split())
    intersection = words1.intersection(words2)
    union = words1.union(words2)

    print(f"Query words: {words1}")
    print(f"Pattern words: {words2}")
    print(f"Intersection: {intersection} (count: {len(intersection)})")
    print(f"Union: {union} (count: {len(union)})")
    print(
        f"Similarity calculation: {len(intersection)}/{len(union)} = {similarity:.3f}"
    )

    # Test if this exceeds the threshold
    threshold = 0.3
    print(f"Threshold: {threshold}")
    print(f"Exceeds threshold: {similarity > threshold}")

    # Test with a correct weight pattern
    print("\n--- Testing with correct weight pattern ---")
    correct_pattern = "average weight patients"
    correct_similarity = cs._calculate_query_similarity(
        normalized_query, correct_pattern
    )
    print(f"Correct pattern: '{correct_pattern}'")
    print(f"Correct similarity: {correct_similarity:.3f}")

    # Test other problematic cases
    print("\n--- Testing other cases ---")
    test_cases = [
        ("What is the average BMI?", "average weight patients"),
        ("Show me patient weights", "average bmi active patients"),
        ("Average weight by gender", "average bmi active patients"),
    ]

    for test_query, test_pattern in test_cases:
        norm_query = cs._normalize_query(test_query)
        sim = cs._calculate_query_similarity(norm_query, test_pattern)
        print(
            f"'{test_query}' vs '{test_pattern}': {sim:.3f} ({'MATCH' if sim > threshold else 'NO MATCH'})"
        )


if __name__ == "__main__":
    test_similarity_calculation()
