"""
AI Assistant Page Component

This page provides an interface for generating SQL queries from natural language using OpenAI.
The OpenAI API key should be set as an environment variable named OPENAI_API_KEY or in a .env file.
"""

import param
import pandas as pd
from app.db_query import query_dataframe
import sys
import logging
from pathlib import Path
from app.config import OPENAI_API_KEY, DEBUG_MODE
from app.pages.ai_assistant_ui import build_assistant_view
from app.utils.query_state import (
    load_saved_queries,
    save_queries_to_file,
    add_or_update_query,
    delete_query,
)
from app.state import WorkflowState, WorkflowStages
import tempfile
import threading
import sqlite3
from etl.json_ingest import ingest as json_ingest
from app.utils.saved_questions_db import DB_FILE

print("AIAssistant module imported")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ai_assistant")

# Add the parent directory to path so we can import app.db_query
sys.path.append(str(Path(__file__).parent.parent.parent))

# Constants
# You can use "gpt-4" for better results if available
OPENAI_MODEL = "gpt-4o"

# Query examples by category
QUERY_EXAMPLES = {
    "Demographics": [
        "Show me all female patients over 65",
        "Find patients who are male between 40 and 50 years old",
        "List all patients with high engagement scores (>80)",
    ],
    "Lab Results": [
        "Find patients with A1C over 8 in their first lab test",
        "Show me female patients with high cholesterol (>240)",
        "List patients whose A1C improved by more than 1 point",
    ],
    "Vitals": [
        "Find patients with systolic BP over 140",
        "Show me patients who lost more than 10 pounds during the program",
        "List patients with BMI over 30 at program start",
    ],
    "Combined Queries": [
        "Find female patients over 50 with A1C over 9 and high blood pressure",
        "Show men with healthy BMI (18.5-24.9) and good heart fitness scores",
        "List patients who improved both A1C and blood pressure during the program",
    ],
}


