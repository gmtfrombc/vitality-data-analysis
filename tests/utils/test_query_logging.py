import tempfile
import os


from app.utils import query_logging as ql


def test_log_interaction_creates_row():
    """log_interaction should insert a row into assistant_logs table."""
    # Use temporary DB file to avoid contamination
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        db_path = tmp.name

    try:
        # Ensure DB starts empty
        assert not os.path.exists(db_path) or os.path.getsize(db_path) == 0

        # Log a fake interaction
        ql.log_interaction(
            query="How many active patients?",
            intent={"analysis_type": "count", "metric": "patients"},
            generated_code="SELECT COUNT(*) FROM patients WHERE active = 1;",
            result="There are 42 active patients.",
            duration_ms=123,
            db_file=db_path,
        )

        # Verify row exists
        rows = ql.fetch_recent(limit=5, db_file=db_path)
        assert len(rows) == 1
        row = rows[0]
        assert row["query"] == "How many active patients?"
        assert row["duration_ms"] == 123
        # intent_json column should contain our analysis_type
        assert "count" in row["intent_json"]
    finally:
        os.unlink(db_path)
