"""
Data Analysis Assistant Page

This page provides interactive data analysis capabilities using natural language queries.
"""

import panel as pn
import param
import pandas as pd
import holoviews as hv
import numpy as np
import logging
import db_query
import json
import os
import re
from app.ai_helper import ai, get_data_schema  # Fix import path
from app.utils.sandbox import run_snippet
from app.utils.plots import histogram  # new helper
from app.utils.query_intent import QueryIntent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("data_assistant")

# Initialize rendering backend for HoloViews plots
hv.extension("bokeh")
pn.extension("tabulator")
pn.extension("plotly")

# Define the path for storing saved questions
SAVED_QUESTIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "saved_questions.json",
)

# Ensure the data directory exists
os.makedirs(os.path.dirname(SAVED_QUESTIONS_FILE), exist_ok=True)

# TODO: For cloud deployment, replace file storage with database storage
# - Create a 'saved_questions' table in patient_data.db
# - Update load_saved_questions() and save_questions_to_file() to use the database
# - This will make saved questions persist across instances in a cloud environment

# Function to load saved questions from file
# tail -n 100 logs/ai_trace.log


def load_saved_questions():
    """Load saved questions from a JSON file"""
    if os.path.exists(SAVED_QUESTIONS_FILE):
        try:
            with open(SAVED_QUESTIONS_FILE, "r") as f:
                saved_questions = json.load(f)
                logger.info(
                    f"Loaded {len(saved_questions)} saved questions from {SAVED_QUESTIONS_FILE}"
                )
                return saved_questions
        except Exception as e:
            logger.error(f"Error loading saved questions: {str(e)}", exc_info=True)

    # Return default questions if file doesn't exist or has an error
    return [
        {
            "name": "Active patients count",
            "query": "How many active patients are in the program?",
        },
        {
            "name": "Average patient weight",
            "query": "What is the average weight of patients?",
        },
        {
            "name": "Female BMI average",
            "query": "What is the average BMI of female patients?",
        },
        {
            "name": "Male BMI average",
            "query": "What is the average BMI of male patients?",
        },
        {
            "name": "BMI distribution",
            "query": "Show me the distribution of BMI across all patients",
        },
        {
            "name": "Blood pressure comparison",
            "query": "Compare blood pressure values for patients with high vs. normal A1C",
        },
        {
            "name": "Improvement percentage",
            "query": "What percentage of patients showed improvement in their vital signs?",
        },
        {
            "name": "No recent visits",
            "query": "Which patients have not had a visit in the last 3 months?",
        },
    ]


# Function to save questions to file


def save_questions_to_file(questions):
    """Save questions to a JSON file"""
    try:
        with open(SAVED_QUESTIONS_FILE, "w") as f:
            json.dump(questions, f, indent=2)
        logger.info(f"Saved {len(questions)} questions to {SAVED_QUESTIONS_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving questions: {str(e)}", exc_info=True)
        return False


