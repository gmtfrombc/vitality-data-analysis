import os
from openai import OpenAI
import logging
import json
from dotenv import load_dotenv
import logging.handlers
from pathlib import Path
from app.utils.query_intent import parse_intent_json, QueryIntent
from pydantic import BaseModel
from app.utils.metrics import METRIC_REGISTRY
import re
import db_query  # for global mapping reuse

# Configure logging
log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger('ai_helper')
logger.setLevel(logging.DEBUG)
# Ensure we also log to a dedicated file for deeper inspection
log_dir = Path(__file__).resolve().parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file_path = log_dir / 'ai_trace.log'
if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file_path) for h in logger.handlers):
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(logging.Formatter(log_format))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

# Load environment variables
load_dotenv()

# Initialize OpenAI API client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AIHelper:
    """Helper class for AI-powered data analysis assistant"""

    def __init__(self):
        """Initialize the AI helper"""
        self.conversation_history = []
        self.model = "gpt-4"  # Using GPT-4 for advanced reasoning

    def add_to_history(self, role, content):
        """Add a message to the conversation history"""
        self.conversation_history.append({"role": role, "content": content})
        # Keep conversation history manageable (last 10 messages)
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def get_query_intent(self, query):
        """
        Analyze the query to determine the user's intent and required analysis
        Returns a structured response with analysis type and parameters
        """
        logger.info(f"Getting intent for query: {query}")

        # Prepare system prompt for intent classification
        system_prompt = """
        You are an expert medical data analyst. Analyze the user's query about patient data **and return ONLY a JSON object** matching the schema described below.

        SCHEMA (all keys required):
        {
          "analysis_type": one of [count, average, median, distribution, comparison, trend, change, sum, min, max],
          "target_field"  : string,  # the metric/column of interest
          "filters"      : [ {"field": string, EITHER "value": <scalar> OR "range": {"start": <val>, "end": <val>} } ],
          "conditions"   : [ {"field": string, "operator": string, "value": <any>} ],
          "parameters"   : { ... arbitrary additional params ... }
        }

        VALID COLUMN NAMES (use EXACTLY these; map synonyms to one of them or ask clarifying questions):
        ["patient_id", "date", "score_type", "score_value", "gender", "age", "ethnicity", "bmi", "weight", "sbp", "dbp"]

        Rules:
        • Use a simple *value* for equality filters (gender == "F").
        • Use a *range* dict only when the user specifies a time/number window.
        • Do NOT output any keys other than the schema above.
        • Respond with raw JSON – no markdown fencing.

        Analyze the following natural-language question and produce the JSON intent.
        1. What type of analysis is being requested (counting, statistics, comparison, trend, threshold, etc.)
        2. What data fields are relevant (BMI, weight, blood pressure, age, gender, etc.)
        3. What filters should be applied (gender, age range, activity status, etc.)
        4. What thresholds or conditions apply (above/below a value, top N, etc.)

        Example – "How many female patients have a BMI over 30?":
        {
          "analysis_type": "count",
          "target_field": "bmi",
          "filters": [{"field": "gender", "value": "F"}],
          "conditions": [{"field": "bmi", "operator": ">", "value": 30}],
          "parameters": {}
        }
        """

        logger.debug("Intent prompt: %s", system_prompt.strip())

        try:
            # Call OpenAI API for intent analysis
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,  # Lower temperature for more deterministic response
                max_tokens=500
            )

            # Log raw response for debugging
            logger.debug("Intent raw response: %s", response)

            # Log token usage if available
            if hasattr(response, 'usage') and response.usage:
                logger.info(
                    "Intent tokens -> prompt: %s, completion: %s, total: %s",
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                    response.usage.total_tokens,
                )

            # Extract and parse the response
            intent_json = response.choices[0].message.content

            # Clean the response in case it has markdown code blocks
            if "```json" in intent_json:
                intent_json = intent_json.split(
                    "```json")[1].split("```")[0].strip()
            elif "```" in intent_json:
                intent_json = intent_json.split(
                    "```")[1].split("```")[0].strip()

            # Validate & convert to QueryIntent
            intent = parse_intent_json(intent_json)
            logger.info(f"Intent analysis: {intent}")

            return intent

        except Exception as e:
            logger.error(
                f"Error analyzing query intent: {str(e)}", exc_info=True)
            # Return a default/fallback intent structure
            return {
                "analysis_type": "unknown",
                "target_field": None,
                "filters": [],
                "conditions": [],
                "parameters": {"error": str(e)}
            }

    def generate_analysis_code(self, intent, data_schema):
        """
        Generate Python code to perform the analysis based on the identified intent
        """
        logger.info(f"Generating analysis code for intent: {intent}")

        # First attempt deterministic generation via metrics registry
        deterministic_code = None
        if isinstance(intent, QueryIntent):
            deterministic_code = _build_code_from_intent(intent)

        if deterministic_code:
            logger.info(
                "Using deterministic metric '%s' for code generation", intent.target_field)
            return deterministic_code

        # Prepare the system prompt with information about available data
        system_prompt = f"""
        You are an expert Python developer specializing in data analysis. Generate executable Python code to analyze patient data based on the specified intent. 
        
        The available data schema is:
        {data_schema}
        
        The code must use **only** the helper functions exposed in the runtime (e.g., `db_query.get_all_vitals()`, `db_query.get_all_scores()`, `db_query.get_all_patients()`).
        Do NOT read external CSV or Excel files from disk, and do NOT attempt internet downloads.
        
        The code should use pandas and should be clean, efficient, and well-commented. Return only the Python code, no explanations or markdown.
        
        Include proper error handling and make sure to handle edge cases like empty dataframes and missing values.
        """

        logger.debug("Code-gen prompt: %s", system_prompt.strip())

        try:
            # Ensure intent is JSON-serialisable string
            if isinstance(intent, BaseModel):
                intent_payload = json.dumps(intent.dict())
            else:
                intent_payload = json.dumps(intent)

            # Call OpenAI API for code generation
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",
                        "content": f"Generate Python code for this analysis intent: {intent_payload}"}
                ],
                temperature=0.2,  # Lower temperature for more deterministic code
                max_tokens=1000
            )

            # Log raw response for debugging
            logger.debug("Code-gen raw response: %s", response)

            # Log token usage if available
            if hasattr(response, 'usage') and response.usage:
                logger.info(
                    "Code-gen tokens -> prompt: %s, completion: %s, total: %s",
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                    response.usage.total_tokens,
                )

            # Extract the code from the response
            code = response.choices[0].message.content

            # Clean the response if it contains markdown code blocks
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

            # Safety: if the generated code tries to read CSV, reject it
            if ".csv" in code.lower():
                logger.warning(
                    "LLM attempted to access CSV; falling back to deterministic template if available")
                return """# Error: generated code attempted forbidden file access\nresults = {'error': 'Generated code tried to read CSV'}"""

            logger.info("Successfully generated analysis code")

            return code

        except Exception as e:
            logger.error(
                f"Error generating analysis code: {str(e)}", exc_info=True)
            # Return a simple error-reporting code
            return f"""
            # Error generating analysis code: {str(e)}
            def analysis_error():
                print("An error occurred during code generation")
                return {{"error": "{str(e)}"}}
                
            results = analysis_error()
            """

    def generate_clarifying_questions(self, query):
        """
        Generate relevant clarifying questions based on the user's query
        """
        logger.info(f"Generating clarifying questions for: {query}")

        system_prompt = """
        You are an expert healthcare data analyst. Based on the user's query about patient data, generate 4 relevant clarifying questions that would help provide a more precise analysis. 
        
        The questions should address potential ambiguities about:
        - Time period or date ranges
        - Specific patient demographics or subgroups
        - Inclusion/exclusion criteria
        - Preferred metrics or visualization types
        
        Return the questions as a JSON array of strings.
        """

        try:
            # Call OpenAI API for generating clarifying questions
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,  # Higher temperature for more diverse questions
                max_tokens=500
            )

            # Extract and parse the response
            questions_json = response.choices[0].message.content

            # Clean the response in case it has markdown code blocks
            if "```json" in questions_json:
                questions_json = questions_json.split(
                    "```json")[1].split("```")[0].strip()
            elif "```" in questions_json:
                questions_json = questions_json.split(
                    "```")[1].split("```")[0].strip()

            # Handle both array-only and object with questions field
            try:
                questions = json.loads(questions_json)
                if isinstance(questions, dict) and "questions" in questions:
                    questions = questions["questions"]
            except:
                # If JSON parsing fails, extract questions manually
                logger.warning(
                    "Failed to parse questions as JSON, extracting manually")
                questions = []
                for line in questions_json.split('\n'):
                    if line.strip().startswith('"') or line.strip().startswith("'"):
                        questions.append(line.strip().strip('",\''))
                    elif line.strip().startswith('-'):
                        questions.append(line.strip()[2:])

            logger.info(f"Generated {len(questions)} clarifying questions")

            return questions[:4]  # Return at most 4 questions

        except Exception as e:
            logger.error(
                f"Error generating clarifying questions: {str(e)}", exc_info=True)
            # Return default questions
            return [
                "Would you like to filter the results by any specific criteria?",
                "Are you looking for a time-based analysis or current data?",
                "Would you like to compare different patient groups?",
                "Should the results include visualizations or just data?"
            ]

    def interpret_results(self, query, results, visualizations=None):
        """
        Interpret analysis results and generate human-readable insights
        """
        logger.info("Interpreting analysis results")

        system_prompt = """
        You are an expert healthcare data analyst and medical professional. Based on the patient data analysis results, provide a clear, insightful interpretation that:
        
        1. Directly answers the user's original question
        2. Highlights key findings and patterns in the data
        3. Provides relevant clinical context or healthcare implications
        4. Suggests potential follow-up analyses if appropriate
        
        Your response should be concise (3-5 sentences) but comprehensive, focusing on the most important insights.
        """

        try:
            # Prepare the visualization descriptions
            viz_descriptions = ""
            if visualizations:
                viz_descriptions = "\n\nVisualizations include:\n"
                for i, viz in enumerate(visualizations):
                    viz_descriptions += f"{i+1}. {viz}\n"

            # Prepare a simplified version of the results that's JSON serializable
            simplified_results = simplify_for_json(results)

            # Call OpenAI API for result interpretation
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",
                        "content": f"Original question: {query}\n\nAnalysis results: {json.dumps(simplified_results)}{viz_descriptions}"}
                ],
                temperature=0.4,
                max_tokens=500
            )

            interpretation = response.choices[0].message.content.strip()
            logger.info("Successfully generated result interpretation")

            return interpretation

        except Exception as e:
            logger.error(
                f"Error interpreting results: {str(e)}", exc_info=True)
            # Return a simple fallback interpretation
            return f"Analysis shows the requested data for your query: '{query}'. The results include relevant metrics based on the available patient data."


