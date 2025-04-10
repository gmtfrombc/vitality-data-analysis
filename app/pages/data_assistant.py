"""
Data Analysis Assistant Page

This page provides interactive data analysis capabilities using natural language queries.
"""

import panel as pn
import param
import pandas as pd
import hvplot.pandas
import holoviews as hv
import numpy as np
import logging
import db_query
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('data_assistant')

# Initialize rendering backend for HoloViews plots
hv.extension('bokeh')
pn.extension('tabulator')
pn.extension('plotly')


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
        default=STAGE_INITIAL, doc="Current stage in the analysis workflow")

    # Data for the workflow stages
    clarifying_questions = param.List(
        default=[], doc="List of questions to clarify user intent")
    data_samples = param.Dict(default={}, doc="Sample data to show the user")
    generated_code = param.String(
        default="", doc="Generated Python code for analysis")
    intermediate_results = param.Dict(
        default={}, doc="Results from intermediate steps")

    example_queries = param.ListSelector(default=[], objects=[
        "How many active patients are in the program?",
        "What is the average weight of patients?",
        "What is the average BMI of female patients?",
        "What is the average BMI of male patients?",
        "Show me the distribution of BMI across all patients",
        "Compare blood pressure values for patients with high vs. normal A1C",
        "What percentage of patients showed improvement in their vital signs?",
        "Which patients have not had a visit in the last 3 months?",
    ])

    def __init__(self, **params):
        super().__init__(**params)

        # Results display panes
        self.result_pane = pn.pane.Markdown("Enter a query to analyze data")
        self.code_display = pn.pane.Markdown("")
        self.visualization_pane = pn.pane.HoloViews(hv.Div(''))

        # Status and interaction
        self.status_message = "Ready to analyze data"
        self.status_display = None
        self.query_input = None

        # Workflow stage displays
        self.workflow_indicator = pn.pane.Markdown(
            "### Analysis Workflow Status")
        self.stage_indicators = {}

        # Interactive components for each stage
        self.clarifying_pane = pn.Column(pn.pane.Markdown(""))
        self.data_sample_pane = pn.Column(pn.pane.Markdown(""))
        self.code_generation_pane = pn.Column(pn.pane.Markdown(""))
        self.execution_pane = pn.Column(pn.pane.Markdown(""))

        # Buttons for workflow navigation
        self.continue_button = pn.widgets.Button(
            name="Continue",
            button_type="primary",
            disabled=True,
            width=100
        )
        self.continue_button.on_click(self._advance_workflow)

        # Initialize display content
        self._initialize_stage_indicators()

    def view(self):
        """Generate the data analysis assistant view"""

        # Create title and description
        title = pn.pane.Markdown(
            "# Data Analysis Assistant", sizing_mode="stretch_width")
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
            
            **Examples:** Click on any example query below to try it out.
            """
        )

        # Create query input with button
        self.query_input = pn.widgets.TextAreaInput(
            name="Enter your question:",
            placeholder="e.g., What is the average BMI of active patients?",
            value=self.query_text,
            rows=3,
            sizing_mode="stretch_width"
        )

        # Add a watcher to update the query_text parameter when the input changes
        def update_query_text(event):
            self.query_text = event.new
            logger.info(f"Query text updated to: {self.query_text}")

        self.query_input.param.watch(update_query_text, 'value')

        # Analyze button
        analyze_button = pn.widgets.Button(
            name="Analyze",
            button_type="primary",
            sizing_mode="fixed",
            width=100
        )

        # Update the button click handler to use the current input value
        def on_analyze_click(event):
            logger.info(
                f"Analyze button clicked with query: {self.query_text}")
            # Reset workflow and start from the beginning
            self.current_stage = self.STAGE_INITIAL
            self._update_stage_indicators()
            self._process_query(event)

        analyze_button.on_click(on_analyze_click)

        # Create example queries buttons
        example_queries_title = pn.pane.Markdown("### Example Queries:")
        example_buttons = []

        for query in self.example_queries:
            btn = pn.widgets.Button(
                name=query,
                button_type="default",
                sizing_mode="stretch_width"
            )
            btn.on_click(lambda event, q=query: self._use_example_query(q))
            example_buttons.append(btn)

        example_queries_panel = pn.Column(
            example_queries_title,
            *example_buttons,
            sizing_mode="stretch_width"
        )

        # Workflow progress display
        workflow_indicators = pn.Column(
            self.workflow_indicator,
            *[indicator for _,
                indicator in sorted(self.stage_indicators.items())],
            sizing_mode="stretch_width"
        )

        # Stage-specific content panels
        workflow_content = pn.Column(
            self.clarifying_pane,
            self.data_sample_pane,
            self.code_generation_pane,
            self.execution_pane,
            sizing_mode="stretch_width"
        )

        # Navigation buttons
        nav_buttons = pn.Row(
            self.continue_button,
            sizing_mode="stretch_width",
            align="end"
        )

        # Create tabs for results, code, and visualizations
        result_tabs = pn.Tabs(
            ("Results", self.result_pane),
            ("Code", self.code_display),
            ("Visualization", self.visualization_pane),
            dynamic=True
        )

        # Status indicator
        self.status_display = pn.pane.Markdown(
            f"**Status:** {self.status_message}")

        # Combine everything in a layout
        input_row = pn.Row(
            pn.Column(self.query_input, sizing_mode="stretch_width"),
            pn.Spacer(width=10),
            analyze_button,
            sizing_mode="stretch_width"
        )

        # Workflow panel
        workflow_panel = pn.Column(
            workflow_indicators,
            pn.layout.Divider(),
            workflow_content,
            nav_buttons,
            sizing_mode="stretch_width",
            css_classes=["workflow-panel"]
        )

        # Main content
        main_content = pn.Column(
            title,
            description,
            pn.layout.Divider(),
            input_row,
            pn.layout.Divider(),
            self.status_display,
            workflow_panel,
            pn.layout.Divider(),
            result_tabs,
            sizing_mode="stretch_width"
        )

        # Create sidebar with example queries
        sidebar = pn.Column(
            example_queries_panel,
            sizing_mode="stretch_width",
            width=300
        )

        # Combine main content and sidebar
        layout = pn.Row(
            sidebar,
            pn.layout.HSpacer(width=20),
            main_content,
            sizing_mode="stretch_both"
        )

        return layout

    def _use_example_query(self, query):
        """Set the query text from an example query"""
        logger.info(f"Using example query: {query}")
        self.query_text = query

        # Update the input field to reflect the example query
        if self.query_input is not None:
            self.query_input.value = query
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
        self.visualization_pane.object = hv.Div('')

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

        # Mock responses based on query types
        if "active patients" in query:
            # Mock getting active patients
            patients_df = db_query.get_all_patients()
            active_count = len(patients_df[patients_df['active'] == 1])

            # Store the result
            self.analysis_result = {
                "type": "count",
                "value": active_count,
                "title": "Active Patients",
                "description": f"There are {active_count} active patients in the program.",
                "code": "# Python code to count active patients\npatients_df = db_query.get_all_patients()\nactive_count = len(patients_df[patients_df['active'] == 1])",
                "visualization": self._create_count_visualization(active_count, "Active Patients")
            }

        elif "average weight" in query:
            # Get actual weight data
            vitals_df = db_query.get_all_vitals()

            # Filter if gender is specified
            if "female" in query or "women" in query:
                logger.info("Filtering for female patients")
                patients_df = db_query.get_all_patients()
                female_patients = patients_df[patients_df['gender'] == 'F']['id'].tolist(
                )
                vitals_df = vitals_df[vitals_df['patient_id'].isin(
                    female_patients)]
                title = "Average Weight (Female Patients)"
            elif "male" in query or "men" in query:
                logger.info("Filtering for male patients")
                patients_df = db_query.get_all_patients()
                male_patients = patients_df[patients_df['gender'] == 'M']['id'].tolist(
                )
                vitals_df = vitals_df[vitals_df['patient_id'].isin(
                    male_patients)]
                title = "Average Weight (Male Patients)"
            else:
                title = "Average Weight (All Patients)"

            # Calculate average
            avg_weight = round(vitals_df['weight'].mean(), 1)
            count = len(vitals_df['patient_id'].unique())

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
                "visualization": self._create_histogram(vitals_df, 'weight', f"Weight Distribution (lbs) - {count} patients")
            }

        elif "bmi" in query:
            # Get real BMI data from database
            vitals_df = db_query.get_all_vitals()

            # Filter only records with valid BMI values
            vitals_df = vitals_df.dropna(subset=['bmi'])

            # Filter if gender is specified
            if "female" in query or "women" in query:
                logger.info("Filtering BMI for female patients")
                patients_df = db_query.get_all_patients()
                female_patients = patients_df[patients_df['gender'] == 'F']['id'].tolist(
                )
                logger.info(f"Found {len(female_patients)} female patients")
                vitals_df = vitals_df[vitals_df['patient_id'].isin(
                    female_patients)]
                title = "BMI Distribution (Female Patients)"
                filtered_desc = "female patients"
            elif "male" in query or "men" in query:
                logger.info("Filtering BMI for male patients")
                patients_df = db_query.get_all_patients()
                male_patients = patients_df[patients_df['gender'] == 'M']['id'].tolist(
                )
                logger.info(f"Found {len(male_patients)} male patients")
                vitals_df = vitals_df[vitals_df['patient_id'].isin(
                    male_patients)]
                title = "BMI Distribution (Male Patients)"
                filtered_desc = "male patients"
            else:
                title = "BMI Distribution (All Patients)"
                filtered_desc = "all patients"

            # Calculate statistics
            logger.info(
                f"Calculating BMI stats based on {len(vitals_df)} records")
            avg_bmi = round(vitals_df['bmi'].mean(), 1)
            count = len(vitals_df['patient_id'].unique())

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
                "visualization": self._create_histogram(vitals_df, 'bmi', f"BMI Distribution - {count} patients")
            }

        else:
            # Default response for other queries
            self.analysis_result = {
                "type": "text",
                "title": "Query Analysis",
                "description": f"Your query: '{self.query_text}' would be analyzed here with real data.",
                "code": "# This is where the Python code to answer your query would appear\n# Based on modern AI workflow:\n# 1. Query understanding\n# 2. Data retrieval\n# 3. Analysis\n# 4. Visualization",
                "visualization": None
            }

    def _update_results_display(self):
        """Update the display with analysis results"""
        result = self.analysis_result
        logger.info(
            f"Updating results display with result: {result.get('title')}")

        # Update the results pane
        result_text = f"""
        ### {result.get('title', 'Analysis Results')}
        
        {result.get('description', 'No results available')}
        """
        self.result_pane.object = result_text
        logger.info(
            f"Results pane updated with text length: {len(result_text)}")

        # Update the code display
        code_text = f"""
        ```python
        {result.get('code', '# No code available')}
        ```
        """
        self.code_display.object = code_text
        logger.info(f"Code display updated with text length: {len(code_text)}")

        # Update visualization
        viz = result.get('visualization')
        if viz is not None:
            logger.info("Visualization found, updating visualization pane")
            self.visualization_pane.object = viz
        else:
            logger.info("No visualization found, displaying placeholder")
            self.visualization_pane.object = hv.Div(
                'No visualization available')

    def _create_count_visualization(self, count, title):
        """Create a simple bar chart for count data"""
        data = pd.DataFrame({'Category': ['Active'], 'Count': [count]})
        return data.hvplot.bar(x='Category', y='Count', title=title, height=400)

    def _create_histogram(self, df, column, title):
        """Create a histogram for the specified column"""
        return df.hvplot.hist(
            y=column,
            bins=10,
            title=title,
            height=400,
            alpha=0.7,
            legend=False
        )

    def _initialize_stage_indicators(self):
        """Initialize the stage indicators for the workflow display"""
        stages = [
            (self.STAGE_INITIAL, "Query Understanding"),
            (self.STAGE_CLARIFYING, "Clarification"),
            (self.STAGE_SHOWING_DATA, "Data Preview"),
            (self.STAGE_CODE_GENERATION, "Code Generation"),
            (self.STAGE_EXECUTION, "Execution"),
            (self.STAGE_RESULTS, "Results Analysis")
        ]

        for stage_id, stage_name in stages:
            indicator = pn.pane.Markdown(
                f"◯ {stage_name}",
                css_classes=['workflow-stage'],
                width=200
            )
            self.stage_indicators[stage_id] = indicator

        # Set the initial stage
        self._update_stage_indicators()

    def _update_stage_indicators(self):
        """Update the stage indicators based on the current stage"""
        for stage_id, indicator in self.stage_indicators.items():
            if stage_id < self.current_stage:
                # Completed stage
                indicator.object = f"✓ {indicator.object.replace('◯ ', '').replace('⦿ ', '')}"
            elif stage_id == self.current_stage:
                # Current stage
                indicator.object = f"⦿ {indicator.object.replace('◯ ', '').replace('✓ ', '')}"
            else:
                # Future stage
                indicator.object = f"◯ {indicator.object.replace('⦿ ', '').replace('✓ ', '')}"

    def _advance_workflow(self, event=None):
        """Advance to the next stage in the workflow"""
        if self.current_stage < self.STAGE_RESULTS:
            self.current_stage += 1
            self._update_stage_indicators()
            self._process_current_stage()
        else:
            # Reset workflow if we're at the end
            self.current_stage = self.STAGE_INITIAL
            self._update_stage_indicators()
            self._update_status("Ready for a new query")

    def _process_current_stage(self):
        """Process the current stage of the analysis workflow"""
        try:
            if self.current_stage == self.STAGE_INITIAL:
                # Initial query processing
                self._update_status("Understanding your query...")
                self._generate_clarifying_questions()
                self.current_stage = self.STAGE_CLARIFYING
                self._update_stage_indicators()
                self._process_current_stage()

            elif self.current_stage == self.STAGE_CLARIFYING:
                # Show clarifying questions
                self._update_status("Clarifying your question...")
                self._display_clarifying_questions()

            elif self.current_stage == self.STAGE_SHOWING_DATA:
                # Show relevant data samples
                self._update_status("Retrieving relevant data samples...")
                self._retrieve_data_samples()
                self._display_data_samples()

            elif self.current_stage == self.STAGE_CODE_GENERATION:
                # Generate code for analysis
                self._update_status("Generating analysis code...")
                self._generate_analysis_code()
                self._display_generated_code()

            elif self.current_stage == self.STAGE_EXECUTION:
                # Execute the analysis
                self._update_status("Executing analysis...")
                self._execute_analysis()
                self._display_execution_results()

            elif self.current_stage == self.STAGE_RESULTS:
                # Show final results and visualizations
                self._update_status("Analyzing results...")
                self._generate_final_results()
                self._display_final_results()

            # Enable continue button after processing (except for the last stage)
            self.continue_button.disabled = (
                self.current_stage == self.STAGE_RESULTS)

        except Exception as e:
            logger.error(
                f"Error in workflow stage {self.current_stage}: {str(e)}", exc_info=True)
            self._update_status(f"Error: {str(e)}")
            self.current_stage = self.STAGE_INITIAL

    def _generate_clarifying_questions(self):
        """Generate clarifying questions based on the user's query"""
        logger.info(
            f"Generating clarifying questions for: '{self.query_text}'")

        query = self.query_text.lower()

        # In a full implementation, an LLM would generate these questions
        # For now, we'll use predetermined questions based on query keywords
        questions = []

        if "bmi" in query:
            if "female" in query or "women" in query:
                questions = [
                    "Are you looking for the average BMI or the full distribution?",
                    "Would you like to filter by age group?",
                    "Are you interested in comparing to male patients?",
                    "Should only active patients be included?"
                ]
            elif "male" in query or "men" in query:
                questions = [
                    "Are you looking for the average BMI or the full distribution?",
                    "Would you like to filter by age group?",
                    "Are you interested in comparing to female patients?",
                    "Should only active patients be included?"
                ]
            else:
                questions = [
                    "Would you like to filter by gender?",
                    "Are you looking for the average BMI or the full distribution?",
                    "Should only active patients be included?",
                    "Would you like to see BMI categories (underweight, normal, overweight, obese)?"
                ]
        elif "weight" in query:
            questions = [
                "Are you interested in weight changes over time?",
                "Would you like to filter by gender?",
                "Should only active patients be included?",
                "Would you like to see weight relative to height (BMI)?"
            ]
        elif "active patients" in query:
            questions = [
                "Do you want the total count or a breakdown by demographics?",
                "Are you interested in how long they've been in the program?",
                "Would you like to compare with inactive patients?",
                "Do you need any additional metrics about active patients?"
            ]
        else:
            # Default questions for any query
            questions = [
                "Would you like to filter the results by any specific criteria?",
                "Are you looking for a time-based analysis or current data?",
                "Would you like to compare different patient groups?",
                "Should the results include visualizations or just data?"
            ]

        self.clarifying_questions = questions

        # For demonstration purposes, we'll pre-set some answers
        self.clarifying_answers = [
            "I'm interested in the average BMI",
            "No age filter is needed",
            "No need to compare with other groups",
            "Yes, only include active patients"
        ]

        logger.info(f"Generated {len(questions)} clarifying questions")

    def _display_clarifying_questions(self):
        """Display the clarifying questions to the user"""
        if not self.clarifying_questions:
            self.clarifying_pane.objects = [
                pn.pane.Markdown("No clarifying questions needed.")
            ]
            return

        # Create a markdown panel with questions and pre-filled answers
        questions_md = "### Clarifying Questions\n\nTo better understand your query, I'd like to confirm a few details:\n\n"

        for i, (question, answer) in enumerate(zip(self.clarifying_questions, self.clarifying_answers)):
            questions_md += f"**Q{i+1}: {question}**  \n"
            questions_md += f"A: {answer}  \n\n"

        questions_panel = pn.pane.Markdown(questions_md)

        # In a full implementation, we would have interactive widgets for each question
        # For demonstration, we'll use static content with pre-filled answers

        self.clarifying_pane.objects = [
            questions_panel,
            pn.pane.Markdown("*Click Continue to proceed with these answers*")
        ]

    def _retrieve_data_samples(self):
        """Retrieve relevant data samples based on the query and clarifications"""
        logger.info("Retrieving data samples")

        query = self.query_text.lower()
        samples = {}

        try:
            # Get patient data
            patients_df = db_query.get_all_patients()

            # Retrieve appropriate sample data based on query
            if "bmi" in query or "weight" in query:
                # Get vitals data for relevant samples
                vitals_df = db_query.get_all_vitals()

                # Handle gender-specific queries
                if "female" in query or "women" in query:
                    female_patients = patients_df[patients_df['gender'] == 'F']['id'].tolist(
                    )
                    filtered_vitals = vitals_df[vitals_df['patient_id'].isin(
                        female_patients)]
                    logger.info(
                        f"Retrieved {len(filtered_vitals)} vitals records for female patients")

                    # Get a sample of the data (first 5 rows)
                    if not filtered_vitals.empty:
                        samples['vitals'] = filtered_vitals.head(5)

                    # Get summary statistics
                    if "bmi" in query and "bmi" in filtered_vitals.columns:
                        valid_bmi = filtered_vitals.dropna(subset=['bmi'])
                        samples['bmi_stats'] = valid_bmi['bmi'].describe()

                elif "male" in query or "men" in query:
                    male_patients = patients_df[patients_df['gender'] == 'M']['id'].tolist(
                    )
                    filtered_vitals = vitals_df[vitals_df['patient_id'].isin(
                        male_patients)]
                    logger.info(
                        f"Retrieved {len(filtered_vitals)} vitals records for male patients")

                    # Get a sample of the data (first 5 rows)
                    if not filtered_vitals.empty:
                        samples['vitals'] = filtered_vitals.head(5)

                    # Get summary statistics
                    if "bmi" in query and "bmi" in filtered_vitals.columns:
                        valid_bmi = filtered_vitals.dropna(subset=['bmi'])
                        samples['bmi_stats'] = valid_bmi['bmi'].describe()
                else:
                    # General vitals data
                    samples['vitals'] = vitals_df.head(5)

                    # Get summary statistics for BMI if relevant
                    if "bmi" in query and "bmi" in vitals_df.columns:
                        valid_bmi = vitals_df.dropna(subset=['bmi'])
                        samples['bmi_stats'] = valid_bmi['bmi'].describe()

            elif "active patients" in query:
                # Get active patients data
                active_patients = patients_df[patients_df['active'] == 1]
                samples['active_patients'] = active_patients.head(5)
                samples['active_count'] = len(active_patients)

            else:
                # Default to sample of general patient data
                samples['patients'] = patients_df.head(5)

        except Exception as e:
            logger.error(
                f"Error retrieving data samples: {str(e)}", exc_info=True)
            samples['error'] = str(e)

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
        sample_panels.append(pn.pane.Markdown(
            "### Data Samples\n\nHere are some relevant data samples to help with your analysis:"))

        # Display samples based on what was retrieved
        if 'error' in self.data_samples:
            sample_panels.append(pn.pane.Markdown(
                f"**Error retrieving samples:** {self.data_samples['error']}"))

        if 'vitals' in self.data_samples:
            sample_panels.append(pn.pane.Markdown("#### Vitals Data Sample:"))
            sample_panels.append(pn.widgets.Tabulator(
                self.data_samples['vitals'],
                pagination='remote',
                page_size=5,
                sizing_mode='stretch_width'
            ))

        if 'bmi_stats' in self.data_samples:
            # Convert the Series to a more display-friendly format
            bmi_stats = self.data_samples['bmi_stats']
            stats_df = pd.DataFrame({
                'Statistic': bmi_stats.index,
                'Value': bmi_stats.values.round(2)
            })

            sample_panels.append(pn.pane.Markdown("#### BMI Statistics:"))
            sample_panels.append(pn.widgets.Tabulator(
                stats_df,
                sizing_mode='stretch_width'
            ))

        if 'active_patients' in self.data_samples:
            sample_panels.append(pn.pane.Markdown(
                "#### Active Patients Sample:"))
            sample_panels.append(pn.widgets.Tabulator(
                self.data_samples['active_patients'],
                pagination='remote',
                page_size=5,
                sizing_mode='stretch_width'
            ))

            if 'active_count' in self.data_samples:
                sample_panels.append(pn.pane.Markdown(
                    f"**Total Active Patients:** {self.data_samples['active_count']}"))

        if 'patients' in self.data_samples:
            sample_panels.append(pn.pane.Markdown(
                "#### General Patient Data:"))
            sample_panels.append(pn.widgets.Tabulator(
                self.data_samples['patients'],
                pagination='remote',
                page_size=5,
                sizing_mode='stretch_width'
            ))

        # Add a note about the data
        sample_panels.append(pn.pane.Markdown(
            "*These samples represent a small subset of the data that will be used for analysis.*"))

        # Update the display
        self.data_sample_pane.objects = sample_panels

    def _generate_analysis_code(self):
        """Generate Python code for the analysis based on the query and clarifications"""
        logger.info("Generating analysis code")

        query = self.query_text.lower()
        code = ""

        # In a real implementation, this code would be generated by an LLM
        # For the demo, we'll generate appropriate code based on the query

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

