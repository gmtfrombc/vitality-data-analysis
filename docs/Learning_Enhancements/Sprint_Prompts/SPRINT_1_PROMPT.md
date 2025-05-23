# SPRINT 1 PROMPT - Database Foundation & Basic Service

## PROJECT CONTEXT

You are working on the **AAA Learning Enhancements Project** - adding automated learning capabilities to the Ask Anything AI Assistant (AAA). This is Sprint 1 of a 5-sprint project.

### Project Overview
The AAA is a healthcare data analysis assistant that converts natural language queries to SQL. Currently, when users get incorrect answers, they must manually fix them. We're building an automated learning system that:
1. Captures user corrections when they provide feedback
2. Analyzes error patterns and suggests fixes  
3. Learns from corrections to improve future responses
4. Routes similar queries to learned patterns

### Current System Status
The AAA already has:
- **Working feedback system**: `app/utils/feedback_db.py` (thumbs up/down)
- **Saved questions**: `app/utils/saved_questions_db.py` (SQLite storage)
- **Query processing**: `app/engine.py` (NL to SQL pipeline)
- **Database migrations**: `app/utils/db_migrations.py`
- **Panel UI framework**: Working interface with workflow management

## SPRINT 1 OBJECTIVES

**Goal**: Establish the database foundation and basic correction service infrastructure for the learning system.

**Key Deliverables**:
1. Database schema with 5 new tables for learning system
2. Basic CorrectionService class for managing correction sessions
3. Data models for correction tracking
4. Database migration framework integration
5. Basic tests to ensure functionality

**User Impact**: None (backend only) - all existing functionality remains unchanged.

## TECHNICAL REQUIREMENTS

### Database Schema to Create

Create `migrations/009_correction_learning_tables.sql` with these tables:

```sql
-- Extended correction sessions for detailed tracking
CREATE TABLE IF NOT EXISTS correction_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER,
    original_query TEXT NOT NULL,
    original_intent_json TEXT,
    original_code TEXT,
    original_results TEXT,
    human_correct_answer TEXT,
    correction_type TEXT CHECK(correction_type IN ('intent_fix', 'code_fix', 'logic_fix', 'data_fix')),
    error_category TEXT, -- 'ambiguous_intent', 'wrong_aggregation', 'missing_filter', etc.
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'integrated', 'validated', 'rejected')),
    reviewed_by TEXT,
    reviewed_at TEXT,
    FOREIGN KEY (feedback_id) REFERENCES assistant_feedback(id)
);

-- Intent patterns learned from corrections
CREATE TABLE IF NOT EXISTS intent_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_pattern TEXT NOT NULL,
    canonical_intent_json TEXT NOT NULL,
    confidence_boost REAL DEFAULT 0.1,
    usage_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 1.0,
    created_from_session_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_used_at TEXT,
    FOREIGN KEY (created_from_session_id) REFERENCES correction_sessions(id)
);

-- Code templates for deterministic generation
CREATE TABLE IF NOT EXISTS code_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_signature TEXT NOT NULL, -- JSON schema pattern for intent matching
    template_code TEXT NOT NULL,
    template_description TEXT,
    success_rate REAL DEFAULT 1.0,
    usage_count INTEGER DEFAULT 0,
    created_from_session_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_used_at TEXT,
    FOREIGN KEY (created_from_session_id) REFERENCES correction_sessions(id)
);

-- Query similarity cache for faster pattern matching
CREATE TABLE IF NOT EXISTS query_similarity_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT NOT NULL UNIQUE, -- Hash of normalized query
    similar_patterns TEXT, -- JSON array of similar pattern IDs
    computed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Performance metrics for learning system
CREATE TABLE IF NOT EXISTS learning_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_date DATE NOT NULL,
    total_queries INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    pattern_matches INTEGER DEFAULT 0,
    template_matches INTEGER DEFAULT 0,
    correction_applied INTEGER DEFAULT 0,
    accuracy_rate REAL DEFAULT 0.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_correction_sessions_feedback_id ON correction_sessions(feedback_id);
CREATE INDEX IF NOT EXISTS idx_correction_sessions_status ON correction_sessions(status);
CREATE INDEX IF NOT EXISTS idx_intent_patterns_usage_count ON intent_patterns(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_code_templates_usage_count ON code_templates(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_query_similarity_cache_hash ON query_similarity_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_learning_metrics_date ON learning_metrics(metric_date DESC);
```

