from app.utils.assumptions import NO_DATA_MESSAGE

"""
UI Components for Data Analysis Assistant

This module contains all the UI components (widgets, buttons, user inputs) for the
data analysis assistant, separated from business logic for better maintainability.

Example:
    >>> from app.ui import UIComponents
    >>> ui = UIComponents()
    >>> ui.query_input.value = "average BMI of active patients"
    >>> # Use ui in Panel app or pass to DataAnalysisAssistant
"""

import panel as pn
import param
import logging
import time
import threading

# Configure logging
logger = logging.getLogger("data_assistant.ui")


class UIComponents(param.Parameterized):
    """
    UI component wrapper for Data Analysis Assistant

    This class encapsulates all user interface elements, providing a clean
    separation from business logic and state management. It handles:

    - Widget creation and initialization
    - Display updates and state visualization
    - User input collection and validation
    - Visual feedback (status messages, animations, etc.)
    - Layout management and component organization

    Example:
        >>> ui = UIComponents()
        >>> ui.query_input.value = "average BMI of active patients"
    """

    # Core UI widgets that need to be accessible
    query_input = param.Parameter(default=None, doc="Main text input for user queries")
    workflow_indicator = param.Parameter(
        default=None, doc="Displays the current workflow stages"
    )
    stage_indicators = param.Dict(
        default={}, doc="Dictionary of indicators for each workflow stage"
    )
    status_display = param.Parameter(
        default=None, doc="Text display for status messages"
    )
    ai_status_text = param.Parameter(
        default=None, doc="Text showing AI processing status"
    )
    ai_status_row_ref = param.Parameter(
        default=None, doc="Container for AI status indicator"
    )
    clarifying_pane = param.Parameter(
        default=None, doc="Pane for displaying clarifying questions"
    )
    clarifying_input = param.Parameter(
        default=None, doc="Input for user responses to clarifying questions"
    )
    code_generation_pane = param.Parameter(
        default=None, doc="Pane for code generation UI elements"
    )
    execution_pane = param.Parameter(
        default=None, doc="Pane for execution results and status"
    )
    code_display = param.Parameter(
        default=None, doc="Code display widget showing generated analysis code"
    )
    result_container = param.Parameter(
        default=None, doc="Container for formatted analysis results"
    )
    visualization_pane = param.Parameter(
        default=None, doc="Pane for displaying data visualizations"
    )
    continue_button = param.Parameter(
        default=None, doc="Button to continue through workflow stages"
    )
    saved_question_buttons_container = param.Parameter(
        default=None, doc="Container for saved question buttons"
    )
    save_question_input = param.Parameter(
        default=None, doc="Input for naming and saving questions"
    )
    reset_button = param.Parameter(
        default=None, doc="Button to reset the analysis workflow"
    )
    import_panel = param.Parameter(default=None, doc="Panel for importing patient data")
    delete_mock_panel = param.Parameter(
        default=None, doc="Panel for resetting to mock data"
    )
    results_view_toggle = param.Parameter(
        default=None, doc="Toggle between narrative and tabular results view"
    )
    data_sample_pane = param.Parameter(
        default=None, doc="Pane showing sample data relevant to the query"
    )

    # Feedback components
    _feedback_up = param.Parameter(default=None, doc="Positive feedback button")
    _feedback_down = param.Parameter(default=None, doc="Negative feedback button")
    _feedback_thanks = param.Parameter(
        default=None, doc="Feedback acknowledgment message"
    )

    def __init__(self, **params):
        """
        Initialize UI components for Data Analysis Assistant

        Creates all Panel widgets, containers, and UI elements needed for the
        application, setting up their initial state and appearance.
        """
        super().__init__(**params)
        self._initialize_components()

    def _initialize_components(self):
        """
        Initialize all UI components

        Creates and configures all widgets, panes, and containers used in the UI.
        Sets up styling, default values, and visibility states for all elements.
        """
        # Main query input
        self.query_input = pn.widgets.TextAreaInput(
            name="Enter your question:",
            placeholder="e.g., What is the average BMI of active patients?",
            value="",
            rows=3,
            sizing_mode="stretch_width",
        )

        # Status display
        self.status_display = pn.pane.Markdown("**Status:** Ready")

        # AI thinking indicator
        self.ai_status_text = pn.pane.Markdown("AI is thinking...", align="center")
        self.ai_status_row_ref = pn.Row(
            self.ai_status_text,
            sizing_mode="stretch_width",
            align="center",
            styles={
                "background": "#f0f7ff",
                "border-radius": "5px",
                "padding": "8px",
                "margin-top": "10px",
                "margin-bottom": "10px",
                "border": "1px solid #cce5ff",
            },
            visible=False,  # Initially hidden until needed
        )

        # Initialize workflow indicators
        self._initialize_workflow_indicators()

        # Initialize stage-specific panels
        self.clarifying_pane = pn.Column(sizing_mode="stretch_width", visible=False)
        self.clarifying_input = pn.Column(sizing_mode="stretch_width", visible=False)
        self.code_generation_pane = pn.Column(
            sizing_mode="stretch_width", visible=False
        )
        self.execution_pane = pn.Column(sizing_mode="stretch_width", visible=False)
        self.code_display = pn.Column(sizing_mode="stretch_width")
        self.result_container = pn.Column(sizing_mode="stretch_width")
        self.visualization_pane = pn.Column(sizing_mode="stretch_width")
        self.data_sample_pane = pn.Column(sizing_mode="stretch_width")

        # Initialize navigation buttons
        self.continue_button = pn.widgets.Button(
            name="Continue",
            button_type="primary",
            disabled=True,
            width=100,
            visible=False,
        )

        # Initialize save components
        self.save_question_input = pn.widgets.TextInput(
            name="Question Name",
            placeholder="Enter a name to save this question",
            value="",
            sizing_mode="stretch_width",
        )

        # Initialize reset button
        self.reset_button = pn.widgets.Button(
            name="Reset All", button_type="danger", width=100
        )

        # Initialize saved questions container
        self.saved_question_buttons_container = pn.Column(sizing_mode="stretch_width")

        # Initialize import panel
        self.import_panel = pn.Column(
            pn.pane.Markdown("### Import Data"),
            pn.widgets.FileInput(
                accept=".json",
                multiple=False,
                height=50,
                sizing_mode="stretch_width",
                styles={"background": "#f8f9fa"},
            ),
            pn.widgets.Button(
                name="Import", button_type="primary", disabled=True, width=100
            ),
            sizing_mode="stretch_width",
            styles={"background": "#f8f9fa", "border-radius": "5px", "padding": "10px"},
            css_classes=["card", "rounded-card"],
        )

        # Initialize delete mock panel
        self.delete_mock_panel = pn.Column(
            pn.pane.Markdown("### Reset Database"),
            pn.widgets.Button(
                name="Reset to Default", button_type="warning", width=140
            ),
            sizing_mode="stretch_width",
            styles={"background": "#f8f9fa", "border-radius": "5px", "padding": "10px"},
            css_classes=["card", "rounded-card"],
        )

        # Initialize narrative/tabular toggle
        self.results_view_toggle = pn.widgets.Checkbox(
            name="ChatGPT Narrative",
            value=True,
            sizing_mode="stretch_width",
        )
        self._show_narrative_checkbox = self.results_view_toggle

        # Initialize feedback components
        self._feedback_up = pn.widgets.Button(
            name="👍", width=40, button_type="light", visible=True
        )
        self._feedback_down = pn.widgets.Button(
            name="👎", width=40, button_type="light", visible=True
        )
        self._feedback_thanks = pn.pane.Markdown(
            "Thank you for your feedback!", visible=False
        )

    def _initialize_workflow_indicators(self):
        """
        Initialize workflow stage indicators

        Creates and configures the visual indicators that show the current
        stage of the analysis workflow, with appropriate styling for each stage.
        """
        self.workflow_indicator = pn.pane.Markdown("### Analysis Workflow")

        # Initialize all stage indicators
        self.stage_indicators = {
            0: pn.pane.Markdown("1. ✏️ Input Query", styles={"color": "blue"}),
            1: pn.pane.Markdown("2. 🔍 Clarify Intent"),
            2: pn.pane.Markdown("3. 🧠 Generate Code"),
            3: pn.pane.Markdown("4. ⚙️ Execute Analysis"),
            4: pn.pane.Markdown("5. 📊 Display Results"),
        }

    def create_feedback_widget(self):
        """
        Create a feedback widget for the results

        Returns a Panel component containing feedback buttons and messages
        that allow users to provide feedback on analysis results.

        Returns:
            panel.Column: Styled feedback widget with buttons and messages
        """
        feedback_row = pn.Row(
            pn.pane.Markdown("Was this answer helpful?", margin=(5, 10, 5, 0)),
            self._feedback_up,
            self._feedback_down,
            self._feedback_thanks,
            align="center",
        )

        return pn.Column(
            pn.layout.Divider(),
            feedback_row,
            styles={"background": "#f8f9fa", "border-radius": "5px", "padding": "10px"},
        )

    def update_stage_indicators(self, current_stage):
        """Update stage indicators based on current stage"""
        for stage, indicator in self.stage_indicators.items():
            if stage < current_stage:
                indicator.styles = {"color": "green", "text-decoration": "line-through"}
            elif stage == current_stage:
                indicator.styles = {"color": "blue", "font-weight": "bold"}
            else:
                indicator.styles = {"color": "gray"}

    def update_status(self, message, type="info"):
        """
        Update the status display message with color and emphasis based on type.
        Args:
            message: The message to display
            type: One of "info", "success", "warning", "error"
        """
        color_map = {
            "info": "#2176ff",  # Blue
            "success": "#28a745",  # Green
            "warning": "#f0ad4e",  # Orange
            "error": "#dc3545",  # Red
        }
        color = color_map.get(type, "#2176ff")
        if self.status_display is not None:
            self.status_display.object = (
                f"<span style='color:{color};font-weight:bold'>{message}</span>"
            )

    def start_ai_indicator(self, message="AI is thinking..."):
        """Start the AI indicator animation"""
        self.ai_status_text.object = message
        self.ai_status_row_ref.visible = True

        # Animate ellipsis using a separate thread
        def _animate_ellipsis():
            base_message = message.rstrip(".")
            for i in range(10):  # 5-second animation
                if not self.ai_status_row_ref.visible:
                    break
                dots = "." * ((i % 3) + 1)
                self.ai_status_text.object = f"{base_message}{dots}"
                time.sleep(0.5)

        # Start animation thread
        thread = threading.Thread(target=_animate_ellipsis)
        thread.daemon = True
        thread.start()

    def stop_ai_indicator(self):
        """Stop the AI indicator animation"""
        self.ai_status_row_ref.visible = False

    def display_clarifying_questions(self, questions, process_clarification_callback):
        """Display clarifying questions to the user"""
        elements = [
            pn.pane.Markdown("### Clarifying Questions"),
            pn.pane.Markdown(
                "To provide more accurate results, please answer these questions:"
            ),
        ]

        # Add each question
        for i, q in enumerate(questions):
            elements.append(pn.pane.Markdown(f"**{i+1}. {q}**"))

        # Add a text area for the user's response
        response_input = pn.widgets.TextAreaInput(
            name="Your response:",
            placeholder="Type your answers here...",
            rows=3,
            sizing_mode="stretch_width",
        )
        elements.append(response_input)

        # Add a submit button
        submit_button = pn.widgets.Button(
            name="Submit", button_type="primary", width=100
        )
        submit_button.on_click(
            lambda event: process_clarification_callback(response_input.value)
        )
        elements.append(pn.Row(submit_button, sizing_mode="stretch_width"))

        # Update the clarifying pane with the elements
        self.clarifying_pane.objects = elements
        self.clarifying_pane.visible = True

    def display_generated_code(self, code):
        """Display the generated code"""
        # Extract SQL from code comments
        sql_statements = self._extract_sql_from_code(code)

        if sql_statements:
            self.code_display.objects = [
                pn.pane.Markdown("### SQL Statement"),
                pn.pane.Markdown(
                    "The following SQL statement is used for the analysis:"
                ),
                pn.widgets.CodeEditor(
                    value=sql_statements,
                    language="sql",
                    sizing_mode="stretch_width",
                    theme="chrome",
                    readonly=True,
                    height=200,
                ),
                pn.pane.Markdown("### Generated Python Code"),
                pn.pane.Markdown(
                    "The following Python code executes the SQL and processes results:"
                ),
                pn.widgets.CodeEditor(
                    value=code,
                    language="python",
                    sizing_mode="stretch_width",
                    theme="chrome",
                    readonly=True,
                    height=300,
                ),
            ]
        else:
            self.code_display.objects = [
                pn.pane.Markdown("### Generated Python Code"),
                pn.pane.Markdown(
                    "The following code will be executed to analyze your query:"
                ),
                pn.widgets.CodeEditor(
                    value=code,
                    language="python",
                    sizing_mode="stretch_width",
                    theme="chrome",
                    readonly=True,
                    height=300,
                ),
            ]

    def _extract_sql_from_code(self, code):
        """Extract SQL statements from code comments"""
        import re

        # Look for SQL in various comment patterns
        patterns = [
            # Multi-line SQL comments
            r"# SQL equivalent:\s*\n# (.+?)(?=\n#|\n[^#]|\Z)",
            # Single-line SQL comments
            r"# SQL equivalent:\s*(.+?)(?=\n|$)",
            # SQL in string variables
            r'sql\s*=\s*["\']([^"\']+)["\']',
            r'_sql\s*=\s*["\']([^"\']+)["\']',  # _sql variables
            r'sql\s*=\s*"""([^"]+)"""',  # Triple-quoted SQL
            r'_sql\s*=\s*"""([^"]+)"""',  # Triple-quoted _sql
        ]

        sql_statements = []
        for pattern in patterns:
            matches = re.findall(pattern, code, re.MULTILINE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ""
                # Clean up the SQL
                sql = match.strip().replace("\\n", "\n").replace('\\"', '"')
                if sql and "SELECT" in sql.upper():
                    sql_statements.append(sql)

        # Return the first valid SQL statement found
        return sql_statements[0] if sql_statements else ""

    def display_execution_results(self, results, visualizations):
        """Display execution results"""
        from app.analysis_helpers import combine_visualizations

        # Create execution pane content
        elements = [
            pn.pane.Markdown("### Analysis Results"),
            pn.pane.Markdown("The analysis has been completed. Here are the results:"),
        ]

        # Handle error results
        if isinstance(results, dict) and "error" in results:
            elements.append(
                pn.pane.Alert(
                    f"Error: {results['error']}",
                    alert_type="danger",
                    sizing_mode="stretch_width",
                )
            )

            # Show traceback if available
            if "traceback" in results:
                elements.append(
                    pn.widgets.CodeEditor(
                        value=results["traceback"],
                        language="python",
                        sizing_mode="stretch_width",
                        theme="chrome",
                        readonly=True,
                        height=300,
                    )
                )
        else:
            # Format results based on type
            if isinstance(results, (int, float)):
                elements.append(pn.pane.Markdown(f"**Result:** {results}"))
            elif isinstance(results, dict):
                # Remove unnecessary fields from display
                display_results = {
                    k: v
                    for k, v in results.items()
                    if k not in ["visualization", "execution_time", "index", "bmi_mean"]
                }

                # If there are meaningful results to show, display them
                if display_results:
                    if len(display_results) == 1:
                        # Single result - display as simple text
                        key, value = next(iter(display_results.items()))
                        elements.append(pn.pane.Markdown(f"**{key.title()}:** {value}"))
                    else:
                        # Multiple results - display as formatted text
                        for key, value in display_results.items():
                            elements.append(
                                pn.pane.Markdown(f"**{key.title()}:** {value}")
                            )
            elif hasattr(results, "to_dict"):
                # Handle DataFrame-like objects
                elements.append(
                    pn.widgets.Tabulator(
                        results,
                        pagination="local",
                        page_size=10,
                        sizing_mode="stretch_width",
                        theme="default",
                    )
                )
            else:
                # Default display
                elements.append(pn.pane.Markdown(NO_DATA_MESSAGE))

        # Update execution pane
        self.execution_pane.objects = elements
        self.execution_pane.visible = True

        # Update visualization pane if visualizations exist or can be created
        if visualizations:
            combined_viz = combine_visualizations(visualizations)
            if combined_viz:
                self.visualization_pane.objects = [combined_viz]
        else:
            # Try to create visualization from results
            self._create_visualization_from_results(results)

    def add_refine_option(self, formatted_results, process_refinement_callback):
        """Add refine option to formatted results"""
        # Create refine section
        refine_section = pn.Column(
            pn.Row(
                pn.pane.Markdown("### Refine Your Query"),
                sizing_mode="stretch_width",
            ),
            pn.Row(
                pn.pane.Markdown(
                    "Not what you're looking for? Refine your query with more details:"
                ),
                sizing_mode="stretch_width",
            ),
            pn.Row(
                pn.widgets.TextAreaInput(
                    placeholder="Add more details to your query...",
                    rows=2,
                    name="refine_input",
                    sizing_mode="stretch_width",
                ),
                sizing_mode="stretch_width",
            ),
            pn.Row(
                pn.widgets.Button(name="Refine", button_type="primary", width=100),
                sizing_mode="stretch_width",
                align="end",
            ),
            sizing_mode="stretch_width",
            styles={
                "background": "#f8f9fa",
                "border-radius": "5px",
                "padding": "10px",
                "margin-top": "20px",
            },
            css_classes=["card"],
        )

        # Connect refine button
        refine_input = refine_section[2][0]
        refine_button = refine_section[3][0]
        refine_button.on_click(
            lambda event: process_refinement_callback(refine_input.value)
        )

        # Handle different input types
        if isinstance(formatted_results, dict):
            # Convert dict to a list with a Markdown pane
            summary = formatted_results.get("summary", str(formatted_results))
            formatted_results = [pn.pane.Markdown(summary)]
        elif not isinstance(formatted_results, list):
            # Handle any other non-list type
            formatted_results = [pn.pane.Markdown(str(formatted_results))]

        # Add refine section to results
        formatted_results.append(pn.layout.Divider())
        formatted_results.append(refine_section)

        return formatted_results

    def _create_visualization_from_results(self, results):
        """Create visualization from results if appropriate"""
        try:
            from app.utils.plots import (
                bar_chart,
                html_bar_chart,
            )
            import pandas as pd

            viz_elements = []
            # Handle dictionary results that might be suitable for visualization
            if isinstance(results, dict):
                # Remove non-data fields
                data_dict = {
                    k: v
                    for k, v in results.items()
                    if k
                    not in [
                        "visualization",
                        "execution_time",
                        "index",
                        "bmi_mean",
                        "error",
                    ]
                    and isinstance(v, (int, float, str))
                    and v is not None
                }
                # If we have multiple numeric values, create a bar chart
                if len(data_dict) > 1:
                    numeric_data = {
                        k: v
                        for k, v in data_dict.items()
                        if isinstance(v, (int, float))
                    }
                    if len(numeric_data) > 1:
                        try:
                            df = pd.DataFrame(
                                list(numeric_data.items()),
                                columns=["Category", "Value"],
                            )
                            chart = bar_chart(
                                df,
                                x="Category",
                                y="Value",
                                title="Analysis Results",
                                height=300,
                                width=500,
                            )
                            viz_elements.append(chart)
                        except Exception:
                            try:
                                categories = list(numeric_data.keys())
                                values = list(numeric_data.values())
                                html_chart = html_bar_chart(
                                    categories, values, title="Analysis Results"
                                )
                                viz_elements.append(html_chart)
                            except Exception:
                                pass
                # For single values, create a simple display
                elif len(data_dict) == 1:
                    key, value = next(iter(data_dict.items()))
                    if isinstance(value, (int, float)):
                        import panel as pn

                        html = f"""
                        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;height:200px;padding:20px;'>
                            <span style='font-size:48px;font-weight:bold;color:#2c3e50'>{value}</span>
                            <span style='font-size:16px;color:#7f8c8d'>{key.replace('_', ' ').title()}</span>
                        </div>
                        """
                        viz_elements.append(pn.pane.HTML(html))
            # Handle DataFrame results
            elif hasattr(results, "to_dict") and hasattr(results, "columns"):
                try:
                    numeric_cols = results.select_dtypes(include=["number"]).columns
                    if len(numeric_cols) > 0 and len(results) > 1:
                        first_numeric = numeric_cols[0]
                        chart = bar_chart(
                            results.reset_index(),
                            x=(
                                "index"
                                if "index" in results.columns
                                else results.index.name or "Category"
                            ),
                            y=first_numeric,
                            title=f'{first_numeric.replace("_", " ").title()} by Category',
                            height=300,
                            width=500,
                        )
                        viz_elements.append(chart)
                except Exception:
                    pass
            if viz_elements:
                self.visualization_pane.objects = viz_elements
            else:
                import panel as pn

                self.visualization_pane.objects = [
                    pn.pane.Markdown(
                        "*No visualization available for this analysis type*"
                    )
                ]
        except Exception:
            import panel as pn

            self.visualization_pane.objects = [
                pn.pane.Markdown("*Visualization could not be generated*")
            ]


def get_stage_emoji(stage):
    """Get the emoji for a workflow stage."""
    emojis = {
        0: "✏️",  # Input
        1: "🔍",  # Clarify
        2: "🧠",  # Generate
        3: "⚙️",  # Execute
        4: "📊",  # Results
    }
    return emojis.get(stage, "❓")