# Check if we need to filter for active patients only (from clarification)
active_only = True  # Based on user's clarification answer
if active_only:
    active_female_patients = patients_df[(patients_df['gender'] == 'F') & (patients_df['active'] == 1)]['id'].tolist()
    female_vitals = female_vitals[female_vitals['patient_id'].isin(active_female_patients)]
    print(f"After filtering for active patients: {len(female_vitals)} records")

# Calculate average BMI
avg_bmi = female_vitals['bmi'].mean()
median_bmi = female_vitals['bmi'].median()
std_bmi = female_vitals['bmi'].std()

# Get summary statistics
bmi_stats = female_vitals['bmi'].describe()

# Count unique patients
unique_patients = female_vitals['patient_id'].nunique()

print(f"Analysis based on {unique_patients} unique female patients")
print(f"Average BMI: {avg_bmi:.2f}")
print(f"Median BMI: {median_bmi:.2f}")
print(f"Standard Deviation: {std_bmi:.2f}")

# Create BMI distribution visualization
plt.figure(figsize=(10, 6))
sns.histplot(female_vitals['bmi'], kde=True, bins=15)
plt.title('BMI Distribution for Female Patients')
plt.xlabel('BMI')
plt.ylabel('Count')
plt.axvline(avg_bmi, color='red', linestyle='--', label=f'Mean: {avg_bmi:.2f}')
plt.legend()
"""
            elif "male" in query or "men" in query:
                code += """
