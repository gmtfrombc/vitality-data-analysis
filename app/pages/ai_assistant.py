"""
AI Assistant Page Component

This page provides an interface for generating SQL queries from natural language using OpenAI.
The OpenAI API key should be set as an environment variable named OPENAI_API_KEY or in a .env file.
"""

import panel as pn
import param
import pandas as pd
import db_query
import sys
import os
import json
import logging
import sqlite3
import re
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ai_assistant')

# Add the parent directory to path so we can import db_query
sys.path.append(str(Path(__file__).parent.parent.parent))

# Constants
# You can use "gpt-4" for better results if available
OPENAI_MODEL = "gpt-3.5-turbo"
QUERIES_FILE = "saved_queries.json"  # File to store saved queries

# Healthcare terminology dictionary - maps common terms to database fields
HEALTHCARE_TERMS = {
    # Gender
    "female": "F",
    "male": "M",
    "woman": "F",
    "women": "F",
    "man": "M",
    "men": "M",

    # Lab tests
    "a1c": "HbA1c",
    "hgba1c": "HbA1c",
    "hemoglobin a1c": "HbA1c",
    "blood sugar": "HbA1c",
    "glucose": "HbA1c",
    "cholesterol": "cholesterol",
    "ldl": "LDL",
    "hdl": "HDL",
    "triglycerides": "triglycerides",

    # Vitals
    "bp": "blood pressure",
    "blood pressure": {"systolic": "sbp", "diastolic": "dbp"},
    "systolic": "sbp",
    "diastolic": "dbp",
    "systolic blood pressure": "sbp",
    "diastolic blood pressure": "dbp",
    "systolic bp": "sbp",
    "diastolic bp": "dbp",
    "weight": "weight",
    "bmi": "bmi",
    "body mass index": "bmi",
    "height": "height",

    # Scores
    "vs": "vitality_score",
    "vitality": "vitality_score",
    "vitality score": "vitality_score",
    "heart fitness": "heart_fit_score",
    "heart health": "heart_fit_score",
    "heart score": "heart_fit_score",
    "heart fit": "heart_fit_score",
    "engagement": "engagement_score",
    "engagement score": "engagement_score",
}