### Basic Correction Service

Create `app/services/correction_service.py`:

```python
"""
Correction Service for AAA Learning System

This service handles the capture, analysis, and integration of user corrections
to continuously improve the Ask Anything AI Assistant's accuracy.

Key Features (Sprint 1 - Basic):
- Captures correction sessions when users provide feedback
- Stores correction data in database
- Provides basic retrieval and update functionality
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

from app.utils.saved_questions_db import DB_FILE
from app.utils.db_migrations import apply_pending_migrations

logger = logging.getLogger(__name__)


@dataclass
class CorrectionSession:
    """Represents a correction session with all relevant data."""
    id: Optional[int] = None
    feedback_id: Optional[int] = None
    original_query: str = ""
    original_intent_json: Optional[str] = None
    original_code: Optional[str] = None
    original_results: Optional[str] = None
    human_correct_answer: str = ""
    correction_type: Optional[str] = None
    error_category: Optional[str] = None
    status: str = "pending"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None


@dataclass 
class IntentPattern:
    """Represents a learned intent pattern."""
    id: Optional[int] = None
    query_pattern: str = ""
    canonical_intent_json: str = ""
    confidence_boost: float = 0.1
    usage_count: int = 0
    success_rate: float = 1.0


class CorrectionService:
    """Main service for handling corrections and learning."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the correction service.
        
        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Ensure all required tables exist."""
        try:
            apply_pending_migrations(self.db_path)
        except Exception as e:
            logger.error(f"Failed to apply migrations: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def capture_correction_session(
        self, 
        feedback_id: int,
        original_query: str,
        human_correct_answer: str,
        original_intent_json: Optional[str] = None,
        original_code: Optional[str] = None,
        original_results: Optional[str] = None
    ) -> int:
        """Capture a new correction session.
        
        Args:
            feedback_id: ID from assistant_feedback table
            original_query: The original user query
            human_correct_answer: The correct answer provided by human
            original_intent_json: The original parsed intent (if available)
            original_code: The original generated code (if available)
            original_results: The original results (if available)
            
        Returns:
            The ID of the created correction session
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO correction_sessions 
                (feedback_id, original_query, original_intent_json, original_code, 
                 original_results, human_correct_answer, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """, (
                feedback_id, original_query, original_intent_json, 
                original_code, original_results, human_correct_answer
            ))
            session_id = cursor.lastrowid
            logger.info(f"Created correction session {session_id} for feedback {feedback_id}")
            return session_id
    
    def get_correction_session(self, session_id: int) -> Optional[CorrectionSession]:
        """Get a correction session by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM correction_sessions WHERE id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if row:
                return CorrectionSession(
                    id=row["id"],
                    feedback_id=row["feedback_id"],
                    original_query=row["original_query"],
                    original_intent_json=row["original_intent_json"],
                    original_code=row["original_code"],
                    original_results=row["original_results"],
                    human_correct_answer=row["human_correct_answer"],
                    correction_type=row["correction_type"],
                    error_category=row["error_category"],
                    status=row["status"],
                    reviewed_by=row["reviewed_by"],
                    reviewed_at=row["reviewed_at"]
                )
            return None
    
    def update_correction_session(self, session_id: int, updates: Dict[str, any]) -> bool:
        """Update a correction session."""
        if not updates:
            return False
            
        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [session_id]
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    UPDATE correction_sessions 
                    SET {set_clause}
                    WHERE id = ?
                """, values)
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to update correction session {session_id}: {e}")
            return False
```

### Required Directory Structure

Ensure these directories exist:
```
app/services/
app/services/__init__.py
tests/services/
tests/services/__init__.py
```

### Testing Requirements

Create `tests/services/test_correction_service_basic.py`:

