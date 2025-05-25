import tempfile
import sqlite3
from app.services.correction_service import CorrectionService
from app.utils.feedback_db import insert_feedback

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