class AIAssistant(param.Parameterized):
    """AI assistant for generating SQL queries from natural language"""

    query_text = param.String(default="")
    generated_sql = param.String(default="")
    status_message = param.String(default="")
    db_schema = param.String(default="")
    saved_queries = param.List(default=[])
    query_name = param.String(default="")
    results_updated = param.Event()  # Add an event parameter to trigger updates
    workflow_state = param.ClassSelector(
        class_=WorkflowState, default=None, doc="Workflow state manager"
    )
    clarifying_questions = param.List(default=[], doc="List of clarifying questions")
    clarification_response = param.String(
        default="", doc="User's clarification response"
    )

    def __init__(self, ui=None, llm_client=None, **params):
        print("AIAssistant __init__ called")
        super().__init__(**params)
        self.ui = ui
        self.result_data = pd.DataFrame()
        self.client = llm_client
        self.results_container = None  # Will be set during view() method
        self.workflow_state = WorkflowState()  # Initialize workflow state
        self._setup_workflow_watchers()

        # Set up logging level from environment variable
        if DEBUG_MODE:
            self._set_log_level(logging.DEBUG)
            logger.debug("Debug mode enabled")
        else:
            self._set_log_level(logging.INFO)

        # Get API key from environment variable
        self.api_key = OPENAI_API_KEY
        if self.client is None and self.api_key:
            self.init_client()
            logger.info("API key found in environment variables")
        elif not self.api_key:
            self.status_message = "OPENAI_API_KEY environment variable not set. Please set it to use AI assistant."
            logger.warning("OPENAI_API_KEY environment variable not set")
            if self.ui:
                self.ui.update_status(self.status_message, type="warning")

        # Get database schema information
        self._load_db_schema()

        # Load saved queries
        self.refresh_saved_queries()
        print(f"[__init__] After refresh_saved_queries: {self.saved_queries}")

    def init_client(self):
        """Initialize the OpenAI client"""
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=self.api_key)
            self.status_message = "OpenAI client initialized successfully"
            logger.info("OpenAI client initialized successfully")
            if self.ui:
                self.ui.update_status(self.status_message, type="success")
        except Exception as e:
            self.status_message = f"Error initializing OpenAI client: {str(e)}"
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.client = None
            if self.ui:
                self.ui.update_status(self.status_message, type="error")

    def _load_db_schema(self):
        """Load database schema information to provide context for AI"""
        try:
            # Get tables information
            tables_info = query_dataframe(
                "SELECT name FROM sqlite_master WHERE type='table';"
            )

            schema_info = []
            table_details = {}  # Store detailed table info for validation

            # Get columns for each table
            for table in tables_info["name"]:
                try:
                    columns_info = query_dataframe(f"PRAGMA table_info({table});")
                    columns_str = ", ".join(
                        [
                            f"{row['name']} ({row['type']})"
                            for _, row in columns_info.iterrows()
                        ]
                    )
                    schema_info.append(f"Table: {table}\nColumns: {columns_str}\n")

                    # Store column details for validation
                    table_details[table.lower()] = {
                        "columns": [
                            row["name"].lower() for _, row in columns_info.iterrows()
                        ],
                        "column_types": {
                            row["name"].lower(): row["type"]
                            for _, row in columns_info.iterrows()
                        },
                    }

                except Exception as e:
                    logger.error(f"Error getting columns for table {table}: {str(e)}")

            self.db_schema = "\n".join(schema_info)
            # Store table details for validation
            self.table_details = table_details
            logger.info(f"Loaded schema for {len(tables_info)} tables")

            # Generate table relationship information
            self._extract_table_relationships()

        except Exception as e:
            logger.error(f"Error loading database schema: {str(e)}")
            self.db_schema = f"Error loading schema: {str(e)}"
            self.table_details = {}

    def _extract_table_relationships(self):
        """Extract table relationships from foreign keys"""
        try:
            relationships = []
            for table_name in self.table_details.keys():
                # Get foreign keys for the table
                fk_info = query_dataframe(f"PRAGMA foreign_key_list({table_name});")

                if not fk_info.empty:
                    for _, row in fk_info.iterrows():
                        ref_table = row.get("table", "")
                        from_col = row.get("from", "")
                        to_col = row.get("to", "")
                        if ref_table and from_col and to_col:
                            relationships.append(
                                f"Table '{table_name}' has foreign key '{from_col}' referencing '{ref_table}({to_col})'"
                            )

            self.table_relationships = relationships
            logger.info(f"Extracted {len(relationships)} table relationships")
        except Exception as e:
            logger.error(f"Error extracting table relationships: {str(e)}")
            self.table_relationships = []

    def refresh_saved_queries(self):
        """Reload saved queries from storage and update the parameter (triggers UI refresh)."""
        self.saved_queries = load_saved_queries()
        print(
            f"[refresh_saved_queries] Loaded {len(self.saved_queries)} saved queries: {self.saved_queries}"
        )

    def _save_queries_to_file(self):
        save_queries_to_file(self.saved_queries)

    def _add_or_update_query(self, new_query):
        self.saved_queries = add_or_update_query(self.saved_queries, new_query)
        self._save_queries_to_file()
        self.refresh_saved_queries()
        print(f"[_add_or_update_query] After refresh: {self.saved_queries}")

    def _delete_query(self, name):
        self.saved_queries = delete_query(self.saved_queries, name)
        self._save_queries_to_file()
        self.refresh_saved_queries()
        print(f"[_delete_query] After refresh: {self.saved_queries}")

    def _set_log_level(self, level=logging.INFO):
        """Set the logging level for the AI assistant module"""
        logger.setLevel(level)

        # Remove all existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add a fresh handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.info(f"Logging level set to {level}")

    def generate_sql(self, event=None):
        """Stub: Generate SQL from the current query_text. For now, just set a placeholder and print a message."""
        print("[generate_sql] called")
        self.generated_sql = "-- SQL generation not yet implemented --"
        self.status_message = "SQL generated (stub)."

    def _save_query(self, event=None):
        print("[_save_query] called")
        self.status_message = "Save query stub called."

    def _setup_workflow_watchers(self):
        # Watch for workflow state changes and log them
        def log_stage(event):
            logger.info(f"Workflow stage changed: {event.old} -> {event.new}")
            print(f"[Workflow] Stage changed: {event.old} -> {event.new}")

        self.workflow_state.param.watch(log_stage, "current_stage")

    def check_for_clarification(self, query):
        # Simple keyword-based ambiguity check
        ambiguous_keywords = ["unclear", "ambiguous", "not sure", "unsure", "confusing"]
        if any(word in query.lower() for word in ambiguous_keywords):
            self.clarifying_questions = [
                "Can you clarify what you mean?",
                "Please provide more details about your request.",
            ]
            print(
                "[Clarification] Ambiguity detected, triggering clarification workflow."
            )
            logger.info("Clarification triggered for query: %s", query)
            return True
        print("[Clarification] No ambiguity detected.")
        logger.info("No clarification needed for query: %s", query)
        return False

    def start_workflow(self, query):
        self.workflow_state.start_query(query)
        logger.info(f"Workflow started for query: {query}")
        print(f"[Workflow] Started for query: {query}")
        # Check for clarification need
        if self.check_for_clarification(query):
            self.workflow_state.current_stage = WorkflowStages.CLARIFYING
            print("[Workflow] Entered clarification stage.")
            logger.info("Entered clarification stage.")
        else:
            self.workflow_state.mark_intent_parsed(needs_clarification=False)
            print("[Workflow] Skipping clarification, proceeding to code generation.")
            logger.info("Skipping clarification, proceeding to code generation.")

    def submit_clarification(self, response):
        self.clarification_response = response
        print(f"[Clarification] User submitted clarification: {response}")
        logger.info(f"User submitted clarification: {response}")
        self.workflow_state.mark_clarification_complete()
        print("[Workflow] Clarification complete, proceeding to code generation.")
        logger.info("Clarification complete, proceeding to code generation.")

    def continue_workflow(self):
        current = self.workflow_state.current_stage
        if current == WorkflowStages.INITIAL:
            self.workflow_state.mark_intent_parsed(needs_clarification=False)
        elif current == WorkflowStages.CLARIFYING:
            # Should not auto-advance; wait for user to submit clarification
            print("[Workflow] Waiting for user clarification input.")
            logger.info("Waiting for user clarification input.")
            return
        elif current == WorkflowStages.CODE_GENERATION:
            self.workflow_state.mark_code_generated()
        elif current == WorkflowStages.EXECUTION:
            self.workflow_state.mark_execution_complete()
        elif current == WorkflowStages.RESULTS:
            self.workflow_state.mark_results_displayed()
        logger.info(f"Workflow continued to stage: {self.workflow_state.current_stage}")
        print(f"[Workflow] Continued to stage: {self.workflow_state.current_stage}")

    def _use_example(self, example):
        # For UI: set query_text and start workflow
        self.query_text = example
        self.start_workflow(example)
        self.status_message = f"Example loaded: {example}"
        logger.info(f"Example used: {example}")
        print(f"[Workflow] Example used: {example}")

    def import_json_data(self, file_bytes, status_callback):
        """Import JSON data using the ETL pipeline in a background thread."""

        def _worker():
            status_callback("Starting import...", "info")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                    tmp.write(file_bytes)
                    tmp_path = Path(tmp.name)
                status_callback("File uploaded. Running import...", "info")
                counts = json_ingest(tmp_path)
                summary = ", ".join(f"{k}: {v}" for k, v in counts.items())
                status_callback(f"Import complete – {summary}", "success")
            except Exception as exc:
                status_callback(f"Import failed: {exc}", "error")
            finally:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

    def reset_mock_patients(self, status_callback):
        """Remove mock/demo patients from the database in a background thread."""

        def _worker():
            status_callback("Resetting mock patients...", "info")
            patient_ids = ["p100", "p101", "p102"]
            try:
                conn = sqlite3.connect(str(DB_FILE))
                with conn:
                    for tbl, col in [
                        ("vitals", "patient_id"),
                        ("scores", "patient_id"),
                        ("mental_health", "patient_id"),
                        ("lab_results", "patient_id"),
                        ("pmh", "patient_id"),
                        ("patients", "id"),
                    ]:
                        placeholders = ",".join(["?"] * len(patient_ids))
                        conn.execute(
                            f"DELETE FROM {tbl} WHERE {col} IN ({placeholders})",
                            patient_ids,
                        )
                status_callback("Mock patients removed.", "success")
            except Exception as exc:
                status_callback(f"Delete failed: {exc}", "error")

        threading.Thread(target=_worker, daemon=True).start()


def ai_assistant_page():
    print("ai_assistant_page factory called")
    ai_assistant = AIAssistant()
    return build_assistant_view(ai_assistant)