# Get all patients
patients_df = db_query.get_all_patients()

# Filter for male patients
male_patients = patients_df[patients_df['gender'] == 'M']['id'].tolist()
print(f"Found {len(male_patients)} male patients")

# Get vitals data
vitals_df = db_query.get_all_vitals()

# Filter vitals for male patients
male_vitals = vitals_df[vitals_df['patient_id'].isin(male_patients)]
print(f"Retrieved {len(male_vitals)} vitals records for male patients")

# Remove records with null BMI values
male_vitals = male_vitals.dropna(subset=['bmi'])
print(f"After removing null BMI values: {len(male_vitals)} records")

# Check if we need to filter for active patients only (from clarification)
active_only = True  # Based on user's clarification answer
if active_only:
    active_male_patients = patients_df[(patients_df['gender'] == 'M') & (patients_df['active'] == 1)]['id'].tolist()
    male_vitals = male_vitals[male_vitals['patient_id'].isin(active_male_patients)]
    print(f"After filtering for active patients: {len(male_vitals)} records")

# Calculate average BMI
avg_bmi = male_vitals['bmi'].mean()
median_bmi = male_vitals['bmi'].median()
std_bmi = male_vitals['bmi'].std()

# Get summary statistics
bmi_stats = male_vitals['bmi'].describe()