# Query examples by category
QUERY_EXAMPLES = {
    "Demographics": [
        "Show me all female patients over 65",
        "Find patients who are male between 40 and 50 years old",
        "List all patients with high engagement scores (>80)"
    ],
    "Lab Results": [
        "Find patients with A1C over 8 in their first lab test",
        "Show me female patients with high cholesterol (>240)",
        "List patients whose A1C improved by more than 1 point"
    ],
    "Vitals": [
        "Find patients with systolic BP over 140",
        "Show me patients who lost more than 10 pounds during the program",
        "List patients with BMI over 30 at program start"
    ],
    "Combined Queries": [
        "Find female patients over 50 with A1C over 9 and high blood pressure",
        "Show men with healthy BMI (18.5-24.9) and good heart fitness scores",
        "List patients who improved both A1C and blood pressure during the program"
    ]
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

    def __init__(self, **params):
        super().__init__(**params)
        self.result_data = pd.DataFrame()
        self.client = None
        self.results_container = None  # Will be set during view() method

        # Set up logging level from environment variable
        debug_mode = os.environ.get(
            "DEBUG", "").lower() in ("true", "1", "yes", "y")
        if debug_mode:
            self._set_log_level(logging.DEBUG)
            logger.debug("Debug mode enabled")
        else:
            self._set_log_level(logging.INFO)

        # Get API key from environment variable
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        if self.api_key:
            self.init_client()
            logger.info("API key found in environment variables")
        else:
            self.status_message = "OPENAI_API_KEY environment variable not set. Please set it to use AI assistant."
            logger.warning("OPENAI_API_KEY environment variable not set")

        # Get database schema information
        self._load_db_schema()

        # Load saved queries
        self._load_saved_queries()

    def init_client(self):
        """Initialize the OpenAI client"""
        try:
            self.client = OpenAI(api_key=self.api_key)
            self.status_message = "OpenAI client initialized successfully"
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            self.status_message = f"Error initializing OpenAI client: {str(e)}"
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.client = None

    def _load_db_schema(self):
        """Load database schema information to provide context for AI"""
        try:
            # Get tables information
            tables_info = db_query.query_dataframe(
                "SELECT name FROM sqlite_master WHERE type='table';"
            )

            schema_info = []
            table_details = {}  # Store detailed table info for validation

            # Get columns for each table
            for table in tables_info['name']:
                try:
                    columns_info = db_query.query_dataframe(
                        f"PRAGMA table_info({table});")
                    columns_str = ", ".join(
                        [f"{row['name']} ({row['type']})" for _, row in columns_info.iterrows()])
                    schema_info.append(
                        f"Table: {table}\nColumns: {columns_str}\n")

                    # Store column details for validation
                    table_details[table.lower()] = {
                        'columns': [row['name'].lower() for _, row in columns_info.iterrows()],
                        'column_types': {row['name'].lower(): row['type'] for _, row in columns_info.iterrows()}
                    }

                except Exception as e:
                    logger.error(
                        f"Error getting columns for table {table}: {str(e)}")

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
                fk_info = db_query.query_dataframe(
                    f"PRAGMA foreign_key_list({table_name});")

                if not fk_info.empty:
                    for _, row in fk_info.iterrows():
                        ref_table = row.get('table', '')
                        from_col = row.get('from', '')
                        to_col = row.get('to', '')
                        if ref_table and from_col and to_col:
                            relationships.append(
                                f"Table '{table_name}' has foreign key '{from_col}' referencing '{ref_table}({to_col})'")

            self.table_relationships = relationships
            logger.info(f"Extracted {len(relationships)} table relationships")
        except Exception as e:
            logger.error(f"Error extracting table relationships: {str(e)}")
            self.table_relationships = []

    def _load_saved_queries(self):
        """Load saved queries from file"""
        try:
            if os.path.exists(QUERIES_FILE):
                with open(QUERIES_FILE, 'r') as f:
                    self.saved_queries = json.load(f)
                logger.info(f"Loaded {len(self.saved_queries)} saved queries")
            else:
                self.saved_queries = []
                logger.info("No saved queries file found")
        except Exception as e:
            logger.error(f"Error loading saved queries: {str(e)}")
            self.saved_queries = []

    def _save_queries_to_file(self):
        """Save queries to file"""
        try:
            with open(QUERIES_FILE, 'w') as f:
                json.dump(self.saved_queries, f, indent=2)
            logger.info(f"Saved {len(self.saved_queries)} queries to file")
        except Exception as e:
            logger.error(f"Error saving queries: {str(e)}")
            self.status_message = f"Error saving queries: {str(e)}"

    def view(self):
        """Generate the AI assistant view"""

        # Create title and description
        title = pn.pane.Markdown("# AI SQL Assistant",
                                 sizing_mode="stretch_width")
        description = pn.pane.Markdown(
            """
            Ask questions about the patient data in natural language, and the AI will 
            generate SQL queries to answer your questions.
            
            **Examples:**
            - "Show me all female patients with an engagement score above 80"
            - "Find patients over 50 with vitality scores below 20"
            - "List patients who started with high blood pressure but improved in their latest reading"
            - "What's the average BMI change for patients with heart_fit_score above 70?"
            """
        )

        # Status message display - repurposed to show detailed validation issues
        status_display = pn.pane.Markdown(f"Status: {self.status_message}", styles={
                                          'background': '#f8f9fa', 'padding': '4px', 'border-radius': '4px', 'margin-bottom': '8px', 'max-height': '120px', 'overflow-y': 'auto', 'font-size': '0.9em'})

        # Watch for status changes
        def update_status(event):
            status_display.object = event.new  # Direct pass-through of HTML content

        self.param.watch(update_status, 'status_message')

        # Create query input
        query_input = pn.widgets.TextAreaInput(
            name='Your Question',
            placeholder='Enter your question here...',
            value=self.query_text,
            height=100,
            sizing_mode='stretch_width'
        )
        query_input.link(self, value='query_text')

        # Create generate button
        generate_button = pn.widgets.Button(
            name='Generate SQL',
            button_type='primary',
            width=150,
            disabled=not bool(self.api_key)  # Disable if no API key
        )
        generate_button.on_click(self._generate_sql)

        # Create SQL display
        sql_display = pn.widgets.TextAreaInput(
            name='Generated SQL',
            value=self.generated_sql,
            height=150,
            sizing_mode='stretch_width'
        )

        # Link generated SQL to display
        self.param.watch(lambda event: setattr(
            sql_display, 'value', event.new), 'generated_sql')

        # Create validation status badge
        validation_badge = pn.pane.HTML(
            "<span class='validation-badge' style='display:none;'></span>",
            width=100,
            height=30,
            margin=(5, 0, 0, 10)
        )

        # Create validate and execute buttons
        validate_button = pn.widgets.Button(
            name='Validate SQL',
            button_type='primary',
            width=150,
            disabled=True
        )

        execute_button = pn.widgets.Button(
            name='Execute Query',
            button_type='success',
            width=150,
            disabled=True
        )

        # Create a dynamic results component
        results_container = pn.Column(
            pn.pane.Markdown(
                "No results to display. Generate and execute a query."),
            sizing_mode='stretch_width'
        )

        # Store reference to results container for future updates
        self.results_container = results_container

        # For reset functionality
        reset_references = {
            'query_input': query_input
        }

        # Create reset button
        reset_button = pn.widgets.Button(
            name='Reset Form',
            button_type='danger',
            width=150
        )
        reset_button.on_click(lambda event: self._reset(
            event, reset_references, results_container))

        # Enable buttons only when SQL is generated
        def update_buttons(event):
            validate_button.disabled = not bool(event.new)
            execute_button.disabled = not bool(event.new)
            # Hide validation badge when SQL changes
            validation_badge.object = "<span class='validation-badge' style='display:none;'></span>"
        self.param.watch(update_buttons, 'generated_sql')

        validate_button.on_click(
            lambda event: self._validate_button_click(event, validation_badge))
        execute_button.on_click(
            lambda event: self._execute_sql(event))

        # Create save query components
        query_name_input = pn.widgets.TextInput(
            name='Query Name',
            placeholder='Enter a name for this query...',
            value=self.query_name,
            width=300
        )
        query_name_input.link(self, value='query_name')

        save_query_button = pn.widgets.Button(
            name='Save Query',
            button_type='primary',
            width=100,
            disabled=not bool(self.api_key)
        )
        save_query_button.on_click(self._save_query)

        # Create saved queries panel
        saved_queries_title = pn.pane.Markdown("## Saved Queries")
        saved_queries_list = pn.widgets.Select(
            name='Saved Queries',
            options={q['name']: i for i, q in enumerate(self.saved_queries)},
            size=10,
            width=250
        )

        load_query_button = pn.widgets.Button(
            name='Load',
            button_type='default',
            width=100,
            disabled=len(self.saved_queries) == 0
        )

        delete_query_button = pn.widgets.Button(
            name='Delete',
            button_type='danger',
            width=100,
            disabled=len(self.saved_queries) == 0
        )

        # Set up callbacks for saved queries
        def load_query(event):
            if saved_queries_list.value is not None and 0 <= saved_queries_list.value < len(self.saved_queries):
                selected_query = self.saved_queries[saved_queries_list.value]
                self.query_text = selected_query['query']
                self.query_name = selected_query['name']
                self.status_message = f"Loaded query: {selected_query['name']}"

        def delete_query(event):
            if saved_queries_list.value is not None and 0 <= saved_queries_list.value < len(self.saved_queries):
                deleted_name = self.saved_queries[saved_queries_list.value]['name']
                del self.saved_queries[saved_queries_list.value]
                self._save_queries_to_file()
                # Update the select widget
                saved_queries_list.options = {
                    q['name']: i for i, q in enumerate(self.saved_queries)}
                # Disable buttons if no saved queries remain
                load_query_button.disabled = len(self.saved_queries) == 0
                delete_query_button.disabled = len(self.saved_queries) == 0
                self.status_message = f"Deleted query: {deleted_name}"

        load_query_button.on_click(load_query)
        delete_query_button.on_click(delete_query)

        # Update saved queries list when queries change
        def update_saved_queries_list(event):
            saved_queries_list.options = {
                q['name']: i for i, q in enumerate(event.new)}
            load_query_button.disabled = len(event.new) == 0
            delete_query_button.disabled = len(event.new) == 0

        self.param.watch(update_saved_queries_list, 'saved_queries')

        # Environment variable information message
        env_info = pn.pane.Markdown(
            """
            **Note:** This AI Assistant requires the OPENAI_API_KEY environment variable to be set.
            
            To set the environment variable:
            
            On macOS/Linux:
            ```
            export OPENAI_API_KEY="your_api_key_here"
            ```
            
            On Windows:
            ```
            set OPENAI_API_KEY=your_api_key_here
            ```
            
            For more detailed logging during development, set DEBUG=true:
            ```
            export DEBUG=true  # For macOS/Linux
            set DEBUG=true     # For Windows
            ```
            
            Then restart the application.
            """,
            styles={'background': '#f8f9fa',
                    'padding': '10px', 'border-radius': '5px'}
        )

        # Only show the environment variable info if API key is not set
        api_key_info = env_info if not self.api_key else pn.pane.Markdown("")

        # SQL display with badge
        sql_header = pn.Row(
            pn.pane.Markdown("### Step 2: Review the SQL",
                             margin=(0, 0, 10, 0)),
            validation_badge,
            sizing_mode='stretch_width'
        )

        # Modified button row to push reset button to the far right
        button_row = pn.Row(
            pn.Row(generate_button, validate_button,
                   execute_button, width=500),
            pn.layout.HSpacer(),  # Use HSpacer instead of Spacer with flex
            reset_button,
            sizing_mode='stretch_width'
        )

        save_row = pn.Row(
            query_name_input,
            save_query_button
        )

        query_buttons_row = pn.Row(
            load_query_button,
            delete_query_button
        )

        # Schema display (collapsible)
        schema_accordion = pn.Accordion(
            ('Database Schema', pn.pane.Markdown(self.db_schema)),
            toggle=True
        )

        # Create Example Queries panel
        example_queries_title = pn.pane.Markdown("## Example Queries")

        # Create a collapsible accordion for each category of examples
        example_accordions = []

        for category, examples in QUERY_EXAMPLES.items():
            # Create a column of example links as clickable divs
            example_links = []
            for i, example in enumerate(examples):
                example_id = f"example_{category}_{i}".replace(" ", "_")

                # Create simple button for each example
                example_btn = pn.widgets.Button(
                    name=example,
                    button_type="light",
                    width=300,
                    align='start',
                    styles={
                        'font-size': '0.9em',
                        'padding': '10px',
                        'text-align': 'left',
                        'white-space': 'normal',
                        'height': 'auto',
                        'min-height': '50px',
                        'margin-bottom': '5px',
                        'overflow-wrap': 'break-word'
                    }
                )

                # Use a direct callback
                example_btn.on_click(
                    lambda event, ex=example: self._use_example(ex))
                example_links.append(example_btn)

            # Add category to accordion
            example_accordions.append(
                (category, pn.Column(*example_links, width=320, margin=0))
            )

        # Create the accordion widget with more space
        examples_accordion = pn.Accordion(
            *example_accordions,
            width=340,
            toggle=True,
            active=[0],  # Start with first category open
            margin=0
        )

        # Create left sidebar with saved queries and examples
        left_sidebar = pn.Column(
            saved_queries_title,
            saved_queries_list,
            query_buttons_row,
            pn.layout.Divider(),
            example_queries_title,
            examples_accordion,
            width=350,  # Ensure enough width for content
            margin=0,
            scroll=True,
            styles={'z-index': '1000'}
        )

        # Main content
        main_content = pn.Column(
            title,
            description,
            pn.layout.Divider(),
            api_key_info,
            status_display,
            pn.layout.Divider(),
            pn.pane.Markdown("### Step 1: Ask your question"),
            query_input,
            pn.layout.Divider(),
            sql_header,
            sql_display,
            button_row,
            pn.layout.Divider(),
            pn.pane.Markdown("### Step 3: View Results"),
            results_container,
            pn.layout.Divider(),
            pn.pane.Markdown("### Save This Query"),
            save_row,
            pn.layout.Divider(),
            schema_accordion,
            min_width=800  # Use min_width instead of width to prevent warning
        )

        # Layout with sidebar and main content in a tabbed interface
        custom_css = """
        <style>
        .bk-root .bk-tab {
            font-weight: bold;
        }
        .example-link {
            transition: background-color 0.3s;
        }
        .example-link:hover {
            background-color: #e0e0e0 !important;
        }
        </style>
        """

        css_pane = pn.pane.HTML(custom_css)

        tabs = pn.Column(
            css_pane,
            pn.Tabs(
                ('AI SQL Assistant', main_content),
                ('Query Library', left_sidebar),
                tabs_location='above',
                margin=0,
                sizing_mode='stretch_width'
            ),
            sizing_mode='stretch_both',
            margin=0
        )

        return tabs

    def _generate_sql(self, event=None):
        """Generate SQL from natural language using OpenAI"""
        if not self.client:
            self.status_message = "OpenAI client not initialized"
            return

        if not self.query_text.strip():
            self.status_message = "Please enter a question first"
            return

        try:
            # Get the query text from the instance variable, not the event
            query_text = self.query_text
            logger.info(f"Generating SQL for query: {query_text}")

            # Create a structured schema description
            schema_description = self._create_enhanced_schema_description()
            logger.debug(
                f"Schema description for prompt:\n{schema_description}")

            # Build the system prompt
            system_prompt = f"""You are an expert SQL generator specializing in healthcare database queries. 
            
DATABASE SCHEMA:
{schema_description}

IMPORTANT RULES:
1. Generate ONLY valid SQLite SQL queries
2. All table names are in PLURAL form (patients, not patient; vitals, not vital)
3. Use only tables and columns that exist in the schema
4. When joining tables, always ensure the join conditions are correct
5. Format dates using datetime() function when needed
6. Return ONLY the SQL query with no explanation or comments
7. Use table aliases for readability (p for patients, v for vitals, etc.)
8. The vitals table does NOT have a test_name column - it has direct columns for sbp, dbp, weight, etc.

The query should be straightforward, focused, and follow SQLite syntax exactly.
"""
            logger.debug(f"System prompt:\n{system_prompt}")

            # Create example-based user prompt
            user_prompt = f"""Here are some examples of natural language questions and their corresponding SQL queries:

Example 1:
User: Show me all female patients over 65
SQL:
SELECT p.id as patient_id, p.first_name, p.last_name, p.birth_date
FROM patients p
WHERE p.gender = 'F' AND (date('now') - p.birth_date) > 65
ORDER BY p.birth_date ASC

Example 2:
User: Find patients with A1C over 8
SQL:
SELECT p.id as patient_id, p.first_name, p.last_name, l.value as a1c_value
FROM patients p
JOIN lab_results l ON p.id = l.patient_id
WHERE l.test_name = 'HbA1c' AND l.value > 8
ORDER BY l.value DESC

Example 3:
User: Show me patients who improved their blood pressure during the program
SQL:
WITH first_bp AS (
    SELECT patient_id, MIN(date) as first_date, sbp as first_sbp, dbp as first_dbp
    FROM vitals
    GROUP BY patient_id
),
last_bp AS (
    SELECT patient_id, MAX(date) as last_date, sbp as last_sbp, dbp as last_dbp
    FROM vitals
    GROUP BY patient_id
)
SELECT p.id as patient_id, p.first_name, p.last_name, 
       f.first_sbp, f.first_dbp, l.last_sbp, l.last_dbp
FROM patients p
JOIN first_bp f ON p.id = f.patient_id
JOIN last_bp l ON p.id = l.patient_id
WHERE (f.first_sbp > l.last_sbp OR f.first_dbp > l.last_dbp)
ORDER BY (f.first_sbp - l.last_sbp) + (f.first_dbp - l.last_dbp) DESC

Example 4:
User: Find patients with high blood pressure readings
SQL:
SELECT p.id as patient_id, p.first_name, p.last_name, v.sbp, v.dbp, v.date as test_date
FROM patients p
JOIN vitals v ON p.id = v.patient_id
WHERE v.sbp > 140 OR v.dbp > 90
ORDER BY v.sbp DESC

Example 5:
User: Show me patients who lost weight during the program
SQL:
WITH first_weight AS (
    SELECT patient_id, MIN(date) as first_date, weight as initial_weight
    FROM vitals
    GROUP BY patient_id
),
last_weight AS (
    SELECT patient_id, MAX(date) as last_date, weight as final_weight
    FROM vitals
    GROUP BY patient_id
)
SELECT p.id as patient_id, p.first_name, p.last_name, 
       fw.initial_weight, lw.final_weight,
       (fw.initial_weight - lw.final_weight) as weight_loss,
       ((fw.initial_weight - lw.final_weight) / fw.initial_weight * 100) as pct_loss
FROM patients p
JOIN first_weight fw ON p.id = fw.patient_id
JOIN last_weight lw ON p.id = lw.patient_id
WHERE lw.final_weight < fw.initial_weight
ORDER BY pct_loss DESC

Now, generate ONLY a SQL query for this question:
{query_text}
"""
            logger.debug(f"User prompt:\n{user_prompt}")

            # Show generating status
            self.status_message = "<span style='color: blue;'>Generating SQL query... please wait.</span>"

            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1  # Lower temperature for more deterministic SQL generation
            )

            # Extract the SQL from the response
            sql = response.choices[0].message.content.strip()
            logger.debug(f"Raw AI response: {sql}")

            # Clean up the SQL if it contains markdown or comments
            sql = self._clean_generated_sql(sql)

            # Update the UI with the generated SQL
            self.generated_sql = sql
            logger.info(f"Generated SQL: {sql}")

            # Update status message
            self.status_message = "<span style='color: green;'>SQL generated successfully. Click 'Validate SQL' or 'Execute Query' to continue.</span>"

            # Return the SQL for use in tests or other functions
            return {"sql": sql, "error": None}
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            self.status_message = f"<span style='color: red; font-weight: bold;'>ERROR</span><br>Failed to generate SQL: {str(e)}"
            return {"sql": "", "error": str(e)}

    def _create_enhanced_schema_description(self):
        """Create an enhanced description of the database schema for the prompt"""
        schema_parts = []

        # Include only essential tables to keep the context concise
        essential_tables = [
            "patients", "vitals", "lab_results", "scores", "pmh", "patient_visit_metrics", "mental_health"
        ]

        # Add tables with their columns and types
        for table_name in essential_tables:
            if table_name.lower() in self.table_details:
                table_info = self.table_details[table_name.lower()]
                columns_info = []

                for col_name, col_type in table_info.get('column_types', {}).items():
                    columns_info.append(f"{col_name} ({col_type})")

                schema_parts.append(
                    f"Table: {table_name}\nColumns: {', '.join(columns_info)}")

        # Add key relationships for better joins
        relationship_info = []
        if hasattr(self, 'table_relationships'):
            for relation in self.table_relationships:
                relationship_info.append(relation)

        if relationship_info:
            schema_parts.append("Relationships:\n" +
                                "\n".join(relationship_info))

        return "\n\n".join(schema_parts)

    def _clean_generated_sql(self, sql):
        """Clean the generated SQL by removing markdown formatting and comments"""
        # Extract SQL from markdown code blocks if present
        if "```sql" in sql:
            # Try to extract from SQL code block
            match = re.search(r'```sql\n(.*?)\n```', sql, re.DOTALL)
            if match:
                sql = match.group(1).strip()
        elif "```" in sql:
            # Try to extract from any code block
            match = re.search(r'```\n(.*?)\n```', sql, re.DOTALL)
            if match:
                sql = match.group(1).strip()

        # Remove any comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)

        # Fix table name issues (singular to plural)
        sql = re.sub(r'\bpatient\b', 'patients', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bvital\b', 'vitals', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\blab\b(?!_)', 'lab_results', sql,
                     flags=re.IGNORECASE)  # Don't match lab_results
        sql = re.sub(r'\bscore\b', 'scores', sql, flags=re.IGNORECASE)

        # Fix incorrect vital table references (vitals table doesn't have test_name column)
        sql = re.sub(
            r'FROM\s+vitals\s+WHERE\s+test_name\s*=\s*[\'"]blood_pressure[\'"]', 'FROM vitals', sql, flags=re.IGNORECASE)
        sql = re.sub(
            r'FROM\s+vitals\s+WHERE\s+test_name\s*=\s*[\'"]weight[\'"]', 'FROM vitals', sql, flags=re.IGNORECASE)
        sql = re.sub(
            r'FROM\s+vitals\s+WHERE\s+test_name\s*=\s*[\'"]bmi[\'"]', 'FROM vitals', sql, flags=re.IGNORECASE)

        # Fix date column name for vitals table
        sql = re.sub(r'vitals\.test_date', 'vitals.date',
                     sql, flags=re.IGNORECASE)

        logger.debug(f"Cleaned SQL: {sql}")
        return sql.strip()

    def _execute_sql(self, event=None):
        """Execute the generated SQL query"""
        if not self.generated_sql or self.generated_sql.startswith('--'):
            self.status_message = "No SQL to execute"
            return

        # Validate SQL before executing
        try:
            validation_result = self._validate_sql(self.generated_sql)
            if not validation_result['valid']:
                error_msg = validation_result['error']
                self.status_message = f"<span style='color: red; font-weight: bold;'>SQL EXECUTION FAILED</span><br><br><strong>Error:</strong> {error_msg}"
                return

            # If the validation returned a fixed query, use that instead
            sql_to_execute = validation_result.get(
                'fixed_query', self.generated_sql)
            if 'fixed_query' in validation_result:
                self.generated_sql = sql_to_execute
                self.status_message = f"<span style='color: blue;'>SQL was automatically fixed and will be executed.</span>"
                logger.info(f"Using fixed SQL for execution: {sql_to_execute}")
        except Exception as e:
            logger.error(f"Error during SQL validation: {str(e)}")
            self.status_message = f"<span style='color: red; font-weight: bold;'>VALIDATION ERROR</span><br><br>Could not validate SQL: {str(e)}"
            return

        try:
            self.status_message = "<span style='color: blue;'>Executing query...</span>"
            logger.info(f"Executing SQL: {sql_to_execute}")

            # Execute the query using our db_query module
            self.result_data = db_query.query_dataframe(sql_to_execute)

            # Update the results display
            self._update_results_display()

            # Ensure results are displayed even if empty
            rows_count = len(self.result_data)
            logger.info(
                f"Query executed successfully. Returned {rows_count} rows.")

            if rows_count == 0:
                self.status_message = f"<span style='color: orange; font-weight: bold;'>NOTICE</span><br>Query executed successfully but returned <strong>zero rows</strong>. Your query might be too restrictive or there's no matching data."
            else:
                self.status_message = f"<span style='color: green; font-weight: bold;'>SUCCESS</span><br>Query executed successfully. Returned <strong>{rows_count} rows</strong>."

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing SQL: {error_msg}")

            # Try to automatically fix the error and retry
            fixed_query = self._attempt_sql_fix(sql_to_execute, error_msg)
            if fixed_query:
                try:
                    logger.info(f"Retrying with fixed query: {fixed_query}")
                    self.result_data = db_query.query_dataframe(fixed_query)

                    # If we get here, the fix worked
                    self.generated_sql = fixed_query
                    rows_count = len(self.result_data)
                    self._update_results_display()

                    self.status_message = f"<span style='color: green; font-weight: bold;'>AUTO-FIXED</span><br>SQL query was automatically fixed and returned <strong>{rows_count} rows</strong>.<br><br>Original error: {error_msg}"
                    return
                except Exception as retry_error:
                    logger.error(f"Auto-fix failed: {str(retry_error)}")
                    # Fall through to error handling

            self.status_message = f"<span style='color: red; font-weight: bold;'>ERROR</span><br><br><strong>Failed to execute query:</strong> {error_msg}"

            # Clear results if there was an error
            self.result_data = pd.DataFrame()
            self._update_results_display()

    def _update_results_display(self):
        """Update the results container with current data"""
        if self.results_container is None:
            logger.warning("Results container not initialized")
            return

        try:
            # Clear existing content
            self.results_container.clear()

            if self.result_data.empty:
                self.results_container.append(pn.pane.Markdown(
                    "No results to display. Generate and execute a query."))
                return

            # Create a new tabulator with the current data
            logger.info(
                f"Creating results table with {len(self.result_data)} rows and columns: {list(self.result_data.columns)}")

            table = pn.widgets.Tabulator(
                self.result_data,
                sizing_mode='stretch_width',
                show_index=False,
                height=300
            )

            self.results_container.append(table)
            logger.info("Results display updated successfully")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error updating results display: {error_msg}")
            self.results_container.append(pn.pane.Markdown(
                f"Error displaying results: {error_msg}"))

    def _reset(self, event=None, reset_references=None, results_container=None):
        """Reset all inputs and outputs to their default state"""
        # Reset underlying data
        self.query_text = ""
        self.generated_sql = ""
        self.status_message = "<span style='color: blue;'>Form cleared. Ready for a new query.</span>"
        self.query_name = ""
        self.result_data = pd.DataFrame()

        # Directly update widgets if references are provided
        if reset_references and 'query_input' in reset_references:
            reset_references['query_input'].value = ""

        # Clear results display
        if results_container is not None:
            results_container.clear()
            results_container.append(pn.pane.Markdown(
                "No results to display. Generate and execute a query."))
        elif self.results_container is not None:
            self.results_container.clear()
            self.results_container.append(pn.pane.Markdown(
                "No results to display. Generate and execute a query."))

        logger.info("Reset form to default state")

    def _validate_button_click(self, event=None, validation_badge=None):
        """Handle validate button click"""
        if not self.generated_sql:
            self.status_message = "No SQL to validate"
            return

        validation_result = self._validate_sql(self.generated_sql)
        if validation_result['valid']:
            if validation_result['error'] and "couldn't be fully validated" in validation_result['error']:
                # Query is likely valid but has complex date functions
                self.status_message = "SQL Validation Status: <span style='color: orange; font-weight: bold;'>REQUIRES REVIEW</span><br><br>" + \
                    validation_result['error']
                if validation_badge:
                    validation_badge.object = "<span class='validation-badge' style='display:inline-block; background-color:#fcf8e3; color:#8a6d3b; padding:5px 10px; border-radius:3px; font-weight:bold;'>REVIEW</span>"
            else:
                # Fully valid query
                self.status_message = "SQL Validation Status: <span style='color: green; font-weight: bold;'>VALID</span><br><br>Your SQL is ready to execute."
                if validation_badge:
                    validation_badge.object = "<span class='validation-badge' style='display:inline-block; background-color:#dff0d8; color:#3c763d; padding:5px 10px; border-radius:3px; font-weight:bold;'>VALID</span>"
        else:
            error_msg = validation_result['error']
            self.status_message = f"SQL Validation Status: <span style='color: red; font-weight: bold;'>INVALID</span><br><br><strong>Error Details:</strong><br>{error_msg}"
            if validation_badge:
                validation_badge.object = "<span class='validation-badge' style='display:inline-block; background-color:#f2dede; color:#a94442; padding:5px 10px; border-radius:3px; font-weight:bold;'>INVALID</span>"

            # Try to provide more helpful context for common errors
            if "no such table" in error_msg.lower():
                self.status_message += "<br><br><strong>Suggestion:</strong> Check that table names match exactly with the schema shown below."
            elif "no such column" in error_msg.lower():
                self.status_message += "<br><br><strong>Suggestion:</strong> Check column names against the schema shown below."
            elif "syntax error" in error_msg.lower():
                self.status_message += "<br><br><strong>Suggestion:</strong> Review your SQL syntax. Common issues include missing commas, parentheses, or incorrect keywords."

    def _save_query(self, event=None):
        """Save the current query to the saved queries list"""
        if not self.query_text:
            self.status_message = "Cannot save empty query"
            return

        if not self.query_name:
            self.status_message = "Please enter a name for the query"
            return

        # Check if name already exists
        existing_names = [q['name'] for q in self.saved_queries]
        if self.query_name in existing_names:
            # Find the query with this name and update it
            for i, query in enumerate(self.saved_queries):
                if query['name'] == self.query_name:
                    self.saved_queries[i] = {
                        'name': self.query_name,
                        'query': self.query_text,
                        'sql': self.generated_sql
                    }
                    self._save_queries_to_file()
                    self.status_message = f"Updated saved query: {self.query_name}"
                    return
        else:
            # Add as a new query
            self.saved_queries.append({
                'name': self.query_name,
                'query': self.query_text,
                'sql': self.generated_sql
            })
            self._save_queries_to_file()
            self.status_message = f"Saved new query: {self.query_name}"

    def _use_example(self, example):
        """Use the selected example query"""
        self.query_text = example
        # Generate a suggested name based on the example
        self.query_name = self._generate_query_name()
        self.status_message = f"Loaded example query: {example}"

    def _validate_sql(self, sql_query):
        """Validate SQL syntax and schema references without executing the query"""
        if not sql_query:
            return {"valid": False, "error": "Empty SQL query"}

        logger.info(f"Validating SQL: {sql_query}")

        # Extract tables and columns from the query
        query_references = self._extract_sql_references(sql_query)

        # Validate schema references
        schema_validation = self._validate_schema_references(query_references)
        if not schema_validation['valid']:
            return schema_validation

        # Pre-check for common errors that SQLite might not catch clearly
        if "JOIN" in sql_query.upper() and "vitals" in sql_query.lower() and "test_name" in sql_query.lower():
            logger.warning(
                "Detected potential error: JOIN with 'test_name' in vitals table")
            # Fix the vitals table subquery issue
            fixed_query = re.sub(
                r'FROM\s+vitals\s+WHERE\s+test_name\s*=\s*[\'"]([^\'"]+)[\'"]', 'FROM vitals', sql_query, flags=re.IGNORECASE)
            if fixed_query != sql_query:
                logger.info(
                    f"Automatically fixed vitals table query: {fixed_query}")
                sql_query = fixed_query

        # Pre-check for singular table names and convert to plural
        singular_to_plural = {
            r'\bpatient\b': 'patients',
            r'\bvital\b': 'vitals',
            r'\blab\b(?!_)': 'lab_results',
            r'\bscore\b': 'scores',
        }

        for singular, plural in singular_to_plural.items():
            if re.search(singular, sql_query, re.IGNORECASE):
                logger.warning(
                    f"Detected singular table name: {singular.strip('\\b')} should be {plural}")
                sql_query = re.sub(
                    singular, plural, sql_query, flags=re.IGNORECASE)
                logger.info(
                    f"Automatically converted singular table name to plural: {singular.strip('\\b')} → {plural}")

        try:
            # Ask db_query to explain the query plan (validates syntax without executing)
            try:
                db_query.query_dataframe(f"EXPLAIN QUERY PLAN {sql_query}")
                return {"valid": True, "error": None}
            except Exception as e:
                error_msg = str(e)
                logger.error(f"SQL validation error: {error_msg}")

                # Try to fix the SQL query automatically
                fixed_query = self._attempt_sql_fix(sql_query, error_msg)
                if fixed_query:
                    logger.info("Attempting to validate fixed query")
                    try:
                        # Validate the fixed query
                        db_query.query_dataframe(
                            f"EXPLAIN QUERY PLAN {fixed_query}")
                        return {
                            "valid": True,
                            "error": f"Original query had errors but was fixed automatically: {error_msg}",
                            "fixed_query": fixed_query
                        }
                    except Exception as fix_error:
                        logger.error(
                            f"Fixed query still has errors: {str(fix_error)}")
                        # Continue with original error handling

                # Simple error message processing for the original query
                if "no such table" in error_msg.lower():
                    table_match = re.search(
                        r"no such table: ([^\s]+)", error_msg.lower())
                    if table_match:
                        bad_table = table_match.group(1)
                        # Suggest plural form if singular was used
                        if not bad_table.lower().endswith('s') and bad_table.lower() + 's' in self.table_details:
                            plural = bad_table + 's'
                            logger.info(
                                f"Suggesting plural form: {plural} for {bad_table}")
                            return {"valid": False, "error": f"Table '{bad_table}' doesn't exist. Did you mean '{plural}'? Our database uses plural table names (patients, vitals, etc.)."}

                        # Check common table name mismatches
                        if bad_table.lower() == 'lab' or bad_table.lower() == 'labs':
                            return {"valid": False, "error": f"Table '{bad_table}' doesn't exist. Did you mean 'lab_results'?"}

                        # Suggest similar table names
                        similar_tables = self._suggest_similar_names(
                            bad_table, list(self.table_details.keys()))
                        if similar_tables:
                            suggestion = f"Did you mean: {', '.join(similar_tables)}?"
                            return {"valid": False, "error": f"Table '{bad_table}' doesn't exist in the database. {suggestion}"}

                        return {"valid": False, "error": f"Table '{bad_table}' doesn't exist in the database. Check the schema for available tables."}

                elif "no such column" in error_msg.lower():
                    col_match = re.search(
                        r"no such column: ([^\s]+)", error_msg.lower())
                    if col_match:
                        bad_column = col_match.group(1).strip()

                        # Check if this might be the test_name issue in vitals table
                        if bad_column.lower() == "test_name" and "vitals" in sql_query.lower():
                            logger.info(
                                "Detected 'test_name' column error in vitals table")
                            return {"valid": False, "error": f"The vitals table doesn't have a 'test_name' column. It has direct columns like sbp, dbp, weight, etc."}

                        # Check if this might be the id vs patient_id issue
                        if bad_column.lower() == "patient_id" and "patients" in sql_query.lower():
                            if "patients.patient_id" in sql_query.lower():
                                return {"valid": False, "error": f"The patients table uses 'id' not 'patient_id' as its primary key column."}

                        # Check for date vs test_date confusion
                        if bad_column.lower() == "test_date" and "vitals" in sql_query.lower():
                            return {"valid": False, "error": f"The vitals table uses 'date' not 'test_date' for the date column."}

                        # Try to suggest correct column names from all tables
                        all_columns = []
                        for table_name, table_info in self.table_details.items():
                            all_columns.extend(table_info.get('columns', []))

                        similar_columns = self._suggest_similar_names(
                            bad_column, all_columns)
                        if similar_columns:
                            suggestion = f"Did you mean: {', '.join(similar_columns)}?"
                            return {"valid": False, "error": f"Column '{bad_column}' doesn't exist in the referenced tables. {suggestion}"}

                        return {"valid": False, "error": f"Column '{bad_column}' doesn't exist in the referenced tables."}

                # For any other error, return the SQLite error message
                return {"valid": False, "error": f"SQL Error: {error_msg}"}

        except Exception as e:
            logger.error(f"Error validating SQL: {str(e)}")
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def _extract_sql_references(self, sql_query):
        """Extract table and column references from an SQL query"""
        logger.info("Extracting table and column references from SQL query")

        # Convert to lowercase for case-insensitive matching
        sql_lower = sql_query.lower()

        # Extract table references
        # Look for patterns like "FROM table", "JOIN table", "table.column"
        tables = set()

        # Find tables in FROM clauses
        from_matches = re.finditer(r'from\s+([a-z0-9_]+)', sql_lower)
        for match in from_matches:
            tables.add(match.group(1))

        # Find tables in JOIN clauses
        join_matches = re.finditer(r'join\s+([a-z0-9_]+)', sql_lower)
        for match in join_matches:
            tables.add(match.group(1))

        # Find tables in qualified column references (table.column)
        qualified_matches = re.finditer(r'([a-z0-9_]+)\.', sql_lower)
        for match in qualified_matches:
            tables.add(match.group(1))

        # Extract column references
        columns = set()

        # Find columns in SELECT clause
        select_clause = ""
        select_match = re.search(
            r'select\s+(.*?)\s+from', sql_lower, re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            # Remove functions and aliases for cleaner column extraction
            select_clause = re.sub(r'count\s*\(\s*\*\s*\)', '', select_clause)
            select_clause = re.sub(
                r'[a-z0-9_]+\s*\(([^)]*)\)', r'\1', select_clause)
            select_clause = re.sub(r'as\s+[a-z0-9_]+', '', select_clause)

            # Extract columns from cleaned SELECT clause
            for item in select_clause.split(','):
                item = item.strip()
                # Handle qualified columns (table.column)
                if '.' in item:
                    cols = re.findall(r'[a-z0-9_]+\.([a-z0-9_]+)', item)
                    columns.update(cols)
                elif item and item != '*':
                    columns.add(item)

        # Find columns in WHERE, GROUP BY, ORDER BY clauses
        clause_matches = re.finditer(
            r'(where|group\s+by|order\s+by|having)\s+(.*?)(?:limit|$|\s+(?:where|group\s+by|order\s+by|having))', sql_lower, re.DOTALL)
        for clause_match in clause_matches:
            clause = clause_match.group(2).strip()
            # Find qualified columns
            qualified_cols = re.findall(r'([a-z0-9_]+)\.([a-z0-9_]+)', clause)
            for _, col in qualified_cols:
                columns.add(col)

            # Find unqualified columns (not part of a function)
            unqualified_cols = re.findall(
                r'(?<![a-z0-9_\.])[a-z0-9_]+(?=\s*[=<>!]|\s+(?:is|like|in|between))', clause)
            columns.update(unqualified_cols)

        logger.info(f"Extracted tables: {tables}")
        logger.info(f"Extracted columns: {columns}")

        return {"tables": tables, "columns": columns}

    def _validate_schema_references(self, references):
        """Validate table and column references against the schema"""
        logger.info("Validating schema references")

        tables = references.get("tables", set())
        columns = references.get("columns", set())

        # Validate tables
        for table in tables:
            if table not in self.table_details:
                # Check if it's a singular form of a plural table name
                if table + 's' in self.table_details:
                    logger.warning(
                        f"Table '{table}' should be '{table}s' (plural form)")
                    return {"valid": False, "error": f"Table '{table}' doesn't exist. Did you mean '{table}s'? Our database uses plural table names."}

                # Special case for 'lab' -> 'lab_results'
                if table in ['lab', 'labs']:
                    return {"valid": False, "error": f"Table '{table}' doesn't exist. Did you mean 'lab_results'?"}

                # Suggest similar table names
                similar_tables = self._suggest_similar_names(
                    table, list(self.table_details.keys()))
                if similar_tables:
                    suggestion = f"Did you mean: {', '.join(similar_tables)}?"
                    return {"valid": False, "error": f"Table '{table}' doesn't exist in the database. {suggestion}"}

                return {"valid": False, "error": f"Table '{table}' doesn't exist in the database schema."}

        # Validate columns
        invalid_columns = []
        for column in columns:
            if column == '*':  # Wildcard is always valid
                continue

            # Check if column exists in any of the referenced tables
            column_found = False
            for table in tables:
                if table in self.table_details:
                    table_columns = self.table_details[table].get(
                        'columns', [])
                    if column in table_columns or column.lower() in [c.lower() for c in table_columns]:
                        column_found = True
                        break

            if not column_found:
                # Special case handling
                if column == 'patient_id' and 'patients' in tables:
                    invalid_columns.append(
                        f"'{column}' (use 'id' in patients table)")
                elif column == 'test_name' and 'vitals' in tables:
                    invalid_columns.append(
                        f"'{column}' (vitals table has direct columns like sbp, dbp, etc.)")
                elif column == 'test_date' and 'vitals' in tables:
                    invalid_columns.append(
                        f"'{column}' (use 'date' in vitals table)")
                else:
                    invalid_columns.append(f"'{column}'")

        if invalid_columns:
            return {"valid": False, "error": f"Invalid column references: {', '.join(invalid_columns)}"}

        # All references are valid
        return {"valid": True, "error": None}

    def _suggest_similar_names(self, name, options, max_suggestions=3, threshold=0.6):
        """Suggest similar names from available options based on string similarity"""
        import difflib

        name = name.lower()
        options_lower = [opt.lower() for opt in options]

        # Use difflib to get close matches
        similar = difflib.get_close_matches(
            name, options_lower, n=max_suggestions, cutoff=threshold)

        # Map back to original case
        result = []
        for sim in similar:
            idx = options_lower.index(sim)
            result.append(options[idx])

        return result

    def _get_database_path(self):
        """Get the path to the database file from db_query module"""
        try:
            return db_query.get_db_path()
        except:
            logger.warning("Could not get database path from db_query module")
            return None

    def _set_log_level(self, level=logging.INFO):
        """Set the logging level for the AI assistant module"""
        logger.setLevel(level)

        # Remove all existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add a fresh handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.info(f"Logging level set to {level}")

    def _attempt_sql_fix(self, sql_query, error_msg):
        """Attempt to fix common SQL errors automatically using schema information"""
        logger.info(f"Attempting to fix SQL: {sql_query}")
        logger.info(f"Error message: {error_msg}")

        # Store original query for comparison
        original_query = sql_query

        # Create a dictionary of common replacements
        replacements = {
            # Singular to plural table names
            r'\bpatient\b': 'patients',
            r'\bvital\b': 'vitals',
            r'\blab\b(?!_)': 'lab_results',  # Don't match lab_results
            r'\bscore\b': 'scores',
            r'\bpm\b(?!h)': 'pmh',  # Don't match pmh

            # Column name corrections
            r'vitals\.test_date': 'vitals.date',
            r'vitals\.test_name': '',  # Remove test_name reference in vitals
            r'patient\.patient_id': 'patient.id',
            r'patients\.patient_id': 'patients.id',

            # Date function corrections
            r'DATEDIFF\(': 'julianday(',
            r'DATEDIFF\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': 'julianday(\2) - julianday(\1)',
            r'DATE_DIFF\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)': 'julianday(\2) - julianday(\1)',
        }

        # Handle table name errors
        if "no such table" in error_msg.lower():
            # Extract the problematic table
            table_match = re.search(
                r"no such table:\s*([^\s,]+)", error_msg.lower())
            if table_match:
                bad_table = table_match.group(1).strip()
                logger.info(f"Attempting to fix unknown table: {bad_table}")

                # Check if it's a singular form of a plural table
                if bad_table + 's' in self.table_details:
                    # Replace the singular form with the plural form
                    pattern = r'\b' + re.escape(bad_table) + r'\b'
                    sql_query = re.sub(pattern, bad_table +
                                       's', sql_query, flags=re.IGNORECASE)
                    logger.info(
                        f"Fixed singular table name: {bad_table} -> {bad_table}s")
                else:
                    # Suggest similar table names
                    similar_tables = self._suggest_similar_names(
                        bad_table, list(self.table_details.keys()))
                    if similar_tables:
                        # Replace with the most similar table name
                        best_match = similar_tables[0]
                        pattern = r'\b' + re.escape(bad_table) + r'\b'
                        sql_query = re.sub(
                            pattern, best_match, sql_query, flags=re.IGNORECASE)
                        logger.info(
                            f"Replaced unknown table with similar one: {bad_table} -> {best_match}")

        # Handle column name errors
        elif "no such column" in error_msg.lower():
            # Extract the problematic column
            col_match = re.search(
                r"no such column:\s*([^\s,]+)", error_msg.lower())
            if col_match:
                bad_column = col_match.group(1).strip()
                logger.info(f"Attempting to fix unknown column: {bad_column}")

                # Handle qualified column names (table.column)
                if '.' in bad_column:
                    table_name, col_name = bad_column.split('.')
                    if table_name.lower() in self.table_details:
                        # Find similar column in the specified table
                        table_columns = self.table_details[table_name.lower(
                        )]['columns']
                        similar_cols = self._suggest_similar_names(
                            col_name, table_columns)
                        if similar_cols:
                            # Replace with the most similar column name
                            best_match = similar_cols[0]
                            pattern = r'\b' + re.escape(bad_column) + r'\b'
                            replacement = f"{table_name}.{best_match}"
                            sql_query = re.sub(
                                pattern, replacement, sql_query, flags=re.IGNORECASE)
                            logger.info(
                                f"Fixed column reference: {bad_column} -> {replacement}")
                else:
                    # Handle unqualified column names by checking all tables
                    for table_name, table_info in self.table_details.items():
                        table_columns = table_info['columns']
                        similar_cols = self._suggest_similar_names(
                            bad_column, table_columns)
                        if similar_cols:
                            # Replace with the most similar column name
                            best_match = similar_cols[0]
                            pattern = r'\b' + re.escape(bad_column) + r'\b'
                            sql_query = re.sub(
                                pattern, best_match, sql_query, flags=re.IGNORECASE)
                            logger.info(
                                f"Fixed column reference: {bad_column} -> {best_match}")
                            break

                    # Special case handling
                    if bad_column.lower() == 'patient_id' and 'patients' in sql_query.lower():
                        sql_query = re.sub(
                            r'\bpatient_id\b', 'id', sql_query, flags=re.IGNORECASE)
                        logger.info(
                            "Fixed column reference: patient_id -> id in patients table")
                    elif bad_column.lower() == 'test_date' and 'vitals' in sql_query.lower():
                        sql_query = re.sub(
                            r'\btest_date\b', 'date', sql_query, flags=re.IGNORECASE)
                        logger.info(
                            "Fixed column reference: test_date -> date in vitals table")

        # Handle ambiguous column references
        elif "ambiguous column name" in error_msg.lower():
            col_match = re.search(
                r"ambiguous column name:\s*([^\s,]+)", error_msg.lower())
            if col_match:
                ambiguous_col = col_match.group(1).strip()
                logger.info(
                    f"Attempting to fix ambiguous column: {ambiguous_col}")

                # Extract table aliases from the query
                aliases = {}
                alias_matches = re.finditer(
                    r'(?:from|join)\s+([a-z0-9_]+)(?:\s+as)?\s+([a-z0-9_]+)', sql_query.lower())
                for match in alias_matches:
                    table, alias = match.group(1), match.group(2)
                    aliases[alias] = table

                # Find which tables have this column
                tables_with_col = []
                for table, table_info in self.table_details.items():
                    if ambiguous_col.lower() in [col.lower() for col in table_info['columns']]:
                        tables_with_col.append(table)

                if tables_with_col:
                    # Qualify the ambiguous column with the first table reference
                    # This is a simplified approach - ideally we'd use context to decide which table to use
                    if len(tables_with_col) == 1:
                        # Only one potential table - use its alias if found
                        table = tables_with_col[0]
                        alias = None
                        for a, t in aliases.items():
                            if t.lower() == table.lower():
                                alias = a
                                break

                        qualifier = alias if alias else table
                        pattern = r'(?<!\w\.)(\b' + \
                            re.escape(ambiguous_col) + r'\b)(?!\.\w)'
                        replacement = f"{qualifier}.{ambiguous_col}"
                        sql_query = re.sub(
                            pattern, replacement, sql_query, flags=re.IGNORECASE)
                        logger.info(
                            f"Qualified ambiguous column: {ambiguous_col} -> {replacement}")
                    else:
                        # Multiple tables have this column - use context to decide
                        # For now, just use the first table alias found in the query
                        for table in tables_with_col:
                            alias = None
                            for a, t in aliases.items():
                                if t.lower() == table.lower():
                                    alias = a
                                    break

                            if alias:
                                qualifier = alias
                                pattern = r'(?<!\w\.)(\b' + \
                                    re.escape(ambiguous_col) + r'\b)(?!\.\w)'
                                replacement = f"{qualifier}.{ambiguous_col}"
                                sql_query = re.sub(
                                    pattern, replacement, sql_query, flags=re.IGNORECASE)
                                logger.info(
                                    f"Qualified ambiguous column with first alias found: {ambiguous_col} -> {replacement}")
                                break

        # Apply common replacements
        for pattern, replacement in replacements.items():
            sql_query = re.sub(pattern, replacement,
                               sql_query, flags=re.IGNORECASE)

        # Log if query was modified
        if sql_query != original_query:
            logger.info(f"SQL query fixed. Original: {original_query}")
            logger.info(f"Fixed query: {sql_query}")
            return sql_query
        else:
            logger.info("No fixes applied to SQL query")
            return None


def ai_assistant_page():
    """Returns the AI assistant page for the application"""
    ai_assistant = AIAssistant()
    return ai_assistant.view()
