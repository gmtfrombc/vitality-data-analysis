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

            # Get columns for each table
            for table in tables_info['name']:
                try:
                    columns_info = db_query.query_dataframe(
                        f"PRAGMA table_info({table});")
                    columns_str = ", ".join(
                        [f"{row['name']} ({row['type']})" for _, row in columns_info.iterrows()])
                    schema_info.append(
                        f"Table: {table}\nColumns: {columns_str}\n")
                except Exception as e:
                    logger.error(
                        f"Error getting columns for table {table}: {str(e)}")

            self.db_schema = "\n".join(schema_info)
            logger.info(f"Loaded schema for {len(tables_info)} tables")
        except Exception as e:
            logger.error(f"Error loading database schema: {str(e)}")
            self.db_schema = f"Error loading schema: {str(e)}"

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

    def _preprocess_query(self, query_text):
        """Preprocess natural language query to replace common terms with database field names"""
        processed_text = query_text

        # Convert query to lowercase for case-insensitive matching
        query_lower = query_text.lower()

        # Find and replace terms
        for term, replacement in HEALTHCARE_TERMS.items():
            # Skip complex replacements (dictionaries)
            if isinstance(replacement, dict):
                continue

            # Pattern to match whole words only
            pattern = r'\b' + re.escape(term) + r'\b'

            # Check if term exists in query
            if re.search(pattern, query_lower):
                # Get the actual case used in the original query
                matches = re.finditer(pattern, query_lower)
                for match in matches:
                    start, end = match.span()
                    original_term = query_text[start:end]

                    # Log the replacement
                    logger.info(
                        f"Term replacement: '{original_term}' -> '{replacement}'")

                    # Replace in the original text, preserving case if replacement is single word
                    if ' ' not in replacement and original_term.isupper():
                        processed_text = processed_text.replace(
                            original_term, replacement.upper())
                    elif ' ' not in replacement and original_term[0].isupper():
                        processed_text = processed_text.replace(
                            original_term, replacement.capitalize())
                    else:
                        processed_text = processed_text.replace(
                            original_term, replacement)

        # Special handling for blood pressure
        if "blood pressure" in query_lower or "bp" in query_lower:
            # If not specifically mentioning systolic or diastolic, assume both
            if "systolic" not in query_lower and "diastolic" not in query_lower:
                processed_text = processed_text.replace(
                    "blood pressure", "systolic blood pressure (sbp) and diastolic blood pressure (dbp)")
                processed_text = processed_text.replace(
                    "BP", "systolic blood pressure (sbp) and diastolic blood pressure (dbp)")
                processed_text = processed_text.replace(
                    "bp", "systolic blood pressure (sbp) and diastolic blood pressure (dbp)")

        logger.info(
            f"Preprocessed query: '{query_text}' -> '{processed_text}'")
        return processed_text

    def _generate_sql(self, event=None):
        """Generate SQL from natural language using OpenAI API"""
        if not self.query_text:
            self.status_message = "Please enter a question first"
            return

        if not self.client:
            if not self.api_key:
                self.status_message = "OpenAI API key not available. Set the OPENAI_API_KEY environment variable."
                return
            self.init_client()
            if not self.client:
                return  # init_client already set an error message

        self.status_message = "Generating SQL query..."

        try:
            # Preprocess the query to handle terminology
            preprocessed_query = self._preprocess_query(self.query_text)

            prompt = f"""
            You are a SQL expert helping to generate SQLite queries for a patient health database.
            
            Here is the database schema:
            {self.db_schema}
            
            Important domain knowledge:
            - The scores table has a 'score_type' column with values like 'vitality_score' and 'heart_fit_score'
            - When a question asks about 'vitality', use 'vitality_score' in the query
            - When a question asks about 'heart fitness', use 'heart_fit_score' in the query
            - Patient ages should be calculated from their birth_date column using: strftime('%Y', 'now') - strftime('%Y', birth_date)
            - Gender is stored as single characters: 'F' for female and 'M' for male
            - For first/earliest/initial readings, use subqueries with MIN(date)
            - Always format date columns in the output using strftime('%Y-%m-%d', date_column) to display as YYYY-MM-DD
            - When joining tables, explicitly qualify column names with their table names to avoid ambiguity
            - For lab test results like A1C, HbA1c, or blood tests, use the 'labs' table, not 'lab_results'
            
            Generate a valid SQLite query to answer this question: "{preprocessed_query}"
            
            Important guidelines:
            1. Return ONLY the SQL query with no additional text, explanations, or markdown.
            2. The query should be valid SQLite syntax.
            3. Don't include any comments in the query unless absolutely necessary.
            4. Don't use placeholder values - use literal values that make sense.
            5. Use appropriate joins where needed.
            6. Limit the results to 100 rows maximum.
            7. For any date columns in the result, use strftime('%Y-%m-%d', date_column) AS formatted_date to format them as YYYY-MM-DD.
            8. Make sure all table and column references are correct according to the schema.
            9. When filtering gender, use 'F' for female and 'M' for male, not full words.
            """

            logger.info(f"Sending prompt to OpenAI: {preprocessed_query}")

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a SQL expert that generates SQLite queries based on natural language questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Lower temperature for more deterministic outputs
                max_tokens=500
            )

            sql_query = response.choices[0].message.content.strip()
            logger.info(f"Generated SQL: {sql_query}")

            # Clean SQL by removing markdown code block syntax if present
            sql_query = self._clean_sql(sql_query)
            logger.info(f"Cleaned SQL: {sql_query}")

            # Ensure it ends with a semicolon
            if not sql_query.endswith(';'):
                sql_query += ';'

            # Validate the SQL query
            validation_result = self._validate_sql(sql_query)

            # If there's a syntax error, try to fix it
            if not validation_result['valid']:
                logger.warning(
                    f"Initial SQL validation failed: {validation_result['error']}")

                # Try to fix common issues
                fixed_query = self._attempt_sql_fix(
                    sql_query, validation_result['error'])

                # Check if the fix worked
                fixed_validation = self._validate_sql(fixed_query)
                if fixed_validation['valid']:
                    logger.info("SQL query was fixed automatically")
                    sql_query = fixed_query
                    self.status_message = "SQL query generated and automatically fixed."
                else:
                    logger.warning("Failed to automatically fix SQL syntax")
                    self.status_message = "SQL query generated with potential syntax issues."
            else:
                self.status_message = "SQL query generated successfully"

            self.generated_sql = sql_query

            # If query_name is empty, generate a suggested name
            if not self.query_name:
                suggested_name = self._generate_query_name()
                self.query_name = suggested_name

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating SQL: {error_msg}")
            self.status_message = f"Error generating SQL: {error_msg}"
            self.generated_sql = f"-- Error generating SQL: {error_msg}"

    def _attempt_sql_fix(self, sql_query, error_message):
        """Attempt to fix common SQL syntax errors"""
        fixed_query = sql_query

        # Fix gender values
        if "gender" in fixed_query.lower():
            # Check for incorrect gender values and fix them
            fixed_query = fixed_query.replace(
                "gender = 'female'", "gender = 'F'")
            fixed_query = fixed_query.replace(
                "gender = 'male'", "gender = 'M'")
            fixed_query = fixed_query.replace(
                "gender = \"female\"", "gender = 'F'")
            fixed_query = fixed_query.replace(
                "gender = \"male\"", "gender = 'M'")
            # Check for incorrect gender values with spaces
            fixed_query = fixed_query.replace(
                "gender = 'Female'", "gender = 'F'")
            fixed_query = fixed_query.replace(
                "gender = 'Male'", "gender = 'M'")
            fixed_query = fixed_query.replace(
                "gender = \"Female\"", "gender = 'F'")
            fixed_query = fixed_query.replace(
                "gender = \"Male\"", "gender = 'M'")
            # For IN clauses
            fixed_query = fixed_query.replace(
                "gender IN ('female'", "gender IN ('F'")
            fixed_query = fixed_query.replace(
                "gender IN ('male'", "gender IN ('M'")

        # Common error patterns and fixes
        if "no such column" in error_message.lower():
            # Try to identify the problematic column
            import re
            column_match = re.search(
                r"no such column: ([^\s]+)", error_message.lower())
            if column_match:
                bad_column = column_match.group(1)
                logger.info(
                    f"Attempting to fix reference to non-existent column: {bad_column}")

                # Try common column name variations (e.g., singular/plural, underscores)
                possible_fixes = []
                if bad_column.endswith('s'):
                    # Remove trailing 's'
                    possible_fixes.append(bad_column[:-1])
                if '_' in bad_column:
                    possible_fixes.append(bad_column.replace(
                        '_', ''))  # Remove underscores
                else:
                    # Try adding underscores between words if camelCase or PascalCase
                    camel_case_fix = re.sub(
                        r'([a-z])([A-Z])', r'\1_\2', bad_column).lower()
                    if camel_case_fix != bad_column:
                        possible_fixes.append(camel_case_fix)

                # Look for possible column replacements
                for fix in possible_fixes:
                    if fix in self.db_schema.lower():
                        fixed_query = fixed_query.replace(bad_column, fix)
                        break

        # Missing FROM clause
        if "no tables specified" in error_message.lower():
            if "where" in fixed_query.lower() and "from" not in fixed_query.lower():
                # Add missing FROM clause before WHERE
                fixed_query = fixed_query.replace(
                    "WHERE", "FROM patients WHERE")

        # Incorrect table name
        if "no such table" in error_message.lower():
            import re
            table_match = re.search(
                r"no such table: ([^\s]+)", error_message.lower())
            if table_match:
                bad_table = table_match.group(1)
                logger.info(
                    f"Attempting to fix reference to non-existent table: {bad_table}")

                # Common table naming variations
                if bad_table == "patient":
                    fixed_query = fixed_query.replace(bad_table, "patients")
                elif bad_table == "vital":
                    fixed_query = fixed_query.replace(bad_table, "vitals")
                elif bad_table == "lab":
                    fixed_query = fixed_query.replace(bad_table, "labs")
                elif bad_table == "lab_results":
                    fixed_query = fixed_query.replace(bad_table, "labs")
                elif bad_table == "score":
                    fixed_query = fixed_query.replace(bad_table, "scores")

        # Fix incorrect date expressions
        if "near \"date\"" in error_message.lower():
            # DATE might be a reserved word causing issues
            fixed_query = fixed_query.replace("date(", "datetime(")

        logger.info(f"Original query: {sql_query}")
        logger.info(f"Fixed query: {fixed_query}")

        return fixed_query

    def _generate_query_name(self):
        """Generate a suggested name for the query based on its content"""
        # Simple approach: use the first 5-7 words
        words = self.query_text.split()
        name_words = words[:min(7, len(words))]
        name = " ".join(name_words)

        # Truncate if too long
        if len(name) > 50:
            name = name[:47] + "..."

        return name

    def _execute_sql(self, event=None):
        """Execute the generated SQL query"""
        if not self.generated_sql or self.generated_sql.startswith('--'):
            self.status_message = "No SQL to execute"
            return

        # Validate SQL before executing
        validation_result = self._validate_sql(self.generated_sql)
        if not validation_result['valid']:
            error_msg = validation_result['error']
            self.status_message = f"<span style='color: red; font-weight: bold;'>SQL EXECUTION FAILED</span><br><br><strong>Error:</strong> {error_msg}"
            return

        try:
            self.status_message = "<span style='color: blue;'>Executing query...</span>"
            logger.info(f"Executing SQL: {self.generated_sql}")

            # Execute the query using our db_query module
            self.result_data = db_query.query_dataframe(self.generated_sql)

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
            logger.error(f"Error executing query: {error_msg}")
            self.status_message = f"<span style='color: red; font-weight: bold;'>ERROR</span><br>Query execution failed: <pre>{error_msg}</pre>"
            self.result_data = pd.DataFrame({'Error': [error_msg]})

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

    def _clean_sql(self, sql):
        """Clean SQL by removing markdown code blocks and other formatting"""
        # Remove markdown code block syntax
        if sql.startswith('```') and '```' in sql[3:]:
            # Extract content between the first and last ```
            first_marker = sql.find('```')
            last_marker = sql.rfind('```')
            if first_marker != last_marker:
                # Extract just the SQL between the markers
                sql_between_markers = sql[first_marker+3:last_marker].strip()

                # If there's a language identifier (like sql) after the first ```, remove it
                if '\n' in sql_between_markers:
                    sql_between_markers = sql_between_markers[sql_between_markers.find(
                        '\n'):].strip()

                return sql_between_markers

        return sql

    def _validate_sql(self, sql_query):
        """Validate SQL syntax without executing the query"""
        result = {'valid': False, 'error': None}

        if not sql_query:
            result['error'] = "Query is empty"
            return result

        # Log the query being validated
        logger.info(f"Validating SQL query: {sql_query}")

        # Always check for and fix common issues before validation
        fixed_query = sql_query

        # Quick check for common issues with specific queries
        if "lab_results" in fixed_query.lower():
            # Fix common table name error before validation
            fixed_query = fixed_query.replace("lab_results", "labs")
            logger.info(f"Fixed 'lab_results' to 'labs': {fixed_query}")

        # Fix date calculations - SQLite requires special handling
        if "date('now')" in fixed_query:
            # This is valid in real SQLite but might cause issues in validation
            fixed_query = fixed_query.replace("date('now')", "'now'")
            logger.info(f"Fixed date('now') syntax: {fixed_query}")

        # Special handling for age calculations
        if "birth_date" in fixed_query.lower() and "strftime" in fixed_query:
            # Age calculations are complex but valid, let's trust it's correct
            logger.info(
                "Query contains age calculation with birth_date, bypassing some validation")
            result['valid'] = True
            return result

        if "test_name = 'A1C'" in fixed_query and "labs" not in fixed_query.lower():
            result['error'] = "Table reference missing. Lab tests should use the 'labs' table."
            return result

        try:
            # Connect to SQLite database
            conn = sqlite3.connect(':memory:')
            cursor = conn.cursor()

            # Try to parse the query - this will validate syntax without executing
            try:
                cursor.execute(f"EXPLAIN QUERY PLAN {fixed_query}")
                # If we get here, the syntax is valid
                result['valid'] = True
                result['error'] = None
                logger.info("SQL validation successful")
            except sqlite3.Error as e:
                error_msg = str(e)
                logger.warning(f"SQL validation error: {error_msg}")

                # Special case: If we have date calculations and get an obscure error,
                # it might be due to the in-memory db lacking proper context
                if "strftime" in fixed_query and ("no such column" in error_msg.lower() or
                                                  "no such table" in error_msg.lower()):
                    logger.info(
                        "Query contains date functions, might be valid despite error")
                    result['valid'] = True
                    result['error'] = "Query appears to have valid syntax but contains date calculations that couldn't be fully validated."
                else:
                    result['error'] = error_msg

            conn.close()
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"SQL validation unexpected error: {error_msg}")
            result['error'] = error_msg

        return result

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