# Count unique patients
unique_patients = male_vitals['patient_id'].nunique()

print(f"Analysis based on {unique_patients} unique male patients")
print(f"Average BMI: {avg_bmi:.2f}")
print(f"Median BMI: {median_bmi:.2f}")
print(f"Standard Deviation: {std_bmi:.2f}")

# Create BMI distribution visualization
plt.figure(figsize=(10, 6))
sns.histplot(male_vitals['bmi'], kde=True, bins=15)
plt.title('BMI Distribution for Male Patients')
plt.xlabel('BMI')
plt.ylabel('Count')
plt.axvline(avg_bmi, color='red', linestyle='--', label=f'Mean: {avg_bmi:.2f}')
plt.legend()
"""
            else:
                code += """
# Get all patients
patients_df = db_query.get_all_patients()

# Get vitals data
vitals_df = db_query.get_all_vitals()

# Remove records with null BMI values
clean_vitals = vitals_df.dropna(subset=['bmi'])
print(f"Total records with BMI data: {len(clean_vitals)}")

# Check if we need to filter for active patients only (from clarification)
active_only = True  # Based on user's clarification answer
if active_only:
    active_patients = patients_df[patients_df['active'] == 1]['id'].tolist()
    clean_vitals = clean_vitals[clean_vitals['patient_id'].isin(active_patients)]
    print(f"After filtering for active patients: {len(clean_vitals)} records")

# Calculate average BMI
avg_bmi = clean_vitals['bmi'].mean()
median_bmi = clean_vitals['bmi'].median()
std_bmi = clean_vitals['bmi'].std()

# Get summary statistics
bmi_stats = clean_vitals['bmi'].describe()

# Count unique patients
unique_patients = clean_vitals['patient_id'].nunique()

print(f"Analysis based on {unique_patients} unique patients")
print(f"Average BMI: {avg_bmi:.2f}")
print(f"Median BMI: {median_bmi:.2f}")
print(f"Standard Deviation: {std_bmi:.2f}")

# Create BMI distribution visualization
plt.figure(figsize=(10, 6))
sns.histplot(clean_vitals['bmi'], kde=True, bins=15)
plt.title('BMI Distribution for All Patients')
plt.xlabel('BMI')
plt.ylabel('Count')
plt.axvline(avg_bmi, color='red', linestyle='--', label=f'Mean: {avg_bmi:.2f}')
plt.legend()

# Optionally, analyze by gender
gender_bmi = clean_vitals.merge(
    patients_df[['id', 'gender']], 
    left_on='patient_id', 
    right_on='id'
)

plt.figure(figsize=(10, 6))
sns.boxplot(x='gender', y='bmi', data=gender_bmi)
plt.title('BMI Distribution by Gender')
plt.xlabel('Gender')
plt.ylabel('BMI')
"""

        elif "active patients" in query:
            code += """
# Get all patients
patients_df = db_query.get_all_patients()

# Count active patients
active_patients = patients_df[patients_df['active'] == 1]
inactive_patients = patients_df[patients_df['active'] == 0]

stats = {
    'total_patients': len(patients_df),
    'active_patients': len(active_patients),
    'inactive_patients': len(inactive_patients),
    'percent_active': len(active_patients) / len(patients_df) * 100 if len(patients_df) > 0 else 0
}

# Gender breakdown if available
if 'gender' in active_patients.columns:
    gender_counts = active_patients['gender'].value_counts()
    gender_stats = {gender: count for gender,
                    count in gender_counts.items()}
    gender_percent = {gender: count / len(active_patients) * 100
                      for gender, count in gender_counts.items()}

    stats['gender_counts'] = gender_stats
    stats['gender_percent'] = gender_percent

# Program duration if available
if 'program_start_date' in active_patients.columns:
    # Convert to datetime if needed
    if not pd.api.types.is_datetime64_dtype(active_patients['program_start_date']):
        active_patients['program_start_date'] = pd.to_datetime(
            active_patients['program_start_date'])

    # Calculate months in program
    now = pd.Timestamp.now()
    active_patients['months_in_program'] = (
        (now - active_patients['program_start_date']) / pd.Timedelta(days=30)).astype(int)

    duration_stats = {
        'avg_months': active_patients['months_in_program'].mean(),
        'median_months': active_patients['months_in_program'].median(),
        'min_months': active_patients['months_in_program'].min(),
        'max_months': active_patients['months_in_program'].max()
    }

    stats['duration'] = duration_stats

results['stats'] = stats
results['active_data'] = active_patients
"""

        elif "weight" in query:
            code += """
# Get all patients
patients_df = db_query.get_all_patients()

# Get vitals data
vitals_df = db_query.get_all_vitals()

# Filter out records with null weight values
clean_vitals = vitals_df.dropna(subset=['weight'])
print(f"Total records with weight data: {len(clean_vitals)}")

# Calculate average weight
avg_weight = clean_vitals['weight'].mean()
median_weight = clean_vitals['weight'].median()
std_weight = clean_vitals['weight'].std()

# Count unique patients
unique_patients = clean_vitals['patient_id'].nunique()

print(f"Analysis based on {unique_patients} unique patients")
print(f"Average weight: {avg_weight:.1f} lbs")
print(f"Median weight: {median_weight:.1f} lbs")
print(f"Standard Deviation: {std_weight:.1f} lbs")

# Create weight distribution visualization
plt.figure(figsize=(10, 6))
sns.histplot(clean_vitals['weight'], kde=True, bins=15)
plt.title('Weight Distribution for All Patients')
plt.xlabel('Weight (lbs)')
plt.ylabel('Count')
plt.axvline(avg_weight, color='red', linestyle='--', label=f'Mean: {avg_weight:.1f}')
plt.legend()

