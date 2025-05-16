"""
Data Analysis Assistant

Coordinator module that uses the UI, Engine, Analysis, and State modules to provide
a complete data analysis assistant experience.
"""

import logging
import os
import panel as pn
import param
from pathlib import Path

from app.ui import UIComponents
from app.engine import AnalysisEngine
from app.analysis_helpers import (
    format_results,
)
from app.state import WorkflowState, WorkflowStages
from app.utils.feedback_db import insert_feedback
from app.utils.saved_questions_db import (
    load_saved_questions as _load_saved_questions_db,
    upsert_question,
)
from app.utils.query_intent import QueryIntent

# Define exports
__all__ = ["DataAnalysisAssistant", "data_assistant_page"]

# Configure logging
logger = logging.getLogger("data_assistant")

# Panel extensions
pn.extension("tabulator")
pn.extension("plotly")


class DataAnalysisAssistant(param.Parameterized):
    """Data Analysis Assistant with AI-powered data analysis capabilities"""

    query_text = param.String(default="", doc="Natural language query")
    analysis_result = param.Dict(default={})
    question_name = param.String(default="", doc="Name for saving the current query")
    saved_questions = param.List(default=[], doc="List of saved questions")
    show_narrative = param.Boolean(
        default=True, doc="Whether to show narrative summary"
    )

    def __init__(self, **params):
        """Initialize the data analysis assistant"""
        super().__init__(**params)

        # Initialize components
        self.ui = UIComponents()
        self.engine = AnalysisEngine()
        self.workflow = WorkflowState()

        # Initialize feedback component
        self.feedback_widget = None

        # Load saved questions
        self.saved_questions = _load_saved_questions_db()

        # Initialize UI components
        self._initialize_ui()

    def _initialize_ui(self):
        """Initialize UI components and connect event handlers"""
        # Set up query input watcher
        self.ui.query_input.param.watch(self._update_query_text, "value")

        # Set up analyze button
        analyze_button = pn.widgets.Button(
            name="Analyze", button_type="primary", sizing_mode="fixed", width=100
        )
        analyze_button.on_click(self._on_analyze_click)
        self.analyze_button = analyze_button

        # Set up continue button
        self.ui.continue_button.on_click(self._advance_workflow)

        # Set up save question components
        self.ui.save_question_input.param.watch(self._update_question_name, "value")
        save_button = pn.widgets.Button(
            name="Save Question", button_type="success", width=120
        )
        save_button.on_click(self._save_question)
        self.save_button = save_button

        # Set up reset button
        self.ui.reset_button.on_click(self._reset_all)

        # Set up narrative toggle
        self.ui._show_narrative_checkbox.param.watch(
            self._update_display_after_toggle, "value"
        )

        # Set up saved questions buttons
        self._update_saved_question_buttons()

        # Set up import panel components
        file_input = self.ui.import_panel[1]
        import_button = self.ui.import_panel[2]
        file_input.param.watch(self._toggle_import_button, "value")
        import_button.on_click(self._on_import_click)

        # Set up delete mock panel
        delete_button = self.ui.delete_mock_panel[1]
        delete_button.on_click(self._delete_mock)

    def _update_query_text(self, event):
        """Update query text when input changes"""
        self.query_text = event.new
        logger.info(f"Query text updated to: {self.query_text}")

    def _update_question_name(self, event):
        """Update question name when input changes"""
        self.question_name = event.new

    def _on_analyze_click(self, event):
        """Handle analyze button click"""
        logger.info(f"Analyze button clicked with query: {self.query_text}")

        # Reset workflow and start from the beginning
        self.workflow.reset()
        self.ui.update_stage_indicators(self.workflow.current_stage)

        # Process the query
        self._process_query()

    def _toggle_import_button(self, event):
        """Enable/disable import button based on file selection"""
        # Get the file input and import button from the import panel
        file_input = self.ui.import_panel[1]
        import_button = self.ui.import_panel[2]

        # Enable button only when a file is selected
        import_button.disabled = file_input.value is None or len(file_input.value) == 0

    def _on_import_click(self, event):
        """Handle import button click"""
        # Get the file input from the import panel
        file_input = self.ui.import_panel[1]

        if file_input.value is None or len(file_input.value) == 0:
            self.ui.update_status("No file selected")
            return

        # Create a temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp:
            temp_path = Path(temp.name)
            temp.write(file_input.value)

        # Process the import in a separate thread
        import threading

        def _worker(path):
            try:
                # Import data
                from etl.json_ingest import ingest

                success = ingest(str(path))

                # Update status based on result
                if success:
                    self.ui.update_status("Data imported successfully")
                else:
                    self.ui.update_status("Import failed")

                # Clean up temporary file
                try:
                    path.unlink()
                except Exception as e:
                    logger.error(f"Error deleting temp file: {e}")

                # Reset file input
                file_input.value = None

            except Exception as e:
                logger.error(f"Import error: {e}", exc_info=True)
                self.ui.update_status(f"Import error: {str(e)}")

        # Start import thread
        thread = threading.Thread(target=_worker, args=(temp_path,))
        thread.daemon = True
        thread.start()

        # Update status
        self.ui.update_status("Importing data...")

    def _delete_mock(self, event):
        """Handle delete mock button click"""
        # Update status
        self.ui.update_status("Regenerating mock data...")

        # Process in a separate thread
        import threading

        def _worker():
            try:
                # Delete existing database
                db_path = Path("patient_data.db")
                mock_path = Path("mock_patient_data.db")

                if db_path.exists():
                    db_path.unlink()

                if mock_path.exists():
                    mock_path.unlink()

                # Regenerate mock data
                import sys
                import subprocess

                # Get Python executable
                python_exe = sys.executable

                # Run the generate_test_database.py script
                cmd = [python_exe, "scripts/dev/generate_test_database.py"]
                process = subprocess.run(cmd, capture_output=True, text=True)

                if process.returncode == 0:
                    self.ui.update_status("Mock data regenerated successfully")
                else:
                    error = process.stderr or "Unknown error"
                    self.ui.update_status(f"Error regenerating mock data: {error}")

            except Exception as e:
                logger.error(f"Error regenerating mock data: {e}", exc_info=True)
                self.ui.update_status(f"Error regenerating mock data: {str(e)}")

        # Start thread
        thread = threading.Thread(target=_worker)
        thread.daemon = True
        thread.start()

    def _update_display_after_toggle(self, *_):
        """Update display when narrative toggle changes"""
        self.show_narrative = self.ui._show_narrative_checkbox.value
        self._display_final_results()

    def _process_query(self):
        """Process the natural language query"""
        # Validate query
        if not self.query_text:
            self.ui.update_status("Please enter a query")
            return

        # Start AI indicator
        self.ui.start_ai_indicator("AI is analyzing your query...")

        # Process the query using the engine
        self.workflow.start_query(self.query_text)
        intent = self.engine.process_query(self.query_text)

        # Check if intent needs clarification
        needs_clarification = self._is_truly_ambiguous_query(intent)
        self.workflow.mark_intent_parsed(needs_clarification)

        # Update UI based on workflow state
        self._process_current_stage()

    def _is_truly_ambiguous_query(self, intent):
        """Return True only when the query is genuinely ambiguous and requires clarification."""
        # In offline/test mode we skip clarification to keep smoke tests fast
        if not os.getenv("OPENAI_API_KEY"):
            return False

        # If parsing failed → truly ambiguous
        if isinstance(intent, dict):
            return True

        assert isinstance(intent, QueryIntent)

        # Check if the query is entirely unclear about what metric or analysis is wanted
        if intent.analysis_type == "unknown" and intent.target_field == "unknown":
            return True

        # Check if multiple interpretations are equally valid (critical ambiguity)
        raw_query = getattr(intent, "raw_query", "").lower()
        if not raw_query:
            return False

        # Ambiguous queries with multiple possible valid interpretations
        ambiguous_patterns = [
            "compare",
            "between",
            "versus",
            "vs",
            "which",
            "better",
            "best",
            "correlation",
            "relationship between",
        ]

        # If query contains ambiguous patterns but doesn't specify what to compare
        has_ambiguous_pattern = any(
            pattern in raw_query for pattern in ambiguous_patterns
        )
        has_unclear_targets = (
            not intent.additional_fields and intent.target_field == "unknown"
        )

        if has_ambiguous_pattern and has_unclear_targets:
            return True

        # Default to not asking questions
        return False

    def _process_current_stage(self):
        """Process the current workflow stage"""
        current_stage = self.workflow.current_stage

        # Update stage indicators
        self.ui.update_stage_indicators(current_stage)

        # Handle each stage
        if current_stage == WorkflowStages.INITIAL:
            # Initial stage - nothing to do
            pass

        elif current_stage == WorkflowStages.CLARIFYING:
            # Clarification stage
            self._display_clarifying_questions()

        elif current_stage == WorkflowStages.CODE_GENERATION:
            # Code generation stage
            self._generate_analysis_code()

        elif current_stage == WorkflowStages.EXECUTION:
            # Execution stage
            self._execute_analysis()

        elif current_stage == WorkflowStages.RESULTS:
            # Results stage
            self._display_final_results()

    def _display_clarifying_questions(self):
        """Display clarifying questions to the user"""
        # Generate clarifying questions
        questions = self.engine.generate_clarifying_questions()

        # Create the clarifying questions UI using the UI component
        self.ui.display_clarifying_questions(questions, self._process_clarification)

        # Update status
        self.ui.update_status("Please answer the clarifying questions")

        # Stop AI indicator
        self.ui.stop_ai_indicator()

    def _process_clarification(self, clarification_text):
        """Process the clarification response"""
        if not clarification_text:
            self.ui.update_status("Please provide clarification")
            return

        # Start AI indicator
        self.ui.start_ai_indicator("Processing your clarification...")

        # Process the clarification
        self.engine.process_clarification(clarification_text)

        # Mark clarification complete
        self.workflow.mark_clarification_complete()

        # Update UI
        self.ui.clarifying_pane.visible = False
        self._process_current_stage()

    def _generate_analysis_code(self):
        """Generate analysis code based on intent"""
        # Start AI indicator
        self.ui.start_ai_indicator("Generating analysis code...")

        # Generate code
        self.engine.generate_analysis_code()

        # Display generated code
        self._display_generated_code()

        # Mark code generated
        self.workflow.mark_code_generated()

        # Process next stage
        self._process_current_stage()

    def _display_generated_code(self):
        """Display the generated code"""
        # Update code display using the UI component
        self.ui.display_generated_code(self.engine.generated_code)

        # Update status
        self.ui.update_status("Analysis code generated")

    def _execute_analysis(self):
        """Execute the generated analysis code"""
        # Start AI indicator
        self.ui.start_ai_indicator("Executing analysis...")

        # Execute code
        results = self.engine.execute_analysis()

        # Display execution results
        self._display_execution_results()

        # Mark execution complete
        self.workflow.mark_execution_complete()

        # Process next stage
        self._process_current_stage()

    def _display_execution_results(self):
        """Display execution results"""
        # Use the UI component to display results
        self.ui.display_execution_results(
            self.engine.execution_results, self.engine.visualizations
        )

        # Update status
        self.ui.update_status("Analysis executed successfully")

        # Stop AI indicator
        self.ui.stop_ai_indicator()

    def _display_final_results(self):
        """Display final formatted results with visualizations"""
        # Format results
        formatted_results = format_results(
            self.engine.execution_results, self.engine.intent, self.show_narrative
        )

        # Add refine option
        formatted_results = self.ui.add_refine_option(
            formatted_results, self._process_refinement
        )

        # Update result container
        self.ui.result_container.objects = formatted_results

        # Create feedback widget if not exists
        if self.feedback_widget is None:
            self.feedback_widget = self.ui.create_feedback_widget()
            self._feedback_up = self.ui._feedback_up
            self._feedback_down = self.ui._feedback_down
            self._feedback_thanks = self.ui._feedback_thanks

            # Connect feedback handlers
            self._feedback_up.on_click(self._on_feedback_up)
            self._feedback_down.on_click(self._on_feedback_down)

        # Make feedback buttons visible
        self._feedback_up.visible = True
        self._feedback_down.visible = True
        self._feedback_thanks.visible = False

        # Add feedback widget to results
        if self.feedback_widget not in self.ui.result_container.objects:
            self.ui.result_container.objects.append(self.feedback_widget)

        # Mark results displayed
        self.workflow.mark_results_displayed()

        # Update status
        self.ui.update_status("Analysis completed")

    def _process_refinement(self, refinement_text):
        """Process refinement query"""
        if not refinement_text:
            self.ui.update_status("Please enter refinement details")
            return

        # Combine original query with refinement
        combined_query = f"{self.query_text}\n\nAdditional details: {refinement_text}"
        self.query_text = combined_query

        # Update query input
        self.ui.query_input.value = combined_query

        # Reset workflow and start from the beginning
        self.workflow.reset()
        self.ui.update_stage_indicators(self.workflow.current_stage)

        # Process the query
        self._process_query()

    def _advance_workflow(self, event=None):
        """Advance to the next workflow stage"""
        current_stage = self.workflow.current_stage
        next_stage = current_stage + 1

        # Check if we can transition to the next stage
        if not self.workflow.can_transition_to(next_stage):
            logger.warning(f"Cannot advance from stage {current_stage} to {next_stage}")
            return

        # Transition to the next stage
        self.workflow.transition_to(next_stage)

        # Process the new stage
        self._process_current_stage()

    def _save_question(self, event=None):
        """Save the current question"""
        if not self.query_text:
            self.ui.update_status("No query to save")
            return

        # Use default name if not provided
        name = self.question_name
        if not name:
            name = (
                self.query_text[:30] + "..."
                if len(self.query_text) > 30
                else self.query_text
            )

        # Save the question
        question = {"name": name, "query": self.query_text}
        success = upsert_question(name, self.query_text)

        if success:
            self.ui.update_status(f"Question saved: {name}")

            # Reload saved questions
            self.saved_questions = _load_saved_questions_db()

            # Update saved question buttons
            self._update_saved_question_buttons()

            # Clear question name
            self.question_name = ""
            self.ui.save_question_input.value = ""
        else:
            self.ui.update_status("Error saving question")

    def _update_saved_question_buttons(self):
        """Update saved question buttons"""
        buttons = []

        for q in self.saved_questions:
            # Create button for each saved question
            btn = pn.widgets.Button(
                name=q["name"],
                button_type="light",
                sizing_mode="stretch_width",
            )

            # Create click handler
            def make_click_handler(q):
                def on_click(event):
                    self._use_example_query(q)

                return on_click

            btn.on_click(make_click_handler(q))
            buttons.append(btn)

        # Update buttons container
        self.ui.saved_question_buttons_container.objects = buttons

    def _use_example_query(self, query):
        """Set the query text from a saved question"""
        logger.info(f"Using example query: {query['name']}")
        self.query_text = query["query"]

        # Update the input field
        self.ui.query_input.value = query["query"]

        # Process the query
        self._process_query()

    def _reset_all(self, event=None):
        """Reset the analysis assistant to initial state"""
        # Reset workflow
        self.workflow.reset()

        # Clear query input
        self.query_text = ""
        self.ui.query_input.value = ""

        # Clear question name
        self.question_name = ""
        self.ui.save_question_input.value = ""

        # Clear results
        self.ui.result_container.objects = []
        self.ui.visualization_pane.objects = []
        self.ui.code_display.objects = []

        # Hide all stage panes
        self.ui.clarifying_pane.visible = False
        self.ui.clarifying_input.visible = False
        self.ui.code_generation_pane.visible = False
        self.ui.execution_pane.visible = False

        # Reset engine
        self.engine = AnalysisEngine()

        # Reset stage indicators
        self.ui.update_stage_indicators(self.workflow.current_stage)

        # Update status
        self.ui.update_status("Ready for a new query")

    def _on_feedback_up(self, *_):
        """Handle thumbs-up click"""
        self._record_feedback("up")

    def _on_feedback_down(self, *_):
        """Handle thumbs-down click"""
        self._record_feedback("down")

    def _record_feedback(self, rating):
        """Record feedback in the database"""
        try:
            insert_feedback(question=self.query_text, rating=rating)
        except Exception as exc:
            logger.error(f"Feedback insert failed: {exc}")

        # Hide thumbs buttons and show thank-you note
        self._feedback_up.visible = False
        self._feedback_down.visible = False
        self._feedback_thanks.visible = True

    def view(self):
        """Generate the complete view for the data analysis assistant"""
        # Create title and description
        title = pn.pane.Markdown(
            "# Data Analysis Assistant", sizing_mode="stretch_width"
        )
        description = pn.pane.Markdown(
            """
            Ask questions about your patient data in natural language and get visualized insights.

            This assistant follows a multi-step workflow:
            1. Ask your question
            2. The assistant will clarify your intent if needed
            3. Python code will be generated for your analysis
            4. The code will be executed with explanations
            5. Results will be shown with visualizations

            You can save questions for future use using the "Save Question" button below.
            """
        )

        # Create query input row
        input_row = pn.Row(
            pn.Column(self.ui.query_input, sizing_mode="stretch_width"),
            pn.Spacer(width=10),
            self.analyze_button,
            sizing_mode="stretch_width",
        )

        # Create saved questions sidebar
        saved_questions_title = pn.pane.Markdown("### Saved Questions:")

        # Workflow progress display
        workflow_indicators = pn.Column(
            self.ui.workflow_indicator,
            *[indicator for _, indicator in sorted(self.ui.stage_indicators.items())],
            sizing_mode="stretch_width",
        )

        # Stage-specific content panels
        workflow_content = pn.Column(
            self.ui.clarifying_pane,
            self.ui.clarifying_input,
            self.ui.code_generation_pane,
            self.ui.execution_pane,
            sizing_mode="stretch_width",
        )

        # Navigation buttons
        workflow_nav_buttons = pn.Row(
            self.ui.continue_button, sizing_mode="stretch_width", align="start"
        )

        # Save/reset panel
        save_reset_panel = pn.Column(
            pn.Row(
                pn.pane.Markdown("### Save This Question", margin=(0, 0, 5, 0)),
                sizing_mode="stretch_width",
            ),
            pn.Row(
                self.ui.save_question_input,
                pn.Spacer(width=10),
                self.save_button,
                sizing_mode="stretch_width",
            ),
            pn.Spacer(height=15),
            pn.Row(
                pn.Spacer(),
                self.ui.reset_button,
                sizing_mode="stretch_width",
                align="end",
            ),
            sizing_mode="stretch_width",
            styles={"background": "#f8f9fa", "border-radius": "5px"},
            css_classes=["card", "rounded-card"],
        )

        # Create tabs for results, code, and visualizations
        result_tabs = pn.Tabs(
            ("Results", self.ui.result_container),
            ("Code", self.ui.code_display),
            ("Visualization", self.ui.visualization_pane),
            dynamic=True,
        )

        # Layout: sidebar – saved questions, narrative toggle, import widget
        sidebar = pn.Column(
            saved_questions_title,
            self.ui.saved_question_buttons_container,
            pn.Spacer(height=15),
            pn.Spacer(height=20),
            self.ui.import_panel,
            pn.Spacer(height=15),
            self.ui.delete_mock_panel,
            pn.Spacer(height=20),
            self.ui._show_narrative_checkbox,
            sizing_mode="stretch_width",
        )

        # Workflow panel
        workflow_panel = pn.Column(
            workflow_indicators,
            pn.layout.Divider(),
            workflow_content,
            workflow_nav_buttons,
            pn.layout.Divider(),
            save_reset_panel,
            sizing_mode="stretch_width",
            css_classes=["workflow-panel"],
        )

        # Create the main content area
        main_content_area = pn.Column(
            title,
            description,
            pn.layout.Divider(),
            input_row,
            pn.layout.Divider(),
            self.ui.status_display,
            workflow_panel,
            self.ui.ai_status_row_ref,
            pn.layout.Divider(),
            result_tabs,
            sizing_mode="stretch_width",
        )

        # Simplified layout with responsive sizes
        layout = pn.Row(
            pn.Column(sidebar, width=300),
            pn.Column(main_content_area, margin=(0, 10, 0, 20)),
            sizing_mode="stretch_width",
        )

        return layout


def data_assistant_page():
    """Create and return the data assistant page for the application."""
    assistant = DataAnalysisAssistant()
    return assistant.view()