# Helper function to get data schema for code generation
def get_data_schema():
    """Return a description of the available data schema for code generation"""
    return {
        "patients": {
            "id": "string - Unique patient identifier",
            "first_name": "string - Patient's first name",
            "last_name": "string - Patient's last name",
            "birth_date": "datetime - Patient's date of birth",
            "gender": "string - 'F' for female, 'M' for male",
            "ethnicity": "string - Patient's ethnicity",
            "engagement_score": "integer - Score indicating patient engagement (0-100)",
            "program_start_date": "datetime - When patient enrolled in program",
            "program_end_date": "datetime - When patient completed program (null if still active)",
            "active": "integer - 1 if patient is active, 0 if inactive",
            "etoh": "integer - 1 if patient uses alcohol, 0 if not",
            "tobacco": "integer - 1 if patient uses tobacco, 0 if not",
            "glp1_full": "integer - 1 if patient is on GLP1 medication, 0 if not"
        },
        "vitals": {
            "vital_id": "integer - Unique vital record ID",
            "patient_id": "string - Patient ID (foreign key)",
            "date": "datetime - Date vital signs were recorded",
            "weight": "float - Weight in pounds",
            "height": "float - Height in inches",
            "bmi": "float - Body Mass Index",
            "sbp": "integer - Systolic blood pressure",
            "dbp": "integer - Diastolic blood pressure"
        },
        "labs": {
            "lab_id": "integer - Unique lab record ID",
            "patient_id": "string - Patient ID (foreign key)",
            "date": "datetime - Date lab was performed",
            "test_name": "string - Name of lab test",
            "value": "float - Result value",
            "unit": "string - Unit of measurement"
        },
        "scores": {
            "score_id": "integer - Unique score record ID",
            "patient_id": "string - Patient ID (foreign key)",
            "date": "datetime - Date score was recorded",
            "score_type": "string - Type of score (e.g., 'vitality_score')",
            "score_value": "integer - Score value"
        }
    }