# Analyze by gender if needed
gender_query = False  # Based on clarification answer
if gender_query:
    # Merge patient data to get gender
    gender_weight = clean_vitals.merge(
        patients_df[['id', 'gender']], 
        left_on='patient_id', 
        right_on='id'
    )
    
    # Calculate gender-specific statistics
    gender_stats = gender_weight.groupby('gender')['weight'].agg(['mean', 'median', 'std', 'count'])
    print("\\nWeight statistics by gender:")
    print(gender_stats)
    
    # Visualize weight by gender
    plt.figure(figsize=(10, 6))
    sns.boxplot(x='gender', y='weight', data=gender_weight)
    plt.title('Weight Distribution by Gender')
    plt.xlabel('Gender')
    plt.ylabel('Weight (lbs)')
"""

        else:
            # Generic analysis for other queries
            code += """
# This is a placeholder for the custom analysis that would be generated
# based on your specific query. A real implementation would use an
# AI model to generate code tailored to your exact requirements.

# For demonstration, here's a general analysis of the patient data:

# Get all patients
patients_df = db_query.get_all_patients()
print(f"Total patients: {len(patients_df)}")

# Count active vs inactive
active_count = patients_df['active'].sum()
print(f"Active patients: {active_count}")
print(f"Inactive patients: {len(patients_df) - active_count}")

# Analyze gender distribution if available
if 'gender' in patients_df.columns:
    gender_counts = patients_df['gender'].value_counts()
    print("\\nGender distribution:")
    print(gender_counts)
    
    # Visualize gender distribution
    plt.figure(figsize=(8, 6))
    gender_counts.plot.pie(autopct='%1.1f%%', startangle=90)
    plt.title('Patients by Gender')
    plt.ylabel('')

# Analyze program duration if available
if 'program_start_date' in patients_df.columns:
    # Convert to datetime if needed
    if not pd.api.types.is_datetime64_dtype(patients_df['program_start_date']):
        patients_df['program_start_date'] = pd.to_datetime(patients_df['program_start_date'])
    
    # Calculate months in program for active patients
    now = pd.Timestamp.now()
    active_patients = patients_df[patients_df['active'] == 1].copy()
    active_patients['months_in_program'] = ((now - active_patients['program_start_date']) / pd.Timedelta(days=30)).astype(int)
    
    avg_months = active_patients['months_in_program'].mean()
    
    print(f"\\nProgram duration for active patients:")
    print(f"  Average months in program: {avg_months:.1f}")
    
    # Visualize distribution of program duration
    plt.figure(figsize=(10, 6))
    sns.histplot(active_patients['months_in_program'], bins=12, kde=True)
    plt.title('Distribution of Time in Program for Active Patients')
    plt.xlabel('Months in Program')
    plt.ylabel('Count')