```python
"""
Basic tests for CorrectionService - Sprint 1 functionality.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path

from app.services.correction_service import CorrectionService, CorrectionSession
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
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='correction_sessions'")
            assert cursor.fetchone() is not None
            
            # Check intent_patterns table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='intent_patterns'")
            assert cursor.fetchone() is not None
            
            # Check other tables...
            tables = ['code_templates', 'learning_metrics', 'query_similarity_cache']
            for table in tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                assert cursor.fetchone() is not None, f"Table {table} not found"
    
    def test_capture_correction_session(self, correction_service, temp_db):
        """Test capturing a correction session."""
        # First insert a feedback record
        insert_feedback(
            question="What is the average BMI?",
            rating="down",
            comment="Wrong calculation",
            db_file=temp_db
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
            original_results="{'average_bmi': 24.2}"
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
            human_correct_answer="Test answer"
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
            human_correct_answer="Test answer"
        )
        
        # Update the session
        success = correction_service.update_correction_session(session_id, {
            "status": "integrated",
            "correction_type": "intent_fix"
        })
        
        assert success
        
        # Verify the update
        session = correction_service.get_correction_session(session_id)
        assert session.status == "integrated"
        assert session.correction_type == "intent_fix"
    
    def test_nonexistent_session(self, correction_service):
        """Test handling of nonexistent sessions."""
        session = correction_service.get_correction_session(99999)
        assert session is None
        
        success = correction_service.update_correction_session(99999, {"status": "integrated"})
        assert success is False
```

## FILES TO CREATE/MODIFY

### Files to Create
```
migrations/009_correction_learning_tables.sql
app/services/__init__.py
app/services/correction_service.py
tests/services/__init__.py
tests/services/test_correction_service_basic.py
```

### Files to Modify
- None (this sprint is purely additive)

## SUCCESS CRITERIA

You are done when:
- [ ] Migration file `009_correction_learning_tables.sql` creates all 5 tables with proper schema
- [ ] `CorrectionService` class can store and retrieve correction sessions
- [ ] All database tables have proper indexes and constraints  
- [ ] Basic tests pass and verify core functionality
- [ ] No existing functionality is broken
- [ ] Database migration runs successfully
- [ ] Code follows existing project patterns and style

## DEVELOPMENT WORKFLOW

1. **Create the migration file first** - This establishes the database foundation
2. **Run the migration** - Test that tables are created properly
3. **Create the services directory structure** if it doesn't exist
4. **Implement the CorrectionService** - Start with basic functionality only
5. **Create comprehensive tests** - Verify all basic operations work
6. **Run all tests** - Ensure no breaking changes to existing code

## TESTING & GITHUB WORKFLOW

After completing the implementation:

1. **Run the full test suite**:
   ```bash
   pytest tests/ -v
   pytest tests/services/test_correction_service_basic.py -v
   ```

2. **Run the migration manually to verify**:
   ```bash
   python -c "from app.utils.db_migrations import apply_pending_migrations; apply_pending_migrations('patient_data.db')"
   ```

3. **Verify no breaking changes**:
   ```bash
   python run.py  # Start the app and verify existing functionality works
   ```

4. **Commit and push changes**:
**IMPORTANT** For all commit and push changes, we are using black and ruff. Create one commmand to perform the add/commit/push rather than separate commands. Below are the single commands--your task is to generate one command (no other text) in your workspace.
   ```bash
   git add .
   git commit -m "Sprint 1: Add database foundation and basic correction service

   - Add migration 009 with 5 new tables for learning system
   - Implement basic CorrectionService for correction session management
   - Add data models for CorrectionSession and IntentPattern
   - Create comprehensive tests for basic functionality
   - All existing functionality remains unchanged"
   
   git push origin main
   ```

## IMPORTANT NOTES

- **Backward Compatibility**: All existing functionality must continue to work unchanged
- **Error Handling**: Add proper error handling and logging throughout
- **Database Safety**: Use transactions and proper SQL practices
- **Code Style**: Follow existing project conventions and naming patterns
- **Testing**: Write tests before implementing complex logic
- **Documentation**: Add docstrings to all public methods

## WHEN YOU'RE STUCK

If you encounter any ambiguous situations or need clarification:
1. **Continue with the most conservative approach** that maintains backward compatibility
2. **Add TODO comments** for any decisions that need human review
3. **Prioritize working, tested code** over perfect implementation
4. **Document your assumptions** in comments

The goal is a solid foundation that future sprints can build upon safely.

---

**START IMPLEMENTING SPRINT 1 NOW** 