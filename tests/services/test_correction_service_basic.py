"""
Basic tests for CorrectionService - Sprint 1 functionality.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path

from app.services.correction_service import CorrectionService
from app.utils.feedback_db import insert_feedback
from app.utils.db_migrations import apply_pending_migrations


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    try:
        Path(path).unlink()  # Remove the temp file so we can create a clean DB
        apply_pending_migrations(path)
        yield path
    finally:
        if Path(path).exists():
            Path(path).unlink()


@pytest.fixture
def correction_service(temp_db):
    """Create a correction service with test database."""
    return CorrectionService(db_path=temp_db)


class TestCorrectionServiceBasic:
    """Test basic CorrectionService functionality."""

    def test_init_creates_tables(self, temp_db):
        """Test that initializing service creates required tables."""
        service = CorrectionService(db_path=temp_db)

        # Check that tables exist
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()

            # Check correction_sessions table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='correction_sessions'"
            )
            assert cursor.fetchone() is not None

            # Check intent_patterns table
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='intent_patterns'"
            )
            assert cursor.fetchone() is not None

            # Check other tables...
            tables = ["code_templates", "learning_metrics", "query_similarity_cache"]
            for table in tables:
                cursor.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                )
                assert cursor.fetchone() is not None, f"Table {table} not found"

    def test_capture_correction_session(self, correction_service, temp_db):
        """Test capturing a correction session."""
        # First insert a feedback record
        insert_feedback(
            question="What is the average BMI?",
            rating="down",
            comment="Wrong calculation",
            db_file=temp_db,
        )

        # Get the feedback ID
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        # Capture correction session
        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="What is the average BMI?",
            human_correct_answer="The average BMI of active patients is 26.5",
            original_intent_json='{"analysis_type": "average", "target_field": "bmi"}',
            original_code="SELECT AVG(bmi) FROM vitals",
            original_results="{'average_bmi': 24.2}",
        )

        assert session_id is not None
        assert session_id > 0

    def test_get_correction_session(self, correction_service, temp_db):
        """Test retrieving a correction session."""
        # Insert feedback and correction session
        insert_feedback(question="Test query", rating="down", db_file=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="Test query",
            human_correct_answer="Test answer",
        )

        # Retrieve the session
        session = correction_service.get_correction_session(session_id)

        assert session is not None
        assert session.original_query == "Test query"
        assert session.human_correct_answer == "Test answer"
        assert session.status == "pending"

    def test_update_correction_session(self, correction_service, temp_db):
        """Test updating a correction session."""
        # Create a session
        insert_feedback(question="Test query", rating="down", db_file=temp_db)

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM assistant_feedback ORDER BY id DESC LIMIT 1")
            feedback_id = cursor.fetchone()[0]

        session_id = correction_service.capture_correction_session(
            feedback_id=feedback_id,
            original_query="Test query",
            human_correct_answer="Test answer",
        )

        # Update the session
        success = correction_service.update_correction_session(
            session_id, {"status": "integrated", "correction_type": "intent_fix"}
        )

        assert success

        # Verify the update
        session = correction_service.get_correction_session(session_id)
        assert session.status == "integrated"
        assert session.correction_type == "intent_fix"

    def test_nonexistent_session(self, correction_service):
        """Test handling of nonexistent sessions."""
        session = correction_service.get_correction_session(99999)
        assert session is None

        success = correction_service.update_correction_session(
            99999, {"status": "integrated"}
        )
        assert success is False