"""

        # Store the generated code
        self.generated_code = code
        logger.info("Generated analysis code")

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
        code_panels.append(pn.pane.Markdown(
            "### Generated Analysis Code\n\nBased on your query and clarifications, I've generated the following Python code to analyze the data:"))

        # Display code in a syntax-highlighted panel using markdown code block
        code_md = f"```python\n{self.generated_code}\n```"
        code_panels.append(pn.pane.Markdown(
            code_md,
            sizing_mode='stretch_width'
        ))

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

        # In a real implementation, we would execute the code in a controlled environment
        # For this demo, we'll simulate execution with pre-calculated results

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
                    female_patients = patients_df[patients_df['gender'] == 'F']['id'].tolist(
                    )
                    filtered_vitals = vitals_df[vitals_df['patient_id'].isin(
                        female_patients)]
                    valid_bmi = filtered_vitals.dropna(subset=['bmi'])

                    # Active only filter
                    active_female_patients = patients_df[(patients_df['gender'] == 'F') &
                                                         (patients_df['active'] == 1)]['id'].tolist()
                    active_filtered = valid_bmi[valid_bmi['patient_id'].isin(
                        active_female_patients)]

                    # Calculate statistics
                    stats = {
                        'total_female_patients': len(female_patients),
                        'active_female_patients': len(active_female_patients),
                        'total_records': len(filtered_vitals),
                        'valid_bmi_records': len(valid_bmi),
                        'active_valid_records': len(active_filtered),
                        'avg_bmi': active_filtered['bmi'].mean() if not active_filtered.empty else None,
                        'median_bmi': active_filtered['bmi'].median() if not active_filtered.empty else None,
                        'std_bmi': active_filtered['bmi'].std() if not active_filtered.empty else None,
                        'min_bmi': active_filtered['bmi'].min() if not active_filtered.empty else None,
                        'max_bmi': active_filtered['bmi'].max() if not active_filtered.empty else None,
                        'unique_patients': active_filtered['patient_id'].nunique() if not active_filtered.empty else 0
                    }

                    results['stats'] = stats
                    results['bmi_data'] = active_filtered

                elif "male" in query or "men" in query:
                    # Male BMI analysis
                    male_patients = patients_df[patients_df['gender'] == 'M']['id'].tolist(
                    )
                    filtered_vitals = vitals_df[vitals_df['patient_id'].isin(
                        male_patients)]
                    valid_bmi = filtered_vitals.dropna(subset=['bmi'])

                    # Active only filter
                    active_male_patients = patients_df[(patients_df['gender'] == 'M') &
                                                       (patients_df['active'] == 1)]['id'].tolist()
                    active_filtered = valid_bmi[valid_bmi['patient_id'].isin(
                        active_male_patients)]

                    # Calculate statistics
                    stats = {
                        'total_male_patients': len(male_patients),
                        'active_male_patients': len(active_male_patients),
                        'total_records': len(filtered_vitals),
                        'valid_bmi_records': len(valid_bmi),
                        'active_valid_records': len(active_filtered),
                        'avg_bmi': active_filtered['bmi'].mean() if not active_filtered.empty else None,
                        'median_bmi': active_filtered['bmi'].median() if not active_filtered.empty else None,
                        'std_bmi': active_filtered['bmi'].std() if not active_filtered.empty else None,
                        'min_bmi': active_filtered['bmi'].min() if not active_filtered.empty else None,
                        'max_bmi': active_filtered['bmi'].max() if not active_filtered.empty else None,
                        'unique_patients': active_filtered['patient_id'].nunique() if not active_filtered.empty else 0
                    }

                    results['stats'] = stats
                    results['bmi_data'] = active_filtered

                else:
                    # General BMI analysis
                    valid_bmi = vitals_df.dropna(subset=['bmi'])

                    # Active only filter
                    active_patients = patients_df[patients_df['active'] == 1]['id'].tolist(
                    )
                    active_filtered = valid_bmi[valid_bmi['patient_id'].isin(
                        active_patients)]

                    # Calculate statistics
                    stats = {
                        'total_patients': len(patients_df),
                        'active_patients': len(active_patients),
                        'total_records': len(vitals_df),
                        'valid_bmi_records': len(valid_bmi),
                        'active_valid_records': len(active_filtered),
                        'avg_bmi': active_filtered['bmi'].mean() if not active_filtered.empty else None,
                        'median_bmi': active_filtered['bmi'].median() if not active_filtered.empty else None,
                        'std_bmi': active_filtered['bmi'].std() if not active_filtered.empty else None,
                        'min_bmi': active_filtered['bmi'].min() if not active_filtered.empty else None,
                        'max_bmi': active_filtered['bmi'].max() if not active_filtered.empty else None,
                        'unique_patients': active_filtered['patient_id'].nunique() if not active_filtered.empty else 0
                    }

                    # Calculate by gender
                    gender_stats = {}
                    for gender in ['F', 'M']:
                        gender_patients = patients_df[(patients_df['gender'] == gender) &
                                                      (patients_df['active'] == 1)]['id'].tolist()
                        gender_filtered = valid_bmi[valid_bmi['patient_id'].isin(
                            gender_patients)]

                        gender_stats[gender] = {
                            'count': len(gender_patients),
                            'avg_bmi': gender_filtered['bmi'].mean() if not gender_filtered.empty else None,
                            'records': len(gender_filtered),
                            'unique_patients': gender_filtered['patient_id'].nunique() if not gender_filtered.empty else 0
                        }

                    results['stats'] = stats
                    results['gender_stats'] = gender_stats
                    results['bmi_data'] = active_filtered

            elif "active patients" in query:
                # Active patients analysis
                active_patients = patients_df[patients_df['active'] == 1]
                inactive_patients = patients_df[patients_df['active'] == 0]

                stats = {
                    'total_patients': len(patients_df),
                    'active_patients': len(active_patients),
                    'inactive_patients': len(inactive_patients),
                    'percent_active': len(active_patients) / len(patients_df) * 100 if len(patients_df) > 0 else 0
                }

                # Gender breakdown if available
                if 'gender' in active_patients.columns:
                    gender_counts = active_patients['gender'].value_counts()
                    gender_stats = {gender: count for gender,
                                    count in gender_counts.items()}
                    gender_percent = {gender: count / len(active_patients) * 100
                                      for gender, count in gender_counts.items()}

                    stats['gender_counts'] = gender_stats
                    stats['gender_percent'] = gender_percent

                # Program duration if available
                if 'program_start_date' in active_patients.columns:
                    # Convert to datetime if needed
                    if not pd.api.types.is_datetime64_dtype(active_patients['program_start_date']):
                        active_patients['program_start_date'] = pd.to_datetime(
                            active_patients['program_start_date'])

                    # Calculate months in program
                    now = pd.Timestamp.now()
                    active_patients['months_in_program'] = (
                        (now - active_patients['program_start_date']) / pd.Timedelta(days=30)).astype(int)

                    duration_stats = {
                        'avg_months': active_patients['months_in_program'].mean(),
                        'median_months': active_patients['months_in_program'].median(),
                        'min_months': active_patients['months_in_program'].min(),
                        'max_months': active_patients['months_in_program'].max()
                    }

                    stats['duration'] = duration_stats

                results['stats'] = stats
                results['active_data'] = active_patients

            elif "weight" in query:
                # Weight analysis
                valid_weight = vitals_df.dropna(subset=['weight'])

                # Overall stats
                stats = {
                    'total_records': len(vitals_df),
                    'valid_records': len(valid_weight),
                    'avg_weight': valid_weight['weight'].mean() if not valid_weight.empty else None,
                    'median_weight': valid_weight['weight'].median() if not valid_weight.empty else None,
                    'std_weight': valid_weight['weight'].std() if not valid_weight.empty else None,
                    'min_weight': valid_weight['weight'].min() if not valid_weight.empty else None,
                    'max_weight': valid_weight['weight'].max() if not valid_weight.empty else None,
                    'unique_patients': valid_weight['patient_id'].nunique() if not valid_weight.empty else 0
                }

                # By gender if needed
                gender_stats = {}
                for gender in ['F', 'M']:
                    gender_patients = patients_df[patients_df['gender'] == gender]['id'].tolist(
                    )
                    gender_filtered = valid_weight[valid_weight['patient_id'].isin(
                        gender_patients)]

                    gender_stats[gender] = {
                        'avg_weight': gender_filtered['weight'].mean() if not gender_filtered.empty else None,
                        'records': len(gender_filtered),
                        'unique_patients': gender_filtered['patient_id'].nunique() if not gender_filtered.empty else 0
                    }

                results['stats'] = stats
                results['gender_stats'] = gender_stats
                results['weight_data'] = valid_weight

            else:
                # General analysis
                stats = {
                    'total_patients': len(patients_df),
                    'active_patients': sum(patients_df['active'] == 1),
                    'inactive_patients': sum(patients_df['active'] == 0),
                    'percent_active': sum(patients_df['active'] == 1) / len(patients_df) * 100 if len(patients_df) > 0 else 0
                }

                # Gender breakdown if available
                if 'gender' in patients_df.columns:
                    gender_counts = patients_df['gender'].value_counts()
                    gender_stats = {gender: count for gender,
                                    count in gender_counts.items()}

                    stats['gender_counts'] = gender_stats

                results['stats'] = stats
                results['patient_data'] = patients_df

            # Store execution time for realism
            import datetime
            results['execution_time'] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            results['execution_duration'] = "0.42 seconds"  # Mock value

            # Store the results
            self.intermediate_results = results
            logger.info(f"Analysis executed with {len(results)} result sets")

        except Exception as e:
            logger.error(f"Error executing analysis: {str(e)}", exc_info=True)
            self.intermediate_results = {'error': str(e)}

    def _display_execution_results(self):
        """Display the results of the code execution with intermediate steps"""
        if not self.intermediate_results:
            self.execution_pane.objects = [
                pn.pane.Markdown("No execution results available.")
            ]
            return

        logger.info("Displaying execution results")

        # Create panels for the execution results
        result_panels = []

        # Header
        result_panels.append(pn.pane.Markdown(
            "### Analysis Execution Results\n\nHere are the step-by-step results from executing the analysis:"))

        # Handle errors if any
        if 'error' in self.intermediate_results:
            result_panels.append(pn.pane.Markdown(
                f"**Error during execution:** {self.intermediate_results['error']}"))
            self.execution_pane.objects = result_panels
            return

        # Display execution metadata
        if 'execution_time' in self.intermediate_results:
            metadata = f"""
**Execution Details:**
- Time: {self.intermediate_results.get('execution_time', 'Unknown')}
- Duration: {self.intermediate_results.get('execution_duration', 'Unknown')}
"""
            result_panels.append(pn.pane.Markdown(metadata))

        # Display results based on query type and available data
        query = self.query_text.lower()

        if "bmi" in query:
            if ('stats' in self.intermediate_results and
                    self.intermediate_results['stats'].get('avg_bmi') is not None):

                stats = self.intermediate_results['stats']

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
                if 'gender_stats' in self.intermediate_results:
                    gender_stats = self.intermediate_results['gender_stats']
                    gender_text = "**BMI by Gender:**\n\n"

                    for gender, g_stats in gender_stats.items():
                        gender_label = "Female" if gender == "F" else "Male"
                        gender_text += f"- {gender_label} ({g_stats.get('count', 'N/A')} patients): "
                        gender_text += f"Average BMI {g_stats.get('avg_bmi', 'N/A'):.2f} "
                        gender_text += f"({g_stats.get('records', 'N/A')} records, "
                        gender_text += f"{g_stats.get('unique_patients', 'N/A')} unique patients)\n"

                    result_panels.append(pn.pane.Markdown(gender_text))

                # Display BMI distribution if data is available
                if 'bmi_data' in self.intermediate_results and not self.intermediate_results['bmi_data'].empty:
                    bmi_data = self.intermediate_results['bmi_data']
                    bmi_hist = bmi_data['bmi'].hvplot.hist(
                        bins=15,
                        height=300,
                        width=500,
                        alpha=0.7,
                        title="BMI Distribution"
                    )
                    result_panels.append(pn.pane.HoloViews(bmi_hist))

        elif "active patients" in query:
            if 'stats' in self.intermediate_results:
                stats = self.intermediate_results['stats']

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
                if 'gender_counts' in stats:
                    gender_text = "**2. Gender Breakdown of Active Patients:**\n\n"

                    for gender, count in stats['gender_counts'].items():
                        gender_label = "Female" if gender == "F" else "Male"
                        percent = stats['gender_percent'].get(gender, 0)
                        gender_text += f"- {gender_label}: {count} ({percent:.1f}%)\n"

                    result_panels.append(pn.pane.Markdown(gender_text))

                    # Add gender pie chart
                    if 'active_data' in self.intermediate_results and 'gender' in self.intermediate_results['active_data'].columns:
                        active_data = self.intermediate_results['active_data']
                        gender_counts = active_data['gender'].value_counts()

                        # Create a more display-friendly DataFrame
                        pie_data = pd.DataFrame({
                            'Gender': ["Female" if g == "F" else "Male" for g in gender_counts.index],
                            'Count': gender_counts.values
                        })

                        gender_pie = pie_data.hvplot.pie(
                            x='Gender',
                            y='Count',
                            height=300,
                            width=300,
                            title="Active Patients by Gender"
                        )
                        result_panels.append(pn.pane.HoloViews(gender_pie))

                # Program duration if available
                if 'duration' in stats:
                    duration = stats['duration']
                    duration_text = f"""