def simplify_for_json(obj):
    """Convert complex objects to JSON-serializable format"""
    import pandas as pd
    import numpy as np

    if isinstance(obj, dict):
        return {k: simplify_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [simplify_for_json(item) for item in obj]
    elif isinstance(obj, (pd.DataFrame, pd.Series)):
        # Convert pandas objects to dictionaries or lists
        try:
            if isinstance(obj, pd.DataFrame):
                return {"type": "DataFrame", "data": obj.head(5).to_dict(orient="records"), "shape": obj.shape}
            else:  # Series
                return {"type": "Series", "data": obj.head(5).to_dict(), "length": len(obj)}
        except:
            return str(obj)
    elif isinstance(obj, np.ndarray):
        # Convert numpy arrays to lists
        return obj.tolist() if obj.size < 100 else f"Array of shape {obj.shape}"
    elif isinstance(obj, (np.integer, np.floating)):
        # Convert numpy scalars to Python scalars
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    elif hasattr(obj, 'to_dict'):
        # Handle objects with to_dict method
        try:
            return obj.to_dict()
        except:
            return str(obj)
    elif hasattr(obj, '__dict__'):
        # Handle custom objects
        try:
            return {k: simplify_for_json(v) for k, v in obj.__dict__.items()
                    if not k.startswith('_')}
        except:
            return str(obj)
    else:
        # Return the object if it's already JSON serializable, otherwise convert to string
        try:
            json.dumps(obj)
            return obj
        except:
            return str(obj)


def _build_code_from_intent(intent: QueryIntent) -> str | None:
    """Return python code string for simple intent matching a registered metric.

    Currently supports analysis_type in {average, count, distribution, change}
    if *target_field* maps directly to a metric name in the registry.
    """
    # Known synonyms → canonical column names
    ALIASES = {
        "test_date": "date",
        "score": "score_value",
        "scorevalue": "score_value",
        "phq9_score": "score_value",
        "phq_score": "score_value",
        "sex": "gender",
        "patient": "patient_id",
        "assessment_type": "assessment_type",
        "score_type": "assessment_type",
    }

    raw_name = intent.target_field.lower()
    metric_name = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_")

    # Heuristic mapping for common synonyms
    if (
        "phq" in metric_name
        and (
            "change" in metric_name
            or "change" in intent.analysis_type
            or "change" in str(intent.parameters).lower()
        )
    ):
        metric_name = "phq9_change"

    if metric_name not in METRIC_REGISTRY:
        # Additional heuristic: PHQ-9 implied via score_type filter
        if any(
            f.field == "score_type" and str(f.value).upper() == "PHQ-9"
            for f in intent.filters
        ):
            metric_name = "phq9_change"
            logger.debug(
                "Heuristic mapped to phq9_change via score_type filter")
        else:
            logger.debug("No deterministic metric found for '%s'", metric_name)
            return None

    # Build filter expressions from intent.filters with alias resolution
    filter_lines: list[str] = []
    canonical_fields: set[str] = set()
    for f in intent.filters:
        original = f.field
        canonical = ALIASES.get(original.lower(), original)
        canonical_fields.add(canonical)

        if f.value is not None:
            filter_lines.append(
                f"df = df[df['{canonical}'] == {repr(f.value)}]")
        elif f.range is not None:
            start_raw = f.range['start']
            end_raw = f.range['end']
            # Only include if both start & end look like ISO dates
            import re as _re
            iso_pattern = r"^\d{4}-\d{2}-\d{2}"
            if _re.match(iso_pattern, str(start_raw)) and _re.match(iso_pattern, str(end_raw)):
                start = repr(start_raw)
                end = repr(end_raw)
                filter_lines.append(
                    f"df = df[(df['{canonical}'] >= {start}) & (df['{canonical}'] <= {end})]"
                )
            else:
                logger.debug(
                    "Ignoring non-date range filter on %s: %s – %s", canonical, start_raw, end_raw)

    demographic_fields = {fld for fld in canonical_fields if fld in {
        "gender", "age", "ethnicity"}}

    merge_lines = []
    if demographic_fields:
        merge_lines.append("patients_df = db_query.get_all_patients()")
        merge_lines.append(
            "if 'patient_id' not in df.columns and 'id' in df.columns:\n    df = df.rename(columns={'id': 'patient_id'})")
        merge_lines.append(
            "df = df.merge(patients_df, left_on='patient_id', right_on='id', how='left')")

    code = f"""
# Auto-generated metric analysis
import pandas as pd
from app.utils.metrics import get_metric
import db_query

# Load relevant table – crude heuristic
df = (
    db_query.get_all_mental_health()
    if '{metric_name}' in ['phq9_change']
    else db_query.get_all_vitals()
)

# Keep only PHQ-9 assessment rows for the metric
if '{metric_name}' == 'phq9_change':
    if 'assessment_type' in df.columns:
        df = df[df['assessment_type'] == 'PHQ-9']
    elif 'score_type' in df.columns:
        df = df[df['score_type'] == 'PHQ-9']

{chr(10).join(merge_lines)}

{chr(10).join(filter_lines)}

metric_func = get_metric('{metric_name}')
# Determine correct score column if using scores table
kwargs = {{}}
if 'score_value' in df.columns and 'value' not in df.columns:
    kwargs['score_col'] = 'score_value'
elif 'score' in df.columns and 'value' not in df.columns:
    kwargs['score_col'] = 'score'
result_series = metric_func(df, **kwargs)

# Default: use the average change across patients (NaN if no data)
if result_series.empty:
    import numpy as _np
    results = _np.nan
else:
    results = result_series.mean()

# If distribution requested, override with descriptive stats (may still be empty)
if '{intent.analysis_type}' == 'distribution':
    results = result_series.describe()

# Fallback: guarantee 'results' variable exists
try:
    results
except NameError:
    results = result_series.mean()
"""
    return code


# Create the single instance to be imported by other modules
ai = AIHelper()