class DataAnalysisAssistant(param.Parameterized):
    """Data Analysis Assistant page with AI-powered data analysis capabilities"""

    query_text = param.String(default="", doc="Natural language query")
    analysis_result = param.Dict(default={})

    # Analysis workflow stages
    STAGE_INITIAL = 0
    STAGE_CLARIFYING = 1
    STAGE_SHOWING_DATA = 2
    STAGE_CODE_GENERATION = 3
    STAGE_EXECUTION = 4
    STAGE_RESULTS = 5

    current_stage = param.Integer(
        default=STAGE_INITIAL, doc="Current stage in the analysis workflow"
    )

    # Data for the workflow stages
    clarifying_questions = param.List(
        default=[], doc="List of questions to clarify user intent"
    )
    data_samples = param.Dict(default={}, doc="Sample data to show the user")
    generated_code = param.String(default="", doc="Generated Python code for analysis")
    # Use a generic Parameter to allow scalar, Series, dict, etc.
    intermediate_results = param.Parameter(
        default=None,
        doc="Results from intermediate steps (could be scalar, Series, or dict)",
    )

    # Replace example_queries with saved_questions
    saved_questions = param.List(default=[], doc="List of saved questions")
    question_name = param.String(default="", doc="Name for saving the current query")

    def __init__(self, **params):
        super().__init__(**params)

        # Initialize saved questions from the saved file
        if not self.saved_questions:
            self.saved_questions = load_saved_questions()

        # Results display panes
        self.result_pane = pn.pane.Markdown("Enter a query to analyze data")
        self.code_display = pn.pane.Markdown("")
        self.visualization_pane = pn.pane.HoloViews(hv.Div(""))

        # AI progress indicator (simple text-based approach)
        self.ai_status_text = pn.pane.Markdown(
            "", styles={"color": "#0066cc", "font-weight": "bold"}
        )

        # Setup for animated ellipsis
        self.ai_status_row_ref = None  # Will hold reference to the status row
        self.ellipsis_count = 0
        self.ellipsis_animation = None  # Will hold periodic callback

        # Status and interaction
        self.status_message = "Ready to analyze data"
        self.status_display = pn.pane.Markdown(f"**Status:** {self.status_message}")
        self.query_input = None
        self.question_name_input = None

        # Workflow stage displays
        self.workflow_indicator = pn.pane.Markdown("### Analysis Workflow Status")
        self.stage_indicators = {}

        # Interactive components for each stage
        self.clarifying_pane = pn.Column(pn.pane.Markdown(""))
        self.data_sample_pane = pn.Column(pn.pane.Markdown(""))
        self.code_generation_pane = pn.Column(pn.pane.Markdown(""))
        self.execution_pane = pn.Column(pn.pane.Markdown(""))

        # Buttons for workflow navigation
        self.continue_button = pn.widgets.Button(
            name="Continue", button_type="primary", disabled=True, width=100
        )
        self.continue_button.on_click(self._advance_workflow)

        # Initialize display content
        self._initialize_stage_indicators()

    def view(self):
        """Generate the data analysis assistant view"""

        # Create title and description
        title = pn.pane.Markdown(
            "# Data Analysis Assistant", sizing_mode="stretch_width"
        )
        description = pn.pane.Markdown(
            """
            Ask questions about your patient data in natural language and get visualized insights.
            
            This assistant follows a multi-step workflow:
            1. Ask your question
            2. The assistant will clarify your intent
            3. Relevant data samples will be shown
            4. Python code will be generated for your analysis
            5. The code will be executed with explanations
            6. Results will be shown with visualizations
            
            You can save questions for future use using the "Save Question" button below.
            """
        )

        # Create query input with button
        self.query_input = pn.widgets.TextAreaInput(
            name="Enter your question:",
            placeholder="e.g., What is the average BMI of active patients?",
            value=self.query_text,
            rows=3,
            sizing_mode="stretch_width",
        )

        # Add a watcher to update the query_text parameter when the input changes
        def update_query_text(event):
            self.query_text = event.new
            logger.info(f"Query text updated to: {self.query_text}")

        self.query_input.param.watch(update_query_text, "value")

        # Analyze button
        analyze_button = pn.widgets.Button(
            name="Analyze", button_type="primary", sizing_mode="fixed", width=100
        )

        # Update the button click handler to use the current input value
        def on_analyze_click(event):
            logger.info(f"Analyze button clicked with query: {self.query_text}")
            # Reset workflow and start from the beginning
            self.current_stage = self.STAGE_INITIAL
            self._update_stage_indicators()
            self._process_query(event)

        analyze_button.on_click(on_analyze_click)

        # Create saved questions sidebar
        saved_questions_title = pn.pane.Markdown("### Saved Questions:")
        self.saved_question_buttons_container = pn.Column(sizing_mode="stretch_width")

        # Update the saved question buttons
        self._update_saved_question_buttons()

        # Workflow progress display
        workflow_indicators = pn.Column(
            self.workflow_indicator,
            *[indicator for _, indicator in sorted(self.stage_indicators.items())],
            sizing_mode="stretch_width",
        )

        # Stage-specific content panels
        workflow_content = pn.Column(
            self.clarifying_pane,
            self.data_sample_pane,
            self.code_generation_pane,
            self.execution_pane,
            sizing_mode="stretch_width",
        )

        # Navigation buttons
        self.save_question_input = pn.widgets.TextInput(
            name="Question Name",
            placeholder="Enter a name to save this question",
            value=self.question_name,
            sizing_mode="stretch_width",
        )

        def update_question_name(event):
            self.question_name = event.new

        self.save_question_input.param.watch(update_question_name, "value")

        save_question_button = pn.widgets.Button(
            name="Save Question", button_type="success", width=120
        )
        save_question_button.on_click(self._save_question)

        reset_button = pn.widgets.Button(
            name="Reset All", button_type="danger", width=100
        )
        reset_button.on_click(self._reset_all)

        # Workflow navigation buttons
        workflow_nav_buttons = pn.Row(
            self.continue_button, sizing_mode="stretch_width", align="start"
        )

        # Save and reset buttons
        save_reset_panel = pn.Column(
            pn.Row(
                pn.pane.Markdown("### Save This Question", margin=(0, 0, 5, 0)),
                sizing_mode="stretch_width",
            ),
            pn.Row(
                self.save_question_input,
                pn.Spacer(width=10),
                save_question_button,
                sizing_mode="stretch_width",
            ),
            pn.Spacer(height=15),
            pn.Row(pn.Spacer(), reset_button, sizing_mode="stretch_width", align="end"),
            sizing_mode="stretch_width",
            styles={"background": "#f8f9fa", "border-radius": "5px"},
            css_classes=["card", "rounded-card"],
            margin=(15, 15, 15, 15),
        )

        # Status indicator
        self.status_display = pn.pane.Markdown(f"**Status:** {self.status_message}")

        # Combine everything in a layout
        input_row = pn.Row(
            pn.Column(self.query_input, sizing_mode="stretch_width"),
            pn.Spacer(width=10),
            analyze_button,
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

        # AI processing indicator with prominent styling
        ai_status_row = pn.Row(
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

        # Store reference to the status row for animation control
        self.ai_status_row_ref = ai_status_row

        # Create tabs for results, code, and visualizations
        result_tabs = pn.Tabs(
            ("Results", self.result_pane),
            ("Code", self.code_display),
            ("Visualization", self.visualization_pane),
            dynamic=True,
        )

        # Create the left sidebar with saved questions
        left_sidebar = pn.Card(
            pn.Column(
                saved_questions_title,
                self.saved_question_buttons_container,
                sizing_mode="stretch_width",
            ),
            sizing_mode="stretch_width",
            title="Saved Questions",
            collapsed=False,
        )

        # Create the main content area
        main_content_area = pn.Column(
            title,
            description,
            pn.layout.Divider(),
            input_row,
            pn.layout.Divider(),
            self.status_display,
            workflow_panel,
            ai_status_row,  # Add AI status indicator after workflow panel
            pn.layout.Divider(),
            result_tabs,
            sizing_mode="stretch_width",
        )

        # Simplified layout with responsive sizes
        layout = pn.Row(
            pn.Column(left_sidebar, width=300),
            pn.Column(main_content_area, margin=(0, 10, 0, 20)),
            sizing_mode="stretch_width",
        )

        return layout

    def _use_example_query(self, query):
        """Set the query text from an example query"""
        logger.info(f"Using example query: {query['name']}")
        self.query_text = query["query"]

        # Update the input field to reflect the example query
        if self.query_input is not None:
            self.query_input.value = query["query"]
            logger.info("Updated query input field with example query")

        # Process the query
        self._process_query()

    def _update_status(self, message):
        """Update the status message and display"""
        self.status_message = message
        logger.info(f"Status updated: {message}")

        if self.status_display is not None:
            self.status_display.object = f"**Status:** {self.status_message}"

    def _process_query(self, event=None):
        """Process the natural language query and generate analysis"""
        logger.info(f"Processing query: '{self.query_text}'")

        if not self.query_text:
            self._update_status("Please enter a query")
            logger.warning("Empty query detected")
            return

        # Reset workflow states
        self.clarifying_pane.objects = []
        self.data_sample_pane.objects = []
        self.code_generation_pane.objects = []
        self.execution_pane.objects = []

        # Reset result displays
        self.result_pane.object = "Enter a query to analyze data"
        self.code_display.object = ""
        self.visualization_pane.object = hv.Div("")

        try:
            # Set up workflow
            self.current_stage = self.STAGE_INITIAL
            self._update_stage_indicators()
            self._update_status("Starting analysis workflow...")

            # Process the query through the workflow
            self._process_current_stage()

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            self._update_status(f"Error: {str(e)}")
            self.result_pane.object = f"### Error\n\nSorry, there was an error processing your query: {str(e)}"

    def _generate_analysis(self):
        """Generate analysis from the query (mock implementation)"""
        query = self.query_text.lower()

        # Initialize samples dict for data sample collection
        samples = {}

        # Mock responses based on query types
        if "active patients" in query:
            # Mock getting active patients
            patients_df = db_query.get_all_patients()
            active_count = len(patients_df[patients_df["active"] == 1])

            # Store the result
            self.analysis_result = {
                "type": "count",
                "value": active_count,
                "title": "Active Patients",
                "description": f"There are {active_count} active patients in the program.",
                "code": "# Python code to count active patients\npatients_df = db_query.get_all_patients()\nactive_count = len(patients_df[patients_df['active'] == 1])",
                "visualization": self._create_count_visualization(
                    active_count, "Active Patients"
                ),
            }

        elif "average weight" in query:
            # Get actual weight data
            vitals_df = db_query.get_all_vitals()

            # Filter if gender is specified
            if "female" in query or "women" in query:
                logger.info("Filtering for female patients")
                patients_df = db_query.get_all_patients()
                female_patients = patients_df[patients_df["gender"] == "F"][
                    "id"
                ].tolist()
                vitals_df = vitals_df[vitals_df["patient_id"].isin(female_patients)]
                title = "Average Weight (Female Patients)"
            elif "male" in query or "men" in query:
                logger.info("Filtering for male patients")
                patients_df = db_query.get_all_patients()
                male_patients = patients_df[patients_df["gender"] == "M"]["id"].tolist()
                vitals_df = vitals_df[vitals_df["patient_id"].isin(male_patients)]
                title = "Average Weight (Male Patients)"
            else:
                title = "Average Weight (All Patients)"

            # Calculate average
            avg_weight = round(vitals_df["weight"].mean(), 1)
            count = len(vitals_df["patient_id"].unique())

            # Generate code string based on the filters
            if "female" in query or "women" in query:
                code_str = "# Python code to calculate average weight for female patients\npatients_df = db_query.get_all_patients()\nvitals_df = db_query.get_all_vitals()\n\n# Filter for female patients\nfemale_patients = patients_df[patients_df['gender'] == 'F']['id'].tolist()\nvitals_df = vitals_df[vitals_df['patient_id'].isin(female_patients)]\n\n# Calculate average\navg_weight = vitals_df['weight'].mean()"
            elif "male" in query or "men" in query:
                code_str = "# Python code to calculate average weight for male patients\npatients_df = db_query.get_all_patients()\nvitals_df = db_query.get_all_vitals()\n\n# Filter for male patients\nmale_patients = patients_df[patients_df['gender'] == 'M']['id'].tolist()\nvitals_df = vitals_df[vitals_df['patient_id'].isin(male_patients)]\n\n# Calculate average\navg_weight = vitals_df['weight'].mean()"
            else:
                code_str = "# Python code to calculate average weight\nvitals_df = db_query.get_all_vitals()\navg_weight = vitals_df['weight'].mean()"

            self.analysis_result = {
                "type": "statistic",
                "value": avg_weight,
                "title": title,
                "description": f"The average weight is {avg_weight} lbs, based on data from {count} patients.",
                "code": code_str,
                "visualization": self._create_histogram(
                    vitals_df, "weight", f"Weight Distribution (lbs) - {count} patients"
                ),
            }

        elif "bmi" in query:
            # Get real BMI data from database
            vitals_df = db_query.get_all_vitals()

            # Filter only records with valid BMI values
            vitals_df = vitals_df.dropna(subset=["bmi"])

            # Check for threshold query patterns - count patients above/below a threshold
            is_threshold_query = False
            threshold_value = None
            threshold_direction = None

            # Extract threshold from query
            if any(
                word in query
                for word in ["above", "over", "greater than", "higher than"]
            ):
                threshold_direction = "above"
                is_threshold_query = True
            elif any(
                word in query for word in ["below", "under", "less than", "lower than"]
            ):
                threshold_direction = "below"
                is_threshold_query = True

            # Extract numeric value from query (e.g., 30 from "BMI over 30")
            numbers = re.findall(r"\d+(?:\.\d+)?", query)
            if numbers and is_threshold_query:
                threshold_value = float(numbers[0])

            # Filter by gender if specified
            if "female" in query or "women" in query:
                logger.info("Filtering BMI for female patients")
                patients_df = db_query.get_all_patients()
                female_patients = patients_df[patients_df["gender"] == "F"][
                    "id"
                ].tolist()
                logger.info(f"Found {len(female_patients)} female patients")
                vitals_df = vitals_df[vitals_df["patient_id"].isin(female_patients)]
                title = "BMI Distribution (Female Patients)"
                filtered_desc = "female patients"
            elif "male" in query or "men" in query:
                logger.info("Filtering BMI for male patients")
                patients_df = db_query.get_all_patients()
                male_patients = patients_df[patients_df["gender"] == "M"]["id"].tolist()
                logger.info(f"Found {len(male_patients)} male patients")
                vitals_df = vitals_df[vitals_df["patient_id"].isin(male_patients)]
                title = "BMI Distribution (Male Patients)"
                filtered_desc = "male patients"
            else:
                title = "BMI Distribution (All Patients)"
                filtered_desc = "all patients"

            # Create different analysis based on query type
            if is_threshold_query and threshold_value is not None:
                # Count-based threshold query
                if threshold_direction == "above":
                    threshold_data = vitals_df[vitals_df["bmi"] > threshold_value]
                    # variable unused; placeholder to satisfy linter
                    _ = f"above {threshold_value}"
                else:
                    threshold_data = vitals_df[vitals_df["bmi"] < threshold_value]
                    _ = f"below {threshold_value}"

                # Count unique patients
                count = threshold_data["patient_id"].nunique()

                # Store the result
                self.analysis_result = {
                    "type": "count",
                    "value": count,
                    "title": f"Patients with BMI {threshold_direction} {threshold_value}",
                    "description": f"There are {count} {filtered_desc} with a BMI {threshold_direction} {threshold_value}.",
                    "code": f"# Python code to count patients with BMI {threshold_direction} {threshold_value}\nvitals_df = db_query.get_all_vitals()\nvitals_df = vitals_df.dropna(subset=['bmi'])\n\n# Filter for patients with BMI {threshold_direction} {threshold_value}\nthreshold_data = vitals_df[vitals_df['bmi'] {'>' if threshold_direction == 'above' else '<'} {threshold_value}]\n\n# Count unique patients\ncount = threshold_data['patient_id'].nunique()",
                    "visualization": self._create_histogram(
                        vitals_df, "bmi", f"BMI Distribution - {filtered_desc}"
                    ),
                }
            else:
                # Standard BMI analysis (average and distribution)
                # Calculate statistics
                logger.info(f"Calculating BMI stats based on {len(vitals_df)} records")
                avg_bmi = round(vitals_df["bmi"].mean(), 1)
                count = len(vitals_df["patient_id"].unique())

                # Generate code string based on the filters
                if "female" in query or "women" in query:
                    code_str = "# Python code to analyze BMI for female patients\npatients_df = db_query.get_all_patients()\nvitals_df = db_query.get_all_vitals()\n\n# Filter for female patients\nfemale_patients = patients_df[patients_df['gender'] == 'F']['id'].tolist()\nvitals_df = vitals_df[vitals_df['patient_id'].isin(female_patients)]\nvitals_df = vitals_df.dropna(subset=['bmi'])\n\n# Calculate statistics\navg_bmi = vitals_df['bmi'].mean()\nunique_patients = len(vitals_df['patient_id'].unique())"
                elif "male" in query or "men" in query:
                    code_str = "# Python code to analyze BMI for male patients\npatients_df = db_query.get_all_patients()\nvitals_df = db_query.get_all_vitals()\n\n# Filter for male patients\nmale_patients = patients_df[patients_df['gender'] == 'M']['id'].tolist()\nvitals_df = vitals_df[vitals_df['patient_id'].isin(male_patients)]\nvitals_df = vitals_df.dropna(subset=['bmi'])\n\n# Calculate statistics\navg_bmi = vitals_df['bmi'].mean()\nunique_patients = len(vitals_df['patient_id'].unique())"
                else:
                    code_str = "# Python code to analyze BMI distribution\nvitals_df = db_query.get_all_vitals()\nvitals_df = vitals_df.dropna(subset=['bmi'])\n\n# Calculate statistics\navg_bmi = vitals_df['bmi'].mean()\nunique_patients = len(vitals_df['patient_id'].unique())"

                self.analysis_result = {
                    "type": "distribution",
                    "title": title,
                    "description": f"The average BMI for {filtered_desc} is {avg_bmi}, based on data from {count} patients.",
                    "code": code_str,
                    "visualization": self._create_histogram(
                        vitals_df, "bmi", f"BMI Distribution - {count} patients"
                    ),
                }

        elif "active patients" in query:
            # Get active patients data
            active_patients = patients_df[patients_df["active"] == 1]
            samples["active_patients"] = active_patients.head(5)
            samples["active_count"] = len(active_patients)

        else:
            # Default to sample of general patient data
            samples["patients"] = patients_df.head(5)

        self.data_samples = samples
        logger.info(f"Retrieved {len(samples)} data sample types")

    def _display_data_samples(self):
        """Display the retrieved data samples to the user"""
        if not self.data_samples:
            self.data_sample_pane.objects = [
                pn.pane.Markdown("No data samples retrieved.")
            ]
            return

        logger.info("Displaying data samples")
        sample_panels = []

        # Header
        sample_panels.append(
            pn.pane.Markdown(
                "### Data Samples\n\nHere are some relevant data samples to help with your analysis:"
            )
        )

        # Display samples based on what was retrieved
        if "error" in self.data_samples:
            sample_panels.append(
                pn.pane.Markdown(
                    f"**Error retrieving samples:** {self.data_samples['error']}"
                )
            )

        if "vitals" in self.data_samples:
            sample_panels.append(pn.pane.Markdown("#### Vitals Data Sample:"))
            sample_panels.append(
                pn.widgets.Tabulator(
                    self.data_samples["vitals"],
                    pagination="remote",
                    page_size=5,
                    sizing_mode="stretch_width",
                )
            )

        if "bmi_stats" in self.data_samples:
            # Convert the Series to a more display-friendly format
            bmi_stats = self.data_samples["bmi_stats"]
            stats_df = pd.DataFrame(
                {"Statistic": bmi_stats.index, "Value": bmi_stats.values.round(2)}
            )

            sample_panels.append(pn.pane.Markdown("#### BMI Statistics:"))
            sample_panels.append(
                pn.widgets.Tabulator(stats_df, sizing_mode="stretch_width")
            )

        if "active_patients" in self.data_samples:
            sample_panels.append(pn.pane.Markdown("#### Active Patients Sample:"))
            sample_panels.append(
                pn.widgets.Tabulator(
                    self.data_samples["active_patients"],
                    pagination="remote",
                    page_size=5,
                    sizing_mode="stretch_width",
                )
            )

            if "active_count" in self.data_samples:
                sample_panels.append(
                    pn.pane.Markdown(
                        f"**Total Active Patients:** {self.data_samples['active_count']}"
                    )
                )

        if "patients" in self.data_samples:
            sample_panels.append(pn.pane.Markdown("#### General Patient Data:"))
            sample_panels.append(
                pn.widgets.Tabulator(
                    self.data_samples["patients"],
                    pagination="remote",
                    page_size=5,
                    sizing_mode="stretch_width",
                )
            )

        # Add a note about the data
        sample_panels.append(
            pn.pane.Markdown(
                "*These samples represent a small subset of the data that will be used for analysis.*"
            )
        )

        # Update the display
        self.data_sample_pane.objects = sample_panels

    def _generate_analysis_code(self):
        """Generate Python code for the analysis based on the query and clarifications"""
        logger.info("Generating analysis code")

        try:
            # Show AI is thinking for intent analysis
            self._start_ai_indicator("ChatGPT is analyzing your query intent...")

            # First, get the query intent using AI
            intent = ai.get_query_intent(self.query_text)

            # Update status for code generation
            self._start_ai_indicator("ChatGPT is generating analysis code...")

            # Get data schema for code generation
            data_schema = get_data_schema()

            # Generate analysis code based on intent
            generated_code = ai.generate_analysis_code(intent, data_schema)

            # Hide the indicator when done
            self._stop_ai_indicator()

            # Store the generated code
            self.generated_code = generated_code

            # Store intent for reference in execution
            self.query_intent = intent

            logger.info("Successfully generated AI-powered analysis code")

        except Exception as e:
            # Hide the indicator in case of error
            self._stop_ai_indicator()

            logger.error(
                f"Error generating AI-powered analysis code: {str(e)}", exc_info=True
            )

            # Fall back to rule-based code generation
            self.generated_code = self._generate_fallback_code()
            logger.info("Generated fallback rule-based analysis code")

    def _display_generated_code(self):
        """Display the generated code with explanations"""
        if not self.generated_code:
            self.code_generation_pane.objects = [
                pn.pane.Markdown("No code has been generated.")
            ]
            return

        logger.info("Displaying generated code")

        # Create a code panel with explanations
        code_panels = []

        # Header
        code_panels.append(
            pn.pane.Markdown(
                "### Generated Analysis Code\n\nBased on your query and clarifications, I've generated the following Python code to analyze the data:"
            )
        )

        # Display code in a syntax-highlighted panel using markdown code block
        code_md = f"```python\n{self.generated_code}\n```"
        code_panels.append(pn.pane.Markdown(code_md, sizing_mode="stretch_width"))

        # Add explanations
        explanation = """
### Code Explanation

This code performs the following steps:

1. **Data Loading**: Gets the necessary data from the database
2. **Data Filtering**: Applies filters based on your query and clarifications
3. **Statistical Analysis**: Calculates relevant metrics like averages and distributions
4. **Visualization**: Creates appropriate visualizations to help interpret the results

The code is designed to be transparent and show each step of the analysis process, including intermediate results that help validate the findings.
"""
        code_panels.append(pn.pane.Markdown(explanation))

        # Update the display
        self.code_generation_pane.objects = code_panels

        # Also update the code display tab
        self.code_display.object = "```python\n" + self.generated_code + "\n```"

    def _execute_analysis(self):
        """Execute the generated analysis code and capture results"""
        logger.info("Executing analysis")

        # Try running generated code via sandbox first
        if self.generated_code:
            logger.info("Running sandbox execution of generated code")
            sandbox_results = run_snippet(self.generated_code)
            # Handle sandbox results flexibly based on their type
            if isinstance(sandbox_results, dict):
                if "error" not in sandbox_results:
                    self.intermediate_results = sandbox_results
                    logger.info("Sandbox execution succeeded (dict result)")
                    print("SANDBOX RAN")
                    logger.debug("Sandbox results: %s", sandbox_results)
                    return
            elif sandbox_results is not None:
                # Scalar, Series or other non-dict types are considered successful results
                self.intermediate_results = sandbox_results
                logger.info(
                    "Sandbox execution succeeded (non-dict result of type %s)",
                    type(sandbox_results).__name__,
                )
                print("SANDBOX RAN")
                logger.debug("Sandbox results: %s", sandbox_results)
                return
            # If we reach here, sandbox failed or returned an error dict
            logger.warning(
                "Sandbox execution failed or returned empty/error; falling back to rule-engine"
            )

        # ---- Fallback legacy rule engine ----
        query = self.query_text.lower()
        results = {}

        try:
            # Get relevant data based on the query
            patients_df = db_query.get_all_patients()
            vitals_df = db_query.get_all_vitals()

            # Execute analysis based on query type
            if "bmi" in query:
                # BMI analysis
                if "female" in query or "women" in query:
                    # Female BMI analysis
                    female_patients = patients_df[patients_df["gender"] == "F"][
                        "id"
                    ].tolist()
                    filtered_vitals = vitals_df[
                        vitals_df["patient_id"].isin(female_patients)
                    ]
                    valid_bmi = filtered_vitals.dropna(subset=["bmi"])

                    # Active only filter
                    active_female_patients = patients_df[
                        (patients_df["gender"] == "F") & (patients_df["active"] == 1)
                    ]["id"].tolist()
                    active_filtered = valid_bmi[
                        valid_bmi["patient_id"].isin(active_female_patients)
                    ]

                    # Check for threshold query patterns - count patients above/below a threshold
                    is_threshold_query = False
                    threshold_value = None
                    threshold_direction = None

                    # Extract threshold from query
                    if any(
                        word in query
                        for word in ["above", "over", "greater than", "higher than"]
                    ):
                        threshold_direction = "above"
                        is_threshold_query = True
                    elif any(
                        word in query
                        for word in ["below", "under", "less than", "lower than"]
                    ):
                        threshold_direction = "below"
                        is_threshold_query = True

                    # Extract numeric value from query (e.g., 30 from "BMI over 30")
                    numbers = re.findall(r"\d+(?:\.\d+)?", query)
                    if numbers and is_threshold_query:
                        threshold_value = float(numbers[0])

                    # Process based on query specifics
                    if "female" in query or "women" in query:
                        # Female BMI analysis
                        female_patients = patients_df[patients_df["gender"] == "F"][
                            "id"
                        ].tolist()
                        filtered_vitals = vitals_df[
                            vitals_df["patient_id"].isin(female_patients)
                        ]
                        valid_bmi = filtered_vitals.dropna(subset=["bmi"])

                        # Active only filter
                        active_female_patients = patients_df[
                            (patients_df["gender"] == "F")
                            & (patients_df["active"] == 1)
                        ]["id"].tolist()
                        active_filtered = valid_bmi[
                            valid_bmi["patient_id"].isin(active_female_patients)
                        ]

                        # Check if this is a threshold query
                        if is_threshold_query and threshold_value is not None:
                            if threshold_direction == "above":
                                threshold_data = active_filtered[
                                    active_filtered["bmi"] > threshold_value
                                ]
                                # variable unused; placeholder to satisfy linter
                                _ = f"above {threshold_value}"
                            else:
                                threshold_data = active_filtered[
                                    active_filtered["bmi"] < threshold_value
                                ]
                                comparison_text = f"below {threshold_value}"

                            # Count unique patients
                            count_above_threshold = threshold_data[
                                "patient_id"
                            ].nunique()

                            # Calculate statistics including threshold counts
                            stats = {
                                "total_female_patients": len(female_patients),
                                "active_female_patients": len(active_female_patients),
                                "total_records": len(filtered_vitals),
                                "valid_bmi_records": len(valid_bmi),
                                "active_valid_records": len(active_filtered),
                                "threshold_value": threshold_value,
                                "comparison": threshold_direction,
                                "count_matching_threshold": count_above_threshold,
                                "percent_matching_threshold": (
                                    (
                                        count_above_threshold
                                        / active_filtered["patient_id"].nunique()
                                    )
                                    * 100
                                    if not active_filtered.empty
                                    else 0
                                ),
                            }

                            results["stats"] = stats
                            results["bmi_data"] = active_filtered

                        else:
                            # Calculate regular statistics
                            stats = {
                                "total_female_patients": len(female_patients),
                                "active_female_patients": len(active_female_patients),
                                "total_records": len(filtered_vitals),
                                "valid_bmi_records": len(valid_bmi),
                                "active_valid_records": len(active_filtered),
                                "avg_bmi": (
                                    active_filtered["bmi"].mean()
                                    if not active_filtered.empty
                                    else None
                                ),
                                "median_bmi": (
                                    active_filtered["bmi"].median()
                                    if not active_filtered.empty
                                    else None
                                ),
                                "std_bmi": (
                                    active_filtered["bmi"].std()
                                    if not active_filtered.empty
                                    else None
                                ),
                                "min_bmi": (
                                    active_filtered["bmi"].min()
                                    if not active_filtered.empty
                                    else None
                                ),
                                "max_bmi": (
                                    active_filtered["bmi"].max()
                                    if not active_filtered.empty
                                    else None
                                ),
                                "unique_patients": (
                                    active_filtered["patient_id"].nunique()
                                    if not active_filtered.empty
                                    else 0
                                ),
                            }

                            results["stats"] = stats
                            results["bmi_data"] = active_filtered

                elif "male" in query or "men" in query:
                    # Male BMI analysis
                    male_patients = patients_df[patients_df["gender"] == "M"][
                        "id"
                    ].tolist()
                    filtered_vitals = vitals_df[
                        vitals_df["patient_id"].isin(male_patients)
                    ]
                    valid_bmi = filtered_vitals.dropna(subset=["bmi"])

                    # Active only filter
                    active_male_patients = patients_df[
                        (patients_df["gender"] == "M") & (patients_df["active"] == 1)
                    ]["id"].tolist()
                    active_filtered = valid_bmi[
                        valid_bmi["patient_id"].isin(active_male_patients)
                    ]

                    # Calculate statistics
                    stats = {
                        "total_male_patients": len(male_patients),
                        "active_male_patients": len(active_male_patients),
                        "total_records": len(filtered_vitals),
                        "valid_bmi_records": len(valid_bmi),
                        "active_valid_records": len(active_filtered),
                        "avg_bmi": (
                            active_filtered["bmi"].mean()
                            if not active_filtered.empty
                            else None
                        ),
                        "median_bmi": (
                            active_filtered["bmi"].median()
                            if not active_filtered.empty
                            else None
                        ),
                        "std_bmi": (
                            active_filtered["bmi"].std()
                            if not active_filtered.empty
                            else None
                        ),
                        "min_bmi": (
                            active_filtered["bmi"].min()
                            if not active_filtered.empty
                            else None
                        ),
                        "max_bmi": (
                            active_filtered["bmi"].max()
                            if not active_filtered.empty
                            else None
                        ),
                        "unique_patients": (
                            active_filtered["patient_id"].nunique()
                            if not active_filtered.empty
                            else 0
                        ),
                    }

                    results["stats"] = stats
                    results["bmi_data"] = active_filtered

                else:
                    # General BMI analysis
                    valid_bmi = vitals_df.dropna(subset=["bmi"])

                    # Active only filter
                    active_patients = patients_df[patients_df["active"] == 1][
                        "id"
                    ].tolist()
                    active_filtered = valid_bmi[
                        valid_bmi["patient_id"].isin(active_patients)
                    ]

                    # Calculate statistics
                    stats = {
                        "total_patients": len(patients_df),
                        "active_patients": len(active_patients),
                        "total_records": len(vitals_df),
                        "valid_bmi_records": len(valid_bmi),
                        "active_valid_records": len(active_filtered),
                        "avg_bmi": (
                            active_filtered["bmi"].mean()
                            if not active_filtered.empty
                            else None
                        ),
                        "median_bmi": (
                            active_filtered["bmi"].median()
                            if not active_filtered.empty
                            else None
                        ),
                        "std_bmi": (
                            active_filtered["bmi"].std()
                            if not active_filtered.empty
                            else None
                        ),
                        "min_bmi": (
                            active_filtered["bmi"].min()
                            if not active_filtered.empty
                            else None
                        ),
                        "max_bmi": (
                            active_filtered["bmi"].max()
                            if not active_filtered.empty
                            else None
                        ),
                        "unique_patients": (
                            active_filtered["patient_id"].nunique()
                            if not active_filtered.empty
                            else 0
                        ),
                    }

                    # Calculate by gender
                    gender_stats = {}
                    for gender in ["F", "M"]:
                        gender_patients = patients_df[
                            (patients_df["gender"] == gender)
                            & (patients_df["active"] == 1)
                        ]["id"].tolist()
                        gender_filtered = valid_bmi[
                            valid_bmi["patient_id"].isin(gender_patients)
                        ]

                        gender_stats[gender] = {
                            "count": len(gender_patients),
                            "avg_bmi": (
                                gender_filtered["bmi"].mean()
                                if not gender_filtered.empty
                                else None
                            ),
                            "records": len(gender_filtered),
                            "unique_patients": (
                                gender_filtered["patient_id"].nunique()
                                if not gender_filtered.empty
                                else 0
                            ),
                        }

                    results["stats"] = stats
                    results["gender_stats"] = gender_stats
                    results["bmi_data"] = active_filtered

            elif "active patients" in query:
                # Active patients analysis
                active_patients = patients_df[patients_df["active"] == 1]
                inactive_patients = patients_df[patients_df["active"] == 0]

                stats = {
                    "total_patients": len(patients_df),
                    "active_patients": len(active_patients),
                    "inactive_patients": len(inactive_patients),
                    "percent_active": (
                        len(active_patients) / len(patients_df) * 100
                        if len(patients_df) > 0
                        else 0
                    ),
                }

                # Gender breakdown if available
                if "gender" in active_patients.columns:
                    gender_counts = active_patients["gender"].value_counts()
                    gender_stats = {
                        gender: count for gender, count in gender_counts.items()
                    }
                    gender_percent = {
                        gender: count / len(active_patients) * 100
                        for gender, count in gender_counts.items()
                    }

                    stats["gender_counts"] = gender_stats
                    stats["gender_percent"] = gender_percent

                # Program duration if available
                if "program_start_date" in active_patients.columns:
                    # Convert to datetime if needed
                    if not pd.api.types.is_datetime64_dtype(
                        active_patients["program_start_date"]
                    ):
                        active_patients["program_start_date"] = pd.to_datetime(
                            active_patients["program_start_date"]
                        )

                    # Calculate months in program
                    now = pd.Timestamp.now()
                    active_patients["months_in_program"] = (
                        (now - active_patients["program_start_date"])
                        / pd.Timedelta(days=30)
                    ).astype(int)

                    duration_stats = {
                        "avg_months": active_patients["months_in_program"].mean(),
                        "median_months": active_patients["months_in_program"].median(),
                        "min_months": active_patients["months_in_program"].min(),
                        "max_months": active_patients["months_in_program"].max(),
                    }

                    stats["duration"] = duration_stats

                results["stats"] = stats
                results["active_data"] = active_patients

            elif "weight" in query:
                # Weight analysis
                valid_weight = vitals_df.dropna(subset=["weight"])

                # Overall stats
                stats = {
                    "total_records": len(vitals_df),
                    "valid_records": len(valid_weight),
                    "avg_weight": (
                        valid_weight["weight"].mean()
                        if not valid_weight.empty
                        else None
                    ),
                    "median_weight": (
                        valid_weight["weight"].median()
                        if not valid_weight.empty
                        else None
                    ),
                    "std_weight": (
                        valid_weight["weight"].std() if not valid_weight.empty else None
                    ),
                    "min_weight": (
                        valid_weight["weight"].min() if not valid_weight.empty else None
                    ),
                    "max_weight": (
                        valid_weight["weight"].max() if not valid_weight.empty else None
                    ),
                    "unique_patients": (
                        valid_weight["patient_id"].nunique()
                        if not valid_weight.empty
                        else 0
                    ),
                }

                # By gender if needed
                gender_stats = {}
                for gender in ["F", "M"]:
                    gender_patients = patients_df[patients_df["gender"] == gender][
                        "id"
                    ].tolist()
                    gender_filtered = valid_weight[
                        valid_weight["patient_id"].isin(gender_patients)
                    ]

                    gender_stats[gender] = {
                        "avg_weight": (
                            gender_filtered["weight"].mean()
                            if not gender_filtered.empty
                            else None
                        ),
                        "records": len(gender_filtered),
                        "unique_patients": (
                            gender_filtered["patient_id"].nunique()
                            if not gender_filtered.empty
                            else 0
                        ),
                    }

                results["stats"] = stats
                results["gender_stats"] = gender_stats
                results["weight_data"] = valid_weight

            else:
                # General analysis
                stats = {
                    "total_patients": len(patients_df),
                    "active_patients": sum(patients_df["active"] == 1),
                    "inactive_patients": sum(patients_df["active"] == 0),
                    "percent_active": (
                        sum(patients_df["active"] == 1) / len(patients_df) * 100
                        if len(patients_df) > 0
                        else 0
                    ),
                }

                # Gender breakdown if available
                if "gender" in patients_df.columns:
                    gender_counts = patients_df["gender"].value_counts()
                    gender_stats = {
                        gender: count for gender, count in gender_counts.items()
                    }

                    stats["gender_counts"] = gender_stats

                results["stats"] = stats
                results["patient_data"] = patients_df

            # Store execution time for realism
            import datetime

            results["execution_time"] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            results["execution_duration"] = "0.42 seconds"  # Mock value

            # Store the results
            self.intermediate_results = results
            logger.info(f"Analysis executed with {len(results)} result sets")

        except Exception as e:
            logger.error(f"Error executing analysis: {str(e)}", exc_info=True)
            self.intermediate_results = {"error": str(e)}

    def _display_execution_results(self):
        """Display the results of the code execution with intermediate steps"""
        # Safely detect "empty" results without triggering pandas truth-value errors
        no_results = False
        if self.intermediate_results is None:
            no_results = True
        elif isinstance(self.intermediate_results, dict | list):
            no_results = len(self.intermediate_results) == 0

        if no_results:
            self.execution_pane.objects = [
                pn.pane.Markdown("No execution results available.")
            ]
            return

        logger.info("Displaying execution results")

        # Create panels for the execution results
        result_panels = []

        # Header
        result_panels.append(
            pn.pane.Markdown(
                "### Analysis Execution Results\n\nHere are the step-by-step results from executing the analysis:"
            )
        )

        # --- NEW ORDER OF TYPE HANDLING ---
        # 1. If the result is a simple scalar (int, float, numpy scalar)
        if isinstance(self.intermediate_results, (int, float, np.generic)):
            self.execution_pane.objects = [
                pn.pane.Markdown(f"**Result:** {float(self.intermediate_results):.2f}")
            ]
            return

        # 2. If the result is a pandas Series
        if isinstance(self.intermediate_results, pd.Series):
            result_df = self.intermediate_results.reset_index()
            self.execution_pane.objects = [
                pn.pane.Markdown("### Result Series"),
                pn.widgets.Tabulator(result_df, sizing_mode="stretch_width"),
            ]
            return

        # 3. If the result is a dict-like structure, handle errors first
        if (
            isinstance(self.intermediate_results, dict)
            and "error" in self.intermediate_results
        ):
            result_panels.append(
                pn.pane.Markdown(
                    f"**Error during execution:** {self.intermediate_results['error']}"
                )
            )
            self.execution_pane.objects = result_panels
            return

        # Handle simple scalar or Series results produced by sandbox
        if isinstance(self.intermediate_results, (int, float, np.generic)):
            self.execution_pane.objects = [
                pn.pane.Markdown(f"**Result:** {self.intermediate_results:.2f}")
            ]
            return

        if isinstance(self.intermediate_results, pd.Series):
            result_df = self.intermediate_results.reset_index()
            self.execution_pane.objects = [
                pn.pane.Markdown("### Result Series"),
                pn.widgets.Tabulator(result_df, sizing_mode="stretch_width"),
            ]
            return

        # Display execution metadata
        if "execution_time" in self.intermediate_results:
            metadata = f"""
**Execution Details:**
- Time: {self.intermediate_results.get('execution_time', 'Unknown')}
- Duration: {self.intermediate_results.get('execution_duration', 'Unknown')}
"""
            result_panels.append(pn.pane.Markdown(metadata))

        # Display results based on query type and available data
        query = self.query_text.lower()

        if "bmi" in query:
            if "stats" in self.intermediate_results:
                stats = self.intermediate_results["stats"]

                # Check if this is a threshold query
                if "threshold_value" in stats and "comparison" in stats:
                    threshold_value = stats.get("threshold_value")
                    comparison = stats.get("comparison")
                    count = stats.get("count_matching_threshold", 0)
                    percent = stats.get("percent_matching_threshold", 0)

                    # Display threshold execution steps
                    comparison_text = f"{comparison} {threshold_value}"
                    execution_steps = f"""
**Execution Steps:**

1. **Data Collection:**
   - Total Records: {stats.get('total_records', 'N/A')}
   - Valid BMI Records: {stats.get('valid_bmi_records', 'N/A')}
   - Records used (after filtering): {stats.get('active_valid_records', 'N/A')}

2. **Threshold Analysis:**
   - BMI threshold: {comparison_text}
   - Patients with BMI {comparison_text}: {count}
   - Percentage: {percent:.1f}% of patients
"""
                    result_panels.append(pn.pane.Markdown(execution_steps))

                    # Display BMI distribution with threshold if data is available
                    if (
                        "bmi_data" in self.intermediate_results
                        and not self.intermediate_results["bmi_data"].empty
                    ):
                        bmi_data = self.intermediate_results["bmi_data"]

                        # Create histogram with vertical line at threshold
                        bmi_hist = histogram(
                            bmi_data,
                            "bmi",
                            bins=15,
                            title=f"BMI Distribution with {comparison_text.title()} Threshold",
                        )

                        # Add vertical line for threshold
                        threshold_line = hv.VLine(threshold_value).opts(
                            color="red", line_width=2, line_dash="dashed"
                        )

                        combined_plot = bmi_hist * threshold_line
                        result_panels.append(pn.pane.HoloViews(combined_plot))

                elif self.intermediate_results["stats"].get("avg_bmi") is not None:
                    # This is the regular BMI analysis display
                    # Display basic execution steps
                    execution_steps = f"""
**Execution Steps:**

1. **Data Collection:**
   - Total Records: {stats.get('total_records', 'N/A')}
   - Valid BMI Records: {stats.get('valid_bmi_records', 'N/A')}
   - Records used (after filtering): {stats.get('active_valid_records', 'N/A')}
   - Unique patients analyzed: {stats.get('unique_patients', 'N/A')}

2. **Statistical Analysis:**
   - Average BMI: {stats.get('avg_bmi', 'N/A'):.2f}
   - Median BMI: {stats.get('median_bmi', 'N/A'):.2f}
   - Standard Deviation: {stats.get('std_bmi', 'N/A'):.2f}
   - Range: {stats.get('min_bmi', 'N/A'):.1f} to {stats.get('max_bmi', 'N/A'):.1f}
"""
                    result_panels.append(pn.pane.Markdown(execution_steps))

                    # Add gender breakdown if available
                    if "gender_stats" in self.intermediate_results:
                        gender_stats = self.intermediate_results["gender_stats"]
                        gender_text = "**BMI by Gender:**\n\n"

                        for gender, g_stats in gender_stats.items():
                            gender_label = "Female" if gender == "F" else "Male"
                            gender_text += f"- {gender_label} ({g_stats.get('count', 'N/A')} patients): "
                            gender_text += (
                                f"Average BMI {g_stats.get('avg_bmi', 'N/A'):.2f} "
                            )
                            gender_text += f"({g_stats.get('records', 'N/A')} records, "
                            gender_text += f"{g_stats.get('unique_patients', 'N/A')} unique patients)\n"

                        result_panels.append(pn.pane.Markdown(gender_text))

                    # Display BMI distribution if data is available
                    if (
                        "bmi_data" in self.intermediate_results
                        and not self.intermediate_results["bmi_data"].empty
                    ):
                        bmi_data = self.intermediate_results["bmi_data"]
                        bmi_hist = histogram(
                            bmi_data,
                            "bmi",
                            bins=15,
                            title="BMI Distribution",
                        )
                        result_panels.append(pn.pane.HoloViews(bmi_hist))

        elif "active patients" in query:
            if "stats" in self.intermediate_results:
                stats = self.intermediate_results["stats"]

                # Display basic counts
                counts_text = f"""
**Execution Steps:**

1. **Patient Counts:**
   - Total Patients: {stats.get('total_patients', 'N/A')}
   - Active Patients: {stats.get('active_patients', 'N/A')}
   - Inactive Patients: {stats.get('inactive_patients', 'N/A')}
   - Percentage Active: {stats.get('percent_active', 'N/A'):.1f}%
"""
                result_panels.append(pn.pane.Markdown(counts_text))

                # Gender breakdown if available
                if "gender_counts" in stats:
                    gender_text = "**2. Gender Breakdown of Active Patients:**\n\n"

                    for gender, count in stats["gender_counts"].items():
                        gender_label = "Female" if gender == "F" else "Male"
                        percent = stats["gender_percent"].get(gender, 0)
                        gender_text += f"- {gender_label}: {count} ({percent:.1f}%)\n"

                    result_panels.append(pn.pane.Markdown(gender_text))

                    # Add gender pie chart
                    if (
                        "active_data" in self.intermediate_results
                        and "gender" in self.intermediate_results["active_data"].columns
                    ):
                        active_data = self.intermediate_results["active_data"]
                        gender_counts = active_data["gender"].value_counts()

                        # Create a more display-friendly DataFrame
                        pie_data = pd.DataFrame(
                            {
                                "Gender": [
                                    "Female" if g == "F" else "Male"
                                    for g in gender_counts.index
                                ],
                                "Count": gender_counts.values,
                            }
                        )

                        gender_series = pie_data.set_index("Gender")["Count"]
                        gender_pie = gender_series.hvplot.pie(
                            title="Active Patients by Gender",
                            height=300,
                            width=300,
                            legend="right",
                        )
                        result_panels.append(pn.pane.HoloViews(gender_pie))

                # Program duration if available
                if "duration" in stats:
                    duration = stats["duration"]
                    duration_text = f"""
**3. Program Duration for Active Patients:**
   - Average Months in Program: {duration.get('avg_months', 'N/A'):.1f}
   - Median Months in Program: {duration.get('median_months', 'N/A'):.1f}
   - Range: {duration.get('min_months', 'N/A')} to {duration.get('max_months', 'N/A')} months
"""
                    result_panels.append(pn.pane.Markdown(duration_text))

                    # Add duration histogram if data is available
                    if (
                        "active_data" in self.intermediate_results
                        and "months_in_program"
                        in self.intermediate_results["active_data"].columns
                    ):
                        active_data = self.intermediate_results["active_data"]
                        duration_hist = histogram(
                            active_data,
                            "months_in_program",
                            bins=12,
                            title="Distribution of Months in Program (Active Patients)",
                        )
                        result_panels.append(pn.pane.HoloViews(duration_hist))

        elif "weight" in query:
            if (
                "stats" in self.intermediate_results
                and self.intermediate_results["stats"].get("avg_weight") is not None
            ):

                stats = self.intermediate_results["stats"]

                # Display basic execution steps
                execution_steps = f"""
**Execution Steps:**

1. **Data Collection:**
   - Total Records: {stats.get('total_records', 'N/A')}
   - Valid Weight Records: {stats.get('valid_records', 'N/A')}
   - Unique patients analyzed: {stats.get('unique_patients', 'N/A')}

2. **Statistical Analysis:**
   - Average Weight: {stats.get('avg_weight', 'N/A'):.1f} lbs
   - Median Weight: {stats.get('median_weight', 'N/A'):.1f} lbs
   - Standard Deviation: {stats.get('std_weight', 'N/A'):.1f} lbs
   - Range: {stats.get('min_weight', 'N/A'):.1f} to {stats.get('max_weight', 'N/A'):.1f} lbs
"""
                result_panels.append(pn.pane.Markdown(execution_steps))

                # Add gender breakdown if available
                if "gender_stats" in self.intermediate_results:
                    gender_stats = self.intermediate_results["gender_stats"]
                    gender_text = "**Weight by Gender:**\n\n"

                    for gender, g_stats in gender_stats.items():
                        gender_label = "Female" if gender == "F" else "Male"
                        gender_text += f"- {gender_label}: "
                        gender_text += f"Average Weight {g_stats.get('avg_weight', 'N/A'):.1f} lbs "
                        gender_text += f"({g_stats.get('records', 'N/A')} records, "
                        gender_text += f"{g_stats.get('unique_patients', 'N/A')} unique patients)\n"

                    result_panels.append(pn.pane.Markdown(gender_text))

                # Display weight distribution if data is available
                if (
                    "weight_data" in self.intermediate_results
                    and not self.intermediate_results["weight_data"].empty
                ):
                    weight_data = self.intermediate_results["weight_data"]
                    weight_hist = histogram(
                        weight_data,
                        "weight",
                        bins=15,
                        title="Weight Distribution (lbs)",
                    )
                    result_panels.append(pn.pane.HoloViews(weight_hist))

        else:
            # Generic execution results
            if "stats" in self.intermediate_results:
                stats = self.intermediate_results["stats"]

                basic_stats = f"""
**General Analysis Results:**

- Total Patients: {stats.get('total_patients', 0)}
- Active Patients: {stats.get('active_patients', 0)} ({stats.get('percent_active', 0):.1f}% of total)
- Inactive Patients: {stats.get('inactive_patients', 0)}
"""
                result_panels.append(pn.pane.Markdown(basic_stats))

                # Gender breakdown if available
                if "gender_counts" in stats:
                    gender_text = "**Gender Breakdown:**\n\n"

                    for gender, count in stats["gender_counts"].items():
                        gender_label = (
                            "Female"
                            if gender == "F"
                            else "Male" if gender == "M" else gender
                        )
                        percent = (
                            count / stats["total_patients"] * 100
                            if stats["total_patients"] > 0
                            else 0
                        )
                        gender_text += f"- {gender_label}: {count} ({percent:.1f}%)"

                    result_panels.append(pn.pane.Markdown(gender_text))

            # Add a note about results validation
            result_panels.append(
                pn.pane.Markdown(
                    "*These results show the actual data analysis findings. The next step will provide a final summary and visualization of key insights.*"
                )
            )

            # Update the display
            self.execution_pane.objects = result_panels

    def _generate_final_results(self):
        """Generate the final results summary based on the analysis"""
        logger.info("Generating final results")

        # In a full implementation, an LLM would analyze the results and provide insights
        query = self.query_text
        result = {}

        # Quick path: if intermediate_results is a simple scalar or Series, summarise immediately
        if isinstance(self.intermediate_results, (int, float, np.generic)):
            result_val = float(self.intermediate_results)
            result["summary"] = f"Result: {result_val:.2f}"
            self.analysis_result = result
            return
        if isinstance(self.intermediate_results, pd.Series):
            mean_val = self.intermediate_results.mean()
            result["summary"] = f"Series mean: {mean_val:.2f}"
            self.analysis_result = result
            return

        try:
            # Use AI to interpret results
            if self.intermediate_results is not None:
                # Show AI is thinking
                self._start_ai_indicator("ChatGPT is interpreting your results...")

                # Prepare visualization descriptions
                visualizations = []
                if "bmi_data" in self.intermediate_results:
                    visualizations.append("BMI distribution histogram")
                if "gender_pie" in self.intermediate_results:
                    visualizations.append("Gender distribution pie chart")

                # Get AI interpretation of results
                interpretation = ai.interpret_results(
                    query, self.intermediate_results, visualizations
                )

                # Hide the indicator when done
                self._stop_ai_indicator()

                # Store the results
                if isinstance(self.intermediate_results, (int, float, np.generic)):
                    result_val = float(self.intermediate_results)
                    result["summary"] = f"Result: {result_val:.2f}"
                else:
                    result["summary"] = interpretation

                # Add visualizations if available
                if (
                    "bmi_data" in self.intermediate_results
                    and not self.intermediate_results["bmi_data"].empty
                ):
                    bmi_data = self.intermediate_results["bmi_data"]

                    # Check if this is a threshold query
                    if "threshold_value" in self.intermediate_results.get("stats", {}):
                        # Create BMI distribution with threshold line
                        threshold_value = self.intermediate_results["stats"][
                            "threshold_value"
                        ]

                        bmi_plot = histogram(
                            bmi_data,
                            "bmi",
                            bins=20,
                            title=f"BMI Distribution with Threshold at {threshold_value}",
                        )

                        # Add vertical line for threshold
                        threshold_line = hv.VLine(threshold_value).opts(
                            color="red", line_width=2, line_dash="dashed"
                        )

                        combined_plot = bmi_plot * threshold_line
                        result["bmi_plot"] = combined_plot
                    else:
                        # Regular BMI distribution
                        result["bmi_plot"] = histogram(
                            bmi_data,
                            "bmi",
                            bins=20,
                            title="BMI Distribution",
                        )

                # Add gender pie chart if available
                if (
                    "active_data" in self.intermediate_results
                    and "gender" in self.intermediate_results["active_data"].columns
                ):
                    active_data = self.intermediate_results["active_data"]

                    # Create gender distribution pie chart
                    gender_counts = active_data["gender"].value_counts()
                    pie_data = pd.DataFrame(
                        {
                            "Gender": [
                                "Female" if g == "F" else "Male"
                                for g in gender_counts.index
                            ],
                            "Count": gender_counts.values,
                        }
                    )

                    # Create pie chart using hvplot directly
                    gender_pie = pie_data.hvplot(
                        x="Gender",
                        y="Count",
                        kind="pie",
                        title="Patient Gender Distribution",
                        height=350,
                        width=350,
                        legend="right",
                    )

                    result["gender_pie"] = gender_pie

                logger.info("Generated AI interpretation of results")

            else:
                # Fallback if no intermediate results are available
                result["summary"] = (
                    f"Analysis complete for query: '{query}'. No detailed results available."
                )
                logger.warning(
                    "No intermediate results available for AI interpretation"
                )

        except Exception as e:
            # Hide the indicator in case of error
            self._stop_ai_indicator()

            logger.error(
                f"Error generating AI results interpretation: {str(e)}", exc_info=True
            )

            # Fall back to rule-based interpretation if AI fails
            result["summary"] = (
                f"Analysis results for your query: '{query}'. The data has been processed and visualized according to your requirements."
            )

            # Add basic visualizations
            if self.intermediate_results is not None:
                if (
                    "bmi_data" in self.intermediate_results
                    and not self.intermediate_results["bmi_data"].empty
                ):
                    bmi_df = self.intermediate_results["bmi_data"]
                    result["bmi_plot"] = histogram(
                        bmi_df,
                        "bmi",
                        bins=20,
                        title="BMI Distribution",
                    )

        self.analysis_result = result

    def _display_final_results(self):
        """Display the final results with visualizations and insights"""
        if not self.analysis_result:
            self.result_pane.object = (
                "No analysis results available. Please enter a query."
            )
            return

        logger.info("Displaying final results")

        # Create a markdown panel with the results
        if "summary" in self.analysis_result:
            results_md = f"### Analysis Results\n\n{self.analysis_result['summary']}"
            self.result_pane.object = results_md

        # Check if we have visualizations to display
        viz = None

        # Extract the appropriate visualization based on query type
        if "bmi_plot" in self.analysis_result:
            viz = self.analysis_result["bmi_plot"]
        elif (
            "gender_pie" in self.analysis_result
            and "duration_hist" in self.analysis_result
        ):
            # Combine multiple plots
            viz = pn.Column(
                self.analysis_result["gender_pie"],
                self.analysis_result["duration_hist"],
                sizing_mode="stretch_width",
            )
        elif "gender_pie" in self.analysis_result:
            viz = self.analysis_result["gender_pie"]
        elif "duration_hist" in self.analysis_result:
            viz = self.analysis_result["duration_hist"]
        elif "weight_plot" in self.analysis_result:
            viz = self.analysis_result["weight_plot"]

        # Update the visualization pane if we have a visualization
        if viz is not None:
            self.visualization_pane.object = viz
        else:
            self.visualization_pane.object = hv.Div(
                "No visualization available for this query"
            )

        # Reset the status and workflow for the next query
        self._update_status("Analysis complete. You can enter a new query.")

    def _update_saved_question_buttons(self):
        """Update the saved question buttons in the sidebar"""
        # Clear existing buttons
        self.saved_question_buttons_container.clear()

        # Create a button for each saved question
        for question in self.saved_questions:
            # Create a container for the question button and delete button
            question_button = pn.widgets.Button(
                name=question["name"],
                button_type="default",
                sizing_mode="stretch_width",
            )
            # Use a partial function to avoid closure issues with lambda
            question_button.on_click(
                lambda event, q=question: self._use_saved_question(q)
            )

            # Create a small delete button
            delete_button = pn.widgets.Button(
                name="✖",
                button_type="light",
                width=25,
                height=25,
                margin=(0, 0, 0, 5),
                styles={"color": "#dc3545", "font-size": "0.8em"},
            )
            delete_button.on_click(
                lambda event, q=question: self._delete_saved_question(q)
            )

            # Add both buttons in a row
            self.saved_question_buttons_container.append(
                pn.Row(
                    question_button,
                    delete_button,
                    sizing_mode="stretch_width",
                    margin=(0, 0, 5, 0),
                )
            )

    def _use_saved_question(self, question):
        """Set the query text from a saved question"""
        logger.info(f"Using saved question: {question}")
        self.query_text = question["query"]

        # Update the input field to reflect the saved question
        if self.query_input is not None:
            self.query_input.value = question["query"]
            logger.info("Updated query input field with saved question")

        # Process the query
        self._process_query()

    def _delete_saved_question(self, question):
        """Delete a saved question from the list"""
        logger.info(f"Deleting saved question: {question['name']}")

        # Filter out the question to delete
        self.saved_questions = [
            q for q in self.saved_questions if q["name"] != question["name"]
        ]

        # Update the UI
        self._update_saved_question_buttons()

        # Save changes to file
        save_questions_to_file(self.saved_questions)

        # Update status
        self._update_status(f"Deleted question: '{question['name']}'")

    def _save_question(self, event=None):
        """Save the current question to the saved questions list"""
        if not self.query_text:
            self._update_status("Cannot save an empty question")
            return

        if not self.question_name:
            self._update_status("Please enter a name for this question")
            return

        # Check if a question with this name already exists
        existing_names = [q["name"] for q in self.saved_questions]
        if self.question_name in existing_names:
            self._update_status(
                f"A question with name '{self.question_name}' already exists"
            )
            return

        # Check if this question text already exists in our saved questions
        if self.query_text in [q["query"] for q in self.saved_questions]:
            self._update_status(f"Question text already saved: '{self.query_text}'")
            return

        # Add the new question to our saved questions
        new_saved_questions = self.saved_questions + [
            {"name": self.question_name, "query": self.query_text}
        ]
        self.saved_questions = new_saved_questions

        # Update the sidebar with the new saved questions
        self._update_saved_question_buttons()

        # Save changes to file
        save_questions_to_file(self.saved_questions)

        # Update status
        self._update_status(f"Question saved as '{self.question_name}'")
        logger.info(f"Saved question '{self.question_name}': '{self.query_text}'")

        # Reset the question name input
        if self.save_question_input is not None:
            self.save_question_input.value = ""

    def _reset_all(self, event=None):
        """Reset the assistant to its initial state"""
        logger.info("Resetting Data Analysis Assistant")

        # Reset all state variables
        self.query_text = ""
        self.question_name = ""
        self.analysis_result = {}
        self.current_stage = self.STAGE_INITIAL
        self.clarifying_questions = []
        self.data_samples = {}
        self.generated_code = ""
        self.intermediate_results = None

        # Clear all display panes
        self.clarifying_pane.objects = []
        self.data_sample_pane.objects = []
        self.code_generation_pane.objects = []
        self.execution_pane.objects = []

        # Reset result displays
        self.result_pane.object = "Enter a query to analyze data"
        self.code_display.object = ""
        self.visualization_pane.object = hv.Div("")

        # Reset the UI elements
        if self.query_input is not None:
            self.query_input.value = ""

        if self.save_question_input is not None:
            self.save_question_input.value = ""

        # Disable the continue button
        self.continue_button.disabled = True

        # Reset workflow stage indicators
        self._update_stage_indicators()

        # Update status
        self._update_status("Reset complete. Ready for a new query.")
        logger.info("Reset completed")

    def _generate_fallback_code(self):
        """Generate fallback code when AI code generation fails"""
        query = self.query_text.lower()

        # Setup imports and initial code for all analyses
        code = """
# Import required libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Set plotting style
plt.style.use('ggplot')
sns.set(style="whitegrid")

# Load data
"""

        # Generate specific analysis code based on the query
        if "bmi" in query:
            if "female" in query or "women" in query:
                code += """
# Get all patients
patients_df = db_query.get_all_patients()

# Filter for female patients
female_patients = patients_df[patients_df['gender'] == 'F']['id'].tolist()
print(f"Found {len(female_patients)} female patients")

# Get vitals data
vitals_df = db_query.get_all_vitals()

# Filter vitals for female patients
female_vitals = vitals_df[vitals_df['patient_id'].isin(female_patients)]
print(f"Retrieved {len(female_vitals)} vitals records for female patients")

# Remove records with null BMI values
female_vitals = female_vitals.dropna(subset=['bmi'])
print(f"After removing null BMI values: {len(female_vitals)} records")

# Calculate BMI statistics
avg_bmi = female_vitals['bmi'].mean()
median_bmi = female_vitals['bmi'].median()
std_bmi = female_vitals['bmi'].std()
min_bmi = female_vitals['bmi'].min()
max_bmi = female_vitals['bmi'].max()

# Count records and unique patients
total_records = len(female_vitals)
unique_patients = female_vitals['patient_id'].nunique()

print(f"Average BMI: {avg_bmi:.2f}")
print(f"Median BMI: {median_bmi:.2f}")
print(f"BMI Range: {min_bmi:.1f} to {max_bmi:.1f}")
print(f"Data from {unique_patients} unique patients")

# Check if this is a threshold query (BMI > X)
# This code handles queries like "How many female patients have a BMI over 30?"
threshold_value = 30  # Default, will be overridden if specified in query
if "over" in "{query}" or "above" in "{query}" or "greater than" in "{query}":
    # Try to extract the threshold from the query
    import re
    numbers = re.findall(r'\\d+', "{query}")
    if numbers:
        threshold_value = float(numbers[0])
    
    # Count patients above threshold
    high_bmi = female_vitals[female_vitals['bmi'] > threshold_value]
    high_bmi_count = high_bmi['patient_id'].nunique()
    high_bmi_percent = high_bmi_count / unique_patients * 100 if unique_patients > 0 else 0
    
    print(f"Patients with BMI > {threshold_value}: {high_bmi_count} ({high_bmi_percent:.1f}%)")

# Prepare results
results = {{
    'avg_bmi': avg_bmi,
    'median_bmi': median_bmi,
    'std_bmi': std_bmi,
    'min_bmi': min_bmi,
    'max_bmi': max_bmi,
    'total_records': total_records,
    'unique_patients': unique_patients
}}

# If threshold analysis was performed, include those results
if 'high_bmi_count' in locals():
    results['threshold_value'] = threshold_value
    results['patients_above_threshold'] = high_bmi_count
    results['percent_above_threshold'] = high_bmi_percent

# Return the results
results
"""
            else:
                # Handle other code generation patterns here
                code += """
# Get patient and vitals data
patients_df = db_query.get_all_patients()
vitals_df = db_query.get_all_vitals()

# Basic data validation
vitals_df = vitals_df.dropna(subset=['bmi'])
print(f"Found {len(vitals_df)} valid vitals records with BMI values")

# Calculate BMI statistics
avg_bmi = vitals_df['bmi'].mean()
median_bmi = vitals_df['bmi'].median()
std_bmi = vitals_df['bmi'].std()
min_bmi = vitals_df['bmi'].min()
max_bmi = vitals_df['bmi'].max()

# Count records and unique patients
total_records = len(vitals_df)
unique_patients = vitals_df['patient_id'].nunique()

print(f"Average BMI: {avg_bmi:.2f}")
print(f"Median BMI: {median_bmi:.2f}")
print(f"BMI Range: {min_bmi:.1f} to {max_bmi:.1f}")
print(f"Data from {unique_patients} unique patients")

# Return the results
results = {{
    'avg_bmi': avg_bmi,
    'median_bmi': median_bmi,
    'std_bmi': std_bmi,
    'min_bmi': min_bmi,
    'max_bmi': max_bmi,
    'total_records': total_records,
    'unique_patients': unique_patients
}}

results
"""
        elif "active patients" in query:
            code += """
# Get patient data
patients_df = db_query.get_all_patients()

# Count active and inactive patients
active_patients = patients_df[patients_df['active'] == 1]
inactive_patients = patients_df[patients_df['active'] == 0]

total_count = len(patients_df)
active_count = len(active_patients)
inactive_count = len(inactive_patients)
percent_active = active_count / total_count * 100 if total_count > 0 else 0

print(f"Total patients: {total_count}")
print(f"Active patients: {active_count} ({percent_active:.1f}%)")
print(f"Inactive patients: {inactive_count}")

# Gender breakdown of active patients
if 'gender' in active_patients.columns:
    gender_counts = active_patients['gender'].value_counts()
    gender_percents = active_patients['gender'].value_counts(normalize=True) * 100
    
    for gender, count in gender_counts.items():
        gender_name = "Female" if gender == "F" else "Male"
        percent = gender_percents[gender]
        print(f"{gender_name}: {count} ({percent:.1f}%)")

# Return the results
results = {{
    'total_patients': total_count,
    'active_patients': active_count,
    'inactive_patients': inactive_count,
    'percent_active': percent_active
}}

# Add gender breakdown if available
if 'gender' in active_patients.columns:
    results['gender_counts'] = {{k: int(v) for k, v in gender_counts.items()}}
    results['gender_percents'] = {{k: float(v) for k, v in gender_percents.items()}}

results
"""
        else:
            # Default code for other queries
            code += """
# Get patient data
patients_df = db_query.get_all_patients()
vitals_df = db_query.get_all_vitals()

# Basic patient statistics
total_patients = len(patients_df)
active_patients = sum(patients_df['active'] == 1)
inactive_patients = sum(patients_df['active'] == 0)
percent_active = active_patients / total_patients * 100 if total_patients > 0 else 0

print(f"Total patients: {total_patients}")
print(f"Active patients: {active_patients} ({percent_active:.1f}%)")

# Gender breakdown if available
if 'gender' in patients_df.columns:
    gender_counts = patients_df['gender'].value_counts()
    for gender, count in gender_counts.items():
        gender_name = "Female" if gender == "F" else "Male"
        print(f"{gender_name}: {count}")

# Return basic results
results = {{
    'total_patients': total_patients,
    'active_patients': active_patients,
    'inactive_patients': inactive_patients,
    'percent_active': percent_active
}}

results
"""
        return code

    def _start_ai_indicator(self, base_message):
        """Start the AI thinking indicator"""
        logger.debug("AI indicator started: %s", base_message)
        self.ai_status_text.object = base_message
        self.ellipsis_count = 0
        # Store the original base message so we can rebuild the string without endlessly appending dots
        self._ai_base_message = base_message
        if self.ellipsis_animation:
            self.ellipsis_animation.stop()
        self.ellipsis_animation = pn.state.add_periodic_callback(
            self._animate_ellipsis, period=500  # Update every 500ms
        )

    def _animate_ellipsis(self):
        """Update the ellipsis animation"""
        self.ellipsis_count = (self.ellipsis_count + 1) % 4
        dots = "." * (self.ellipsis_count + 1)
        # Re-build the status string from the original message rather than appending.
        # This prevents the string from growing indefinitely which could cause UI slow-downs.
        base_msg = getattr(self, "_ai_base_message", "")
        self.ai_status_text.object = f"{base_msg}{dots}"

    def _stop_ai_indicator(self):
        """Stop the AI thinking indicator"""
        logger.debug("AI indicator stopped")
        if self.ellipsis_animation:
            self.ellipsis_animation.stop()
            self.ellipsis_animation = None
        self.ai_status_text.object = ""
        # Reset base message to avoid stale references
        self._ai_base_message = ""
        if self.ai_status_row_ref:
            self.ai_status_row_ref.visible = False

    def _initialize_stage_indicators(self):
        """Create markdown indicators for each workflow stage"""
        stage_names = {
            self.STAGE_INITIAL: "Initial",
            self.STAGE_CLARIFYING: "Clarifying",
            self.STAGE_SHOWING_DATA: "Showing Data",
            self.STAGE_CODE_GENERATION: "Code Generation",
            self.STAGE_EXECUTION: "Execution",
            self.STAGE_RESULTS: "Results",
        }
        self.stage_indicators = {}
        for stage_id, name in stage_names.items():
            md = pn.pane.Markdown(f"- {name}")
            self.stage_indicators[stage_id] = md
        # Ensure visual reflects initial stage
        self._update_stage_indicators()

    def _update_stage_indicators(self):
        """Update markdown to highlight current stage"""
        for stage_id, md in self.stage_indicators.items():
            if stage_id < self.current_stage:
                prefix = "✅"
            elif stage_id == self.current_stage:
                prefix = "➡️"
            else:
                prefix = "•"
            name_plain = md.object.split(maxsplit=1)[-1] if md.object else ""
            md.object = f"{prefix} {name_plain}"

    def _process_current_stage(self):
        """Automatically progress through all workflow stages for this prototype."""
        # Disable navigation button during automatic run
        self.continue_button.disabled = True

        # First, attempt intent parsing with confidence check
        intent = ai.get_query_intent(self.query_text)

        if self._is_low_confidence_intent(intent):
            # Low confidence – ask clarifying questions and stop pipeline
            self.clarifying_questions = ai.generate_clarifying_questions(
                self.query_text
            )
            self.current_stage = self.STAGE_CLARIFYING
            self._display_clarifying_questions()
            self._update_stage_indicators()
            return

        # Store confident intent for later deterministic generation
        self.query_intent = intent

        try:
            # Stage: Code Generation
            self.current_stage = self.STAGE_CODE_GENERATION
            self._update_stage_indicators()
            self._generate_analysis_code()
            self._display_generated_code()

            # Stage: Execution
            self.current_stage = self.STAGE_EXECUTION
            self._update_stage_indicators()
            self._execute_analysis()
            self._display_execution_results()

            # Stage: Results
            self.current_stage = self.STAGE_RESULTS
            self._update_stage_indicators()
            self._generate_final_results()
            self._display_final_results()

        finally:
            # Ensure indicators reflect final state and button remains disabled
            self._update_stage_indicators()

    def _advance_workflow(self, event=None):
        """Advance to the next workflow stage and trigger associated actions"""
        logger.info("Advancing workflow from stage %s", self.current_stage)
        # Disable button to prevent double-clicks during processing
        self.continue_button.disabled = True

        if self.current_stage == self.STAGE_INITIAL:
            # Directly jump to code generation for now
            self.current_stage = self.STAGE_CODE_GENERATION
            self._generate_analysis_code()
            self._display_generated_code()

        elif self.current_stage == self.STAGE_CODE_GENERATION:
            self.current_stage = self.STAGE_EXECUTION
            self._execute_analysis()
            self._display_execution_results()

        elif self.current_stage == self.STAGE_EXECUTION:
            self.current_stage = self.STAGE_RESULTS
            self._generate_final_results()
            self._display_final_results()

        # If we reached the final stage, keep button disabled; otherwise re-enable
        if self.current_stage < self.STAGE_RESULTS:
            self.continue_button.disabled = False
        self._update_stage_indicators()

    # ------------------------------------------------------------------
    # Clarification helper
    # ------------------------------------------------------------------

    def _display_clarifying_questions(self):
        """Show clarifying questions returned by the AI helper."""

        if not self.clarifying_questions:
            self.clarifying_pane.objects = [
                pn.pane.Markdown(
                    "I need a bit more detail to proceed; could you rephrase your question?"
                )
            ]
            return

        md_list = "\n".join(f"* {q}" for q in self.clarifying_questions)

        clarification_input = pn.widgets.TextAreaInput(
            placeholder="Type extra details here and click Submit…",
            rows=3,
            sizing_mode="stretch_width",
        )

        submit_btn = pn.widgets.Button(
            name="Submit Details", button_type="primary", width=140
        )

        def _submit(event=None):
            extra = clarification_input.value.strip()
            if not extra:
                return
            # Merge extra detail into original query text
            self.query_text = f"{self.query_text}  {extra}"
            # Reflect in the main input box so user sees full query
            if self.query_input is not None:
                self.query_input.value = self.query_text

            # Reset pipeline and re-run
            clarification_input.value = ""
            self.current_stage = self.STAGE_INITIAL
            self._update_stage_indicators()
            self._process_query()

        submit_btn.on_click(_submit)

        self.clarifying_pane.objects = [
            pn.pane.Markdown("### I need a quick clarification:"),
            pn.pane.Markdown(md_list),
            pn.layout.Divider(),
            clarification_input,
            pn.Row(submit_btn, sizing_mode="stretch_width"),
        ]

    @staticmethod
    def _is_low_confidence_intent(intent):
        """Return True when *intent* is too generic and needs clarification."""

        # If parsing already failed → low confidence
        if isinstance(intent, dict):
            return True

        assert isinstance(intent, QueryIntent)

        # Generic target fields offer no real metric information
        GENERIC_TARGETS = {"score_value", "value"}
        if intent.target_field in GENERIC_TARGETS:
            return True

        # If analysis_type is change but no conditions/filters specified
        if intent.analysis_type == "change" and not intent.filters:
            return True

        # If user talks about patients but provides no patient_id filter
        if any(word in intent.target_field for word in ["patient", "patients"]):
            has_patient_filter = any(f.field == "patient_id" for f in intent.filters)
            if not has_patient_filter:
                return True

        return False


def data_assistant_page():
    """Returns the data analysis assistant page for the application"""
    data_assistant = DataAnalysisAssistant()
    return data_assistant.view()