**3. Program Duration for Active Patients:**
   - Average Months in Program: {duration.get('avg_months', 'N/A'):.1f}
   - Median Months in Program: {duration.get('median_months', 'N/A'):.1f}
   - Range: {duration.get('min_months', 'N/A')} to {duration.get('max_months', 'N/A')} months
"""
                    result_panels.append(pn.pane.Markdown(duration_text))

                    # Add duration histogram if data is available
                    if ('active_data' in self.intermediate_results and
                            'months_in_program' in self.intermediate_results['active_data'].columns):
                        active_data = self.intermediate_results['active_data']
                        duration_hist = active_data['months_in_program'].hvplot.hist(
                            bins=12,
                            height=300,
                            width=500,
                            alpha=0.7,
                            title="Distribution of Months in Program (Active Patients)"
                        )
                        result_panels.append(pn.pane.HoloViews(duration_hist))

        elif "weight" in query:
            if ('stats' in self.intermediate_results and
                    self.intermediate_results['stats'].get('avg_weight') is not None):

                stats = self.intermediate_results['stats']

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
                if 'gender_stats' in self.intermediate_results:
                    gender_stats = self.intermediate_results['gender_stats']
                    gender_text = "**Weight by Gender:**\n\n"

                    for gender, g_stats in gender_stats.items():
                        gender_label = "Female" if gender == "F" else "Male"
                        gender_text += f"- {gender_label}: "
                        gender_text += f"Average Weight {g_stats.get('avg_weight', 'N/A'):.1f} lbs "
                        gender_text += f"({g_stats.get('records', 'N/A')} records, "
                        gender_text += f"{g_stats.get('unique_patients', 'N/A')} unique patients)\n"

                    result_panels.append(pn.pane.Markdown(gender_text))

                # Display weight distribution if data is available
                if 'weight_data' in self.intermediate_results and not self.intermediate_results['weight_data'].empty:
                    weight_data = self.intermediate_results['weight_data']
                    weight_hist = weight_data['weight'].hvplot.hist(
                        bins=15,
                        height=300,
                        width=500,
                        alpha=0.7,
                        title="Weight Distribution (lbs)"
                    )
                    result_panels.append(pn.pane.HoloViews(weight_hist))

        else:
            # Generic execution results
            if 'stats' in self.intermediate_results:
                stats = self.intermediate_results['stats']

                basic_stats = f"""
**General Analysis Results:**

