"""Test suite for feedback database helpers."""

import os
import sqlite3
import tempfile

import pytest

from app.utils.feedback_db import insert_feedback, load_feedback
from app.utils.db_migrations import apply_pending_migrations


# Use a fresh temporary database for these tests to avoid side effects
@pytest.fixture
def temp_db():
    """Provide a temporary database file path that's initialized."""
    fd, path = tempfile.mkstemp(suffix=".db")
    try:
        # Close the file descriptor opened by mkstemp
        os.close(fd)
        apply_pending_migrations(path)
        yield path  # This is the value returned by the fixture
    finally:
        # Cleanup: remove the temp file when test is done
        os.unlink(path)


def test_insert_feedback_happy_path(temp_db):
    """Happy path: insert valid feedback record."""
    result = insert_feedback(
        question="What is the average BMI?",
        rating="up",
        comment="Very helpful!",
        db_file=temp_db,
    )
    assert result is True, "Insertion should succeed"

    # Verify it's in the database
    conn = sqlite3.connect(temp_db)
    count = conn.execute("SELECT COUNT(*) FROM assistant_feedback").fetchone()[0]
    conn.close()

    assert count == 1, "Should have exactly one record"


def test_insert_feedback_invalid_rating(temp_db):
    """Should fail if rating is not 'up' or 'down'."""
    with pytest.raises(ValueError):
        insert_feedback(
            question="What is the average BMI?",
            rating="neutral",  # Invalid - not up/down
            db_file=temp_db,
        )


def test_load_feedback_empty(temp_db):
    """Should return empty list when no feedback exists."""
    feedback = load_feedback(db_file=temp_db)
    assert feedback == [], "Should return empty list"


def test_load_feedback_with_data(temp_db):
    """Should return feedback records in reverse chronological order."""
    # Insert some records
    insert_feedback(question="First question", rating="up", db_file=temp_db)
    insert_feedback(
        question="Second question", rating="down", comment="Needs work", db_file=temp_db
    )

    # Load them back
    feedback = load_feedback(db_file=temp_db)

    # Verify
    assert len(feedback) == 2, "Should have 2 records"
    assert feedback[0]["question"] == "Second question"  # Most recent first
    assert feedback[0]["rating"] == "down"
    assert feedback[0]["comment"] == "Needs work"
    assert feedback[1]["question"] == "First question"
    assert feedback[1]["rating"] == "up"
    assert feedback[1]["comment"] is None