- Total Patients: {stats.get('total_patients', 0)}
- Active Patients: {stats.get('active_patients', 0)} ({stats.get('percent_active', 0):.1f}% of total)
- Inactive Patients: {stats.get('inactive_patients', 0)}
"""
                result_panels.append(pn.pane.Markdown(basic_stats))

                # Gender breakdown if available
                if 'gender_counts' in stats:
                    gender_text = "**Gender Breakdown:**\n\n"

                    for gender, count in stats['gender_counts'].items():
                        gender_label = "Female" if gender == "F" else "Male" if gender == "M" else gender
                        percent = count / \
                            stats['total_patients'] * \
                            100 if stats['total_patients'] > 0 else 0
                        gender_text += f"- {gender_label}: {count} ({percent:.1f}%)"

                    result_panels.append(pn.pane.Markdown(gender_text))

        # Add a note about results validation
        result_panels.append(pn.pane.Markdown(
            "*These results show the actual data analysis findings. The next step will provide a final summary and visualization of key insights.*"))

        # Update the display
        self.execution_pane.objects = result_panels

    def _generate_final_results(self):
        """Generate the final results summary based on the analysis"""
        logger.info("Generating final results")

        # In a full implementation, an LLM would analyze the results and provide insights
        # For this demo, we'll generate the insights based on the intermediate results

        query = self.query_text.lower()
        result = {}

        # Generate insights based on query type and results
        if "bmi" in query:
            if 'stats' in self.intermediate_results:
                stats = self.intermediate_results['stats']

                if "female" in query or "women" in query:
                    target = "female patients"
                elif "male" in query or "men" in query:
                    target = "male patients"
                else:
                    target = "all patients"

                # Check if we have BMI data
                if stats.get('avg_bmi') is not None:
                    avg_bmi = stats.get('avg_bmi')

                    # Create BMI category descriptions
                    bmi_category = "unknown"
                    clinical_implications = ""

                    if avg_bmi < 18.5:
                        bmi_category = "underweight"
                        clinical_implications = "may indicate nutritional deficiencies or other health conditions"
                    elif avg_bmi < 25:
                        bmi_category = "normal weight"
                        clinical_implications = "is associated with the lowest risk of weight-related health problems"
                    elif avg_bmi < 30:
                        bmi_category = "overweight"
                        clinical_implications = "indicates increased risk for heart disease, diabetes, and other conditions"
                    elif avg_bmi < 35:
                        bmi_category = "obesity (Class 1)"
                        clinical_implications = "is associated with significantly higher risk of cardiovascular disease, diabetes, and metabolic syndrome"
                    elif avg_bmi < 40:
                        bmi_category = "obesity (Class 2)"
                        clinical_implications = "indicates severe obesity with high risk of health complications"
                    else:
                        bmi_category = "extreme obesity (Class 3)"
                        clinical_implications = "is associated with extremely high risk of serious health conditions and reduced life expectancy"

                    # Format summary text
                    summary = f"The average BMI for {target} is {avg_bmi:.1f}, which falls in the '{bmi_category}' category. This {clinical_implications}."

                    # Add distribution info if available
                    if stats.get('std_bmi') is not None:
                        summary += f" The standard deviation is {stats.get('std_bmi', 0):.1f}, indicating the variability in the BMI values."

                    # Add active patients context
                    if target == "all patients":
                        if 'gender_stats' in self.intermediate_results:
                            gender_stats = self.intermediate_results['gender_stats']
                            f_avg = gender_stats.get('F', {}).get('avg_bmi')
                            m_avg = gender_stats.get('M', {}).get('avg_bmi')

                            if f_avg is not None and m_avg is not None:
                                gender_diff = abs(f_avg - m_avg)
                                higher_gender = "female" if f_avg > m_avg else "male"

                                summary += f" On average, {higher_gender} patients have a higher BMI by {gender_diff:.1f} points."

                    # Add recommendation
                    if avg_bmi >= 25:
                        summary += " Interventions focusing on healthy diet, regular physical activity, and behavioral changes could be beneficial for this patient population."

                    # Store results
                    result['summary'] = summary
                    result['avg_bmi'] = avg_bmi
                    result['bmi_category'] = bmi_category
                    result['target_population'] = target

                    # Create visualization if we have the data
                    if 'bmi_data' in self.intermediate_results and not self.intermediate_results['bmi_data'].empty:
                        bmi_data = self.intermediate_results['bmi_data']

                        # Create BMI distribution with category ranges
                        bmi_plot = bmi_data['bmi'].hvplot.hist(
                            bins=20,
                            height=400,
                            width=700,
                            alpha=0.7,
                            title=f"BMI Distribution for {target.title()}"
                        )

                        # Store the plot
                        result['bmi_plot'] = bmi_plot

        elif "active patients" in query:
            if 'stats' in self.intermediate_results:
                stats = self.intermediate_results['stats']

                # Generate insights about active patients
                active_count = stats.get('active_patients', 0)
                total_count = stats.get('total_patients', 0)
                percent_active = stats.get('percent_active', 0)

                summary = f"There are {active_count} active patients out of {total_count} total patients, representing {percent_active:.1f}% of the patient population."

                # Add gender insights if available
                if 'gender_counts' in stats:
                    gender_text = "**2. Gender Breakdown of Active Patients:**\n\n"

                    for gender, count in stats['gender_counts'].items():
                        gender_label = "Female" if gender == "F" else "Male"
                        percent = stats['gender_percent'].get(gender, 0)
                        gender_text += f"- {gender_label}: {count} ({percent:.1f}%)\n"

                    result['gender_text'] = gender_text

                    # Add gender pie chart
                    if 'active_data' in self.intermediate_results and 'gender' in self.intermediate_results['active_data'].columns:
                        active_data = self.intermediate_results['active_data']

                        # Create gender distribution pie chart
                        gender_counts = active_data['gender'].value_counts()
                        pie_data = pd.DataFrame({
                            'Gender': ["Female" if g == "F" else "Male" for g in gender_counts.index],
                            'Count': gender_counts.values
                        })

                        gender_pie = pie_data.hvplot.pie(
                            x='Gender',
                            y='Count',
                            height=350,
                            width=350,
                            title="Active Patients by Gender"
                        )

                        # Store the plot
                        result['gender_pie'] = gender_pie

                # Add program duration insights if available
                if 'duration' in stats:
                    duration = stats['duration']
                    avg_months = duration.get('avg_months', 0)

                    summary += f" On average, active patients have been in the program for {avg_months:.1f} months."

                    # Add additional insights based on duration
                    if avg_months < 3:
                        summary += " This is a relatively new patient cohort, suggesting recent program growth."
                    elif avg_months > 12:
                        summary += " This indicates strong patient retention in the program."

                # Store results
                result['summary'] = summary
                result['active_count'] = active_count
                result['percent_active'] = percent_active

                # Create visualization if data is available
                if 'active_data' in self.intermediate_results and 'gender' in self.intermediate_results['active_data'].columns:
                    active_data = self.intermediate_results['active_data']

                    # Create gender distribution pie chart
                    gender_counts = active_data['gender'].value_counts()
                    pie_data = pd.DataFrame({
                        'Gender': ["Female" if g == "F" else "Male" for g in gender_counts.index],
                        'Count': gender_counts.values
                    })

                    gender_pie = pie_data.hvplot.pie(
                        x='Gender',
                        y='Count',
                        height=350,
                        width=350,
                        title="Active Patients by Gender"
                    )

                    # Store the plot
                    result['gender_pie'] = gender_pie

                    # Create duration histogram if available
                    if 'months_in_program' in active_data.columns:
                        duration_hist = active_data['months_in_program'].hvplot.hist(
                            bins=12,
                            height=350,
                            width=600,
                            alpha=0.7,
                            title="Time in Program for Active Patients"
                        )

                        # Store the plot
                        result['duration_hist'] = duration_hist

        elif "weight" in query:
            if 'stats' in self.intermediate_results:
                stats = self.intermediate_results['stats']

                # Check if we have weight data
                if stats.get('avg_weight') is not None:
                    avg_weight = stats.get('avg_weight')
                    unique_patients = stats.get('unique_patients', 0)

                    # Format summary text
                    summary = f"The average weight of patients is {avg_weight:.1f} lbs, based on data from {unique_patients} patients."

                    # Add gender insights if available
                    if 'gender_stats' in self.intermediate_results:
                        gender_stats = self.intermediate_results['gender_stats']
                        f_avg = gender_stats.get('F', {}).get('avg_weight')
                        m_avg = gender_stats.get('M', {}).get('avg_weight')

                        if f_avg is not None and m_avg is not None:
                            gender_diff = abs(f_avg - m_avg)
                            summary += f" Female patients average {f_avg:.1f} lbs, while male patients average {m_avg:.1f} lbs, a difference of {gender_diff:.1f} lbs."

                    # Add context about weight statistics
                    if stats.get('std_weight') is not None:
                        std_weight = stats.get('std_weight')
                        summary += f" The standard deviation is {std_weight:.1f} lbs, indicating the spread of weight values in the population."

                    if stats.get('min_weight') is not None and stats.get('max_weight') is not None:
                        min_weight = stats.get('min_weight')
                        max_weight = stats.get('max_weight')
                        summary += f" Weights range from {min_weight:.1f} to {max_weight:.1f} lbs."

                    # Store results
                    result['summary'] = summary
                    result['avg_weight'] = avg_weight
                    result['unique_patients'] = unique_patients

                    # Create visualization if data is available
                    if 'weight_data' in self.intermediate_results and not self.intermediate_results['weight_data'].empty:
                        weight_data = self.intermediate_results['weight_data']

                        # Create weight distribution
                        weight_plot = weight_data['weight'].hvplot.hist(
                            bins=20,
                            height=400,
                            width=700,
                            alpha=0.7,
                            title="Weight Distribution (lbs)"
                        )

                        # Store the plot
                        result['weight_plot'] = weight_plot

        else:
            # Generic summary for other queries
            summary = f"Based on the analysis of your query '{self.query_text}', here are the key findings:"

            if 'stats' in self.intermediate_results:
                stats = self.intermediate_results['stats']

                total_patients = stats.get('total_patients', 0)
                active_patients = stats.get('active_patients', 0)

                summary += f"\n\n- Total patients in the database: {total_patients}"
                summary += f"\n- Active patients: {active_patients} ({active_patients/total_patients*100:.1f}% of total)" if total_patients > 0 else ""

                # Add gender breakdown if available
                if 'gender_counts' in stats:
                    gender_text = "**Gender Breakdown:**\n\n"

                    for gender, count in stats['gender_counts'].items():
                        gender_label = "Female" if gender == "F" else "Male" if gender == "M" else gender
                        percent = count / total_patients * 100 if total_patients > 0 else 0
                        gender_text += f"- {gender_label}: {count} ({percent:.1f}%)"

                    result['gender_text'] = gender_text

                # Add a note about custom queries
                summary += "\n\nFor more specific analysis, please try a more targeted query such as 'What is the average BMI of female patients?' or 'Show me the distribution of active patients by gender.'"

                # Store results
                result['summary'] = summary

        # Mark that we have final results
        self.analysis_result = result
        logger.info("Generated final results")

    def _display_final_results(self):
        """Display the final results with visualizations and insights"""
        if not self.analysis_result:
            self.result_pane.object = "No analysis results available. Please enter a query."
            return

        logger.info("Displaying final results")

        # Create a markdown panel with the results
        if 'summary' in self.analysis_result:
            results_md = f"### Analysis Results\n\n{self.analysis_result['summary']}"
            self.result_pane.object = results_md

        # Check if we have visualizations to display
        viz = None

        # Extract the appropriate visualization based on query type
        if 'bmi_plot' in self.analysis_result:
            viz = self.analysis_result['bmi_plot']
        elif 'gender_pie' in self.analysis_result and 'duration_hist' in self.analysis_result:
            # Combine multiple plots
            viz = pn.Column(
                self.analysis_result['gender_pie'],
                self.analysis_result['duration_hist'],
                sizing_mode='stretch_width'
            )
        elif 'gender_pie' in self.analysis_result:
            viz = self.analysis_result['gender_pie']
        elif 'duration_hist' in self.analysis_result:
            viz = self.analysis_result['duration_hist']
        elif 'weight_plot' in self.analysis_result:
            viz = self.analysis_result['weight_plot']

        # Update the visualization pane if we have a visualization
        if viz is not None:
            self.visualization_pane.object = viz
        else:
            self.visualization_pane.object = hv.Div(
                'No visualization available for this query')

        # Reset the status and workflow for the next query
        self._update_status("Analysis complete. You can enter a new query.")


def data_assistant_page():
    """Returns the data analysis assistant page for the application"""
    data_assistant = DataAnalysisAssistant()
    return data_assistant.view()
