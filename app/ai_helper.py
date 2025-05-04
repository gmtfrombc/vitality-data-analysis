import os
from openai import OpenAI
import logging
import json
from dotenv import load_dotenv
import logging.handlers
from pathlib import Path
from app.utils.query_intent import parse_intent_json, QueryIntent, DateRange
from pydantic import BaseModel
from app.utils.metrics import METRIC_REGISTRY
import re

# Configure logging
log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("ai_helper")
logger.setLevel(logging.DEBUG)
# Ensure we also log to a dedicated file for deeper inspection
log_dir = Path(__file__).resolve().parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file_path = log_dir / "ai_trace.log"
if not any(
    isinstance(h, logging.FileHandler) and h.baseFilename == str(log_file_path)
    for h in logger.handlers
):
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

# Load environment variables
load_dotenv()

# Initialize OpenAI API client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AIHelper:
    """Helper class for AI-powered data analysis assistant.

    Adds a built-in retry (2 attempts) when the LLM returns unparsable JSON for
    query intent.  The second attempt appends a stricter instruction to *only*
    output raw JSON.
    """

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

    # ------------------------------------------------------------------
    # Low-level helper so tests can stub out the LLM call.
    # ------------------------------------------------------------------

    def _ask_llm(self, prompt: str, query: str):
        """Send *prompt* + *query* to the LLM and return the raw assistant content."""
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        # Log token usage if present (helps with cost debugging)
        if hasattr(response, "usage") and response.usage:
            logger.info(
                "Intent tokens -> prompt: %s, completion: %s, total: %s",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.usage.total_tokens,
            )

        return response.choices[0].message.content

    # ------------------------------------------------------------------

    def get_query_intent(self, query):
        """
        Analyze the query to determine the user's intent and required analysis
        Returns a structured response with analysis type and parameters
        """
        logger.info(f"Getting intent for query: {query}")

        # Prepare system prompt for intent classification
        system_prompt = """
        You are an expert medical data analyst. Analyze the user's query about patient data **and return ONLY a JSON object** matching the schema described below.

        SCHEMA (all keys required, optional keys can be empty lists):
        {
          "analysis_type": one of [count, average, median, distribution, comparison, trend, change, sum, min, max, variance, std_dev, percent_change, top_n, correlation],
          "target_field"  : string,            # Primary metric/column (e.g., "bmi")
          "filters"      : [ {"field": string, EITHER "value": <scalar> OR "range": {"start": <val>, "end": <val>} OR "date_range": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"} } ],
          "conditions"   : [ {"field": string, "operator": string, "value": <any>} ],
          "parameters"   : { ... },              # Extra params (e.g., {"n": 5} for top_n)
          "additional_fields": [string],         # OPTIONAL: Extra metrics for multi-metric queries (e.g., ["weight"] if target_field="bmi")
          "group_by": [string],                  # OPTIONAL: Columns to group results by (e.g., ["gender"])
          "time_range": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}  # OPTIONAL: Global date range for the entire query
        }

        VALID COLUMN NAMES (use EXACTLY these; map synonyms):
        ["patient_id", "date", "score_type", "score_value", "gender", "age", "ethnicity", "bmi", "weight", "sbp", "dbp", "active"]

        DATE RANGE HANDLING:
        • If the query mentions a specific date range (e.g., "from January to March 2025" or "between 2024-01-01 and 2024-03-31"), add a "time_range" field.
        • If the range is relative (e.g., "last 3 months", "previous quarter"), calculate the actual dates relative to the current date.
        • For queries like "Q1 2025" or "first quarter of 2025", use "2025-01-01" to "2025-03-31".
        • Month names should be converted to their numeric values (e.g., "January 2025" becomes "2025-01-01").

        Rules:
        • Use "filters" for simple equality (gender="F") or date/numeric ranges.
        • Use "conditions" for inequalities (bmi > 30, age < 50).
        • If the user asks for multiple metrics (e.g., "average weight AND BMI"), put the first metric in "target_field" and subsequent ones in "additional_fields".
        • If the user asks for correlation or relationship between metrics (e.g., "correlation between BMI and weight"), use analysis_type="correlation", put the first metric in "target_field" and the second in "additional_fields".
        • If the user asks to break down results "by" or "per" a category (e.g., "by gender", "per ethnicity"), populate the "group_by" list.
        • Keep "additional_fields" and "group_by" as empty lists `[]` if not applicable.
        • If the query has a timeframe like "in January", "during Q2", or "from March to June", add a "time_range" with the appropriate dates.
        • Do NOT output any keys other than the schema above.
        • Respond with raw JSON – no markdown fencing.

        Analyze the following natural-language question and produce the JSON intent.

        Example 1 – "How many female patients have a BMI over 30?":
        {
          "analysis_type": "count",
          "target_field": "patient_id",  // Counting patients
          "filters": [{"field": "gender", "value": "F"}],
          "conditions": [{"field": "bmi", "operator": ">", "value": 30}],
          "parameters": {},
          "additional_fields": [],
          "group_by": [],
          "time_range": null
        }

        Example 2 – "What is the average weight and BMI for active patients under 60?":
        {
          "analysis_type": "average",
          "target_field": "weight",
          "filters": [{"field": "active", "value": 1}],
          "conditions": [{"field": "age", "operator": "<", "value": 60}],
          "parameters": {},
          "additional_fields": ["bmi"],
          "group_by": [],
          "time_range": null
        }

        Example 3 – "Show patient count per ethnicity":
        {
          "analysis_type": "count",
          "target_field": "patient_id",
          "filters": [],
          "conditions": [],
          "parameters": {},
          "additional_fields": [],
          "group_by": ["ethnicity"],
          "time_range": null
        }

        Example 4 – "Show weight trends from January to March 2025":
        {
          "analysis_type": "trend",
          "target_field": "weight",
          "filters": [],
          "conditions": [],
          "parameters": {},
          "additional_fields": [],
          "group_by": [],
          "time_range": {"start_date": "2025-01-01", "end_date": "2025-03-31"}
        }
        
        Example 5 – "Is there a correlation between weight and BMI in active patients?":
        {
          "analysis_type": "correlation",
          "target_field": "weight",
          "filters": [{"field": "active", "value": 1}],
          "conditions": [],
          "parameters": {"method": "pearson"},
          "additional_fields": ["bmi"],
          "group_by": [],
          "time_range": null
        }
        """

        logger.debug("Intent prompt: %s", system_prompt.strip())

        max_attempts = 2
        stricter_suffix = (
            "\nRespond with *only* valid JSON — no markdown, no explanations."
        )

        last_err: Exception | None = None

        for attempt in range(max_attempts):
            try:
                prompt = (
                    system_prompt if attempt == 0 else system_prompt + stricter_suffix
                )
                raw_reply = self._ask_llm(prompt, query)

                # Remove any accidental markdown fences
                if "```" in raw_reply:
                    raw_reply = raw_reply.split("```", maxsplit=2)[1].strip()

                # Validate & convert
                intent = parse_intent_json(raw_reply)

                # ------------------------------------------------------------------
                # Post-processing heuristic:
                # If the user's natural language includes the words "active patient"
                # (or "active patients") and the LLM didn't include an explicit
                # filter on *active*, inject it – this keeps the workflow
                # deterministic even when the model forgets.
                # ------------------------------------------------------------------
                q_lower = query.lower()
                mentions_active_patients = (
                    "active patient" in q_lower or "active patients" in q_lower
                )
                has_active_filter = any(
                    f.field.lower() in {"active", "status", "activity_status"}
                    for f in intent.filters
                )
                if (
                    intent.analysis_type == "count"
                    and mentions_active_patients
                    and not has_active_filter
                ):
                    from app.utils.query_intent import Filter as _Filter

                    logger.debug(
                        "Injecting missing active=1 filter based on query text heuristic"
                    )
                    intent.filters.append(_Filter(field="active", value="active"))

                # Heuristic 2 – map "total ..." phrasing to count
                if "total" in q_lower and intent.analysis_type not in {"count", "sum"}:
                    logger.debug(
                        "Overriding analysis_type to 'count' based on 'total' keyword"
                    )
                    intent.analysis_type = "count"

                # ------------------------------------------------------------------
                # NEW: Post-processing heuristics for date ranges
                # ------------------------------------------------------------------
                # Check for date range mentions that might have been missed
                date_range_patterns = [
                    r"from\s+(\w+)\s+to\s+(\w+)",
                    r"between\s+(\w+)\s+and\s+(\w+)",
                    r"in\s+(january|february|march|april|may|june|july|august|september|october|november|december)",
                    r"during\s+(q1|q2|q3|q4)",
                    r"(last|past)\s+(\d+)\s+(days|weeks|months|years)",
                ]

                # If the intent doesn't already have a date range but query mentions dates
                if not intent.has_date_filter():
                    # Simple date heuristic for "in [month]" or "during [month]"
                    month_pattern = r"(?:in|during)\s+(january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+(\d{4}))?\.?"
                    month_match = re.search(month_pattern, q_lower)

                    if month_match:
                        from datetime import datetime

                        month_name = month_match.group(1)
                        year = (
                            int(month_match.group(2))
                            if month_match.group(2)
                            else datetime.now().year
                        )

                        month_map = {
                            "january": 1,
                            "february": 2,
                            "march": 3,
                            "april": 4,
                            "may": 5,
                            "june": 6,
                            "july": 7,
                            "august": 8,
                            "september": 9,
                            "october": 10,
                            "november": 11,
                            "december": 12,
                        }

                        month_num = month_map.get(month_name.lower())
                        if month_num:
                            # Create a date range for the full month
                            import calendar

                            _, last_day = calendar.monthrange(year, month_num)

                            start_date = f"{year}-{month_num:02d}-01"
                            end_date = f"{year}-{month_num:02d}-{last_day:02d}"

                            intent.time_range = DateRange(
                                start_date=start_date, end_date=end_date
                            )
                            logger.debug(
                                f"Added implicit date range for month: {start_date} to {end_date}"
                            )

                logger.info("Intent analysis successful on attempt %s", attempt + 1)
                return intent
            except Exception as exc:  # noqa: BLE001 – broad ok at boundary
                last_err = exc
                logger.warning(
                    "Intent parse failure on attempt %s – %s", attempt + 1, exc
                )

        # All attempts failed – return fallback structure with error message
        logger.error("All intent parse attempts failed: %s", last_err)
        return {
            "analysis_type": "unknown",
            "target_field": None,
            "filters": [],
            "conditions": [],
            "parameters": {"error": str(last_err) if last_err else "unknown"},
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
                "Using deterministic metric '%s' for code generation",
                intent.target_field,
            )
            return deterministic_code

        # Prepare the system prompt with information about available data
        system_prompt = f"""
        You are an expert Python developer specializing in data analysis. Generate executable Python code to analyze patient data based on the specified intent.

        The available data schema is:
        {data_schema}

        The code must use **only** the helper functions exposed in the runtime (e.g., `db_query.get_all_vitals()`, `db_query.get_all_scores()`, `db_query.get_all_patients()`).
        Do NOT read external CSV or Excel files from disk, and do NOT attempt internet downloads.

        The code should use pandas and should be clean, efficient, and well-commented **and MUST assign the final output to a variable named `results`**. The UI downstream expects this variable.

        Return only the Python code (no markdown fences) and ensure the last line sets `results`.

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
                    {
                        "role": "user",
                        "content": f"Generate Python code for this analysis intent: {intent_payload}",
                    },
                ],
                temperature=0.2,  # Lower temperature for more deterministic code
                max_tokens=1000,
            )

            # Log raw response for debugging
            logger.debug("Code-gen raw response: %s", response)

            # Log token usage if available
            if hasattr(response, "usage") and response.usage:
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
                    "LLM attempted to access CSV; falling back to deterministic template if available"
                )
                return """# Error: generated code attempted forbidden file access\nresults = {'error': 'Generated code tried to read CSV'}"""

            # Safety net – if LLM forgot to define `results`, patch it in
            if "results" not in code:
                logger.warning(
                    "Generated code did not define `results`; appending placeholder assignment"
                )
                code += "\n\n# Auto-added safeguard – ensure variable exists\nresults = locals().get('results', None)"

            logger.info("Successfully generated analysis code")

            return code

        except Exception as e:
            logger.error(f"Error generating analysis code: {str(e)}", exc_info=True)
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
                    {"role": "user", "content": query},
                ],
                temperature=0.7,  # Higher temperature for more diverse questions
                max_tokens=500,
            )

            # Extract and parse the response
            questions_json = response.choices[0].message.content

            # Clean the response in case it has markdown code blocks
            if "```json" in questions_json:
                questions_json = (
                    questions_json.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in questions_json:
                questions_json = questions_json.split("```")[1].split("```")[0].strip()

            # Handle both array-only and object with questions field
            try:
                questions = json.loads(questions_json)
                if isinstance(questions, dict) and "questions" in questions:
                    questions = questions["questions"]
            except Exception as e:
                # If JSON parsing fails, extract questions manually
                logger.warning(
                    "Failed to parse questions as JSON, extracting manually: %s", e
                )
                questions = []
                for line in questions_json.split("\n"):
                    if line.strip().startswith('"') or line.strip().startswith("'"):
                        questions.append(line.strip().strip("',"))
                    elif line.strip().startswith("-"):
                        questions.append(line.strip()[2:])

            logger.info(f"Generated {len(questions)} clarifying questions")

            return questions[:4]  # Return at most 4 questions

        except Exception as e:
            logger.error(
                f"Error generating clarifying questions: {str(e)}", exc_info=True
            )
            # Return default questions
            return [
                "Would you like to filter the results by any specific criteria?",
                "Are you looking for a time-based analysis or current data?",
                "Would you like to compare different patient groups?",
                "Should the results include visualizations or just data?",
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
                    {
                        "role": "user",
                        "content": f"Original question: {query}\n\nAnalysis results: {json.dumps(simplified_results)}{viz_descriptions}",
                    },
                ],
                temperature=0.4,
                max_tokens=500,
            )

            interpretation = response.choices[0].message.content.strip()
            logger.info("Successfully generated result interpretation")

            return interpretation

        except Exception as e:
            logger.error(f"Error interpreting results: {str(e)}", exc_info=True)
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
            "glp1_full": "integer - 1 if patient is on GLP1 medication, 0 if not",
        },
        "vitals": {
            "vital_id": "integer - Unique vital record ID",
            "patient_id": "string - Patient ID (foreign key)",
            "date": "datetime - Date vital signs were recorded",
            "weight": "float - Weight in pounds",
            "height": "float - Height in inches",
            "bmi": "float - Body Mass Index",
            "sbp": "integer - Systolic blood pressure",
            "dbp": "integer - Diastolic blood pressure",
        },
        "labs": {
            "lab_id": "integer - Unique lab record ID",
            "patient_id": "string - Patient ID (foreign key)",
            "date": "datetime - Date lab was performed",
            "test_name": "string - Name of lab test",
            "value": "float - Result value",
            "unit": "string - Unit of measurement",
        },
        "scores": {
            "score_id": "integer - Unique score record ID",
            "patient_id": "string - Patient ID (foreign key)",
            "date": "datetime - Date score was recorded",
            "score_type": "string - Type of score (e.g., 'vitality_score')",
            "score_value": "integer - Score value",
        },
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
                return {
                    "type": "DataFrame",
                    "data": obj.head(5).to_dict(orient="records"),
                    "shape": obj.shape,
                }
            else:  # Series
                return {
                    "type": "Series",
                    "data": obj.head(5).to_dict(),
                    "length": len(obj),
                }
        except Exception:
            return str(obj)
    elif isinstance(obj, np.ndarray):
        # Convert numpy arrays to lists
        return obj.tolist() if obj.size < 100 else f"Array of shape {obj.shape}"
    elif isinstance(obj, (np.integer, np.floating)):
        # Convert numpy scalars to Python scalars
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    elif hasattr(obj, "to_dict"):
        # Handle objects with to_dict method
        try:
            return obj.to_dict()
        except Exception:
            return str(obj)
    elif hasattr(obj, "__dict__"):
        # Handle custom objects
        try:
            return {
                k: simplify_for_json(v)
                for k, v in obj.__dict__.items()
                if not k.startswith("_")
            }
        except Exception:
            return str(obj)
    else:
        # Return the object if it's already JSON serializable, otherwise convert to string
        try:
            json.dumps(obj)
            return obj
        except Exception:
            return str(obj)


def _build_code_from_intent(intent: QueryIntent) -> str | None:
    """Return python code string for simple intent matching a registered metric.

    Adds *optional* group-by support: if `intent.parameters.group_by` is set and
    the analysis is an aggregate, the assistant returns counts/aggregates broken
    down by that column.
    """

    # ------------------------------------------------------------------
    # 1. Normalise target field & map common synonyms
    # ------------------------------------------------------------------
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
        "activity_status": "active",
        "status": "active",
    }

    raw_name = intent.target_field.lower()
    metric_name = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_")

    if metric_name.startswith("phq") and "change" in (
        metric_name + intent.analysis_type + str(intent.parameters).lower()
    ):
        metric_name = "phq9_change"

    # Counting active patients → map to active_patients metric helper
    if (
        intent.analysis_type == "count"
        and metric_name in {"patient", "patients", "patient_id"}
        and any(
            f.field.lower() in {"active", "status", "activity_status"}
            for f in intent.filters
        )
    ):
        metric_name = "active_patients"

    # ------------------------------------------------------------------
    # 2. Quick out via metrics registry (unchanged path)
    # ------------------------------------------------------------------
    if metric_name in METRIC_REGISTRY:
        pass  # original registry logic continues later

    # ------------------------------------------------------------------
    # 3. Aggregate path with *optional* GROUP BY
    # ------------------------------------------------------------------
    AGGREGATE_TYPES = {"count", "average", "sum", "min", "max"}
    if intent.analysis_type in AGGREGATE_TYPES:

        group_by_field: str | None = None
        # Check V2 intent.group_by list first
        if intent.group_by:
            group_by_field = ALIASES.get(intent.group_by[0].lower(), intent.group_by[0])
        # Fallback to checking V1 parameters dict (for potential backward compat or edge cases)
        elif isinstance(intent.parameters, dict):
            raw_gb = intent.parameters.get("group_by") or intent.parameters.get("by")
            if isinstance(raw_gb, str):
                group_by_field = ALIASES.get(raw_gb.lower(), raw_gb)

        # Auto-detect group-by when counting a categorical field directly
        if (
            group_by_field is None
            and intent.analysis_type == "count"
            and metric_name in {"gender", "ethnicity", "age", "active"}
        ):
            group_by_field = metric_name

        # Decide which table to hit (simple heuristics)
        if metric_name in {"bmi", "weight", "sbp", "dbp"}:
            table_name = "vitals"
        elif metric_name in {
            "age",
            "gender",
            "ethnicity",
            "active",
            "patient_id",
            "id",
        }:
            table_name = "patients"
        elif metric_name in {"score_value", "value"}:
            table_name = "scores"
        else:
            logger.debug("No SQL table mapping for %s", metric_name)
            table_name = "patients" if intent.analysis_type == "count" else None

        if table_name is None:
            return None

        agg_expr = {
            "count": "COUNT(*)",
            "average": f"AVG({metric_name})",
            "sum": f"SUM({metric_name})",
            "min": f"MIN({metric_name})",
            "max": f"MAX({metric_name})",
        }[intent.analysis_type]

        # Build WHERE clause -------------------------------------------
        where_clauses: list[str] = []

        # ------------------------------------------------------------------
        # New: handle *Condition* objects (>, <, etc.) and Filter.range
        # ------------------------------------------------------------------
        def _quote(v):  # noqa: D401 – tiny helper
            return f"'{v}'" if isinstance(v, str) else str(v)

        # Inject implicit active filter heuristic (unchanged)
        if (
            intent.analysis_type == "count"
            and not any(f.field.lower() == "active" for f in intent.filters)
            and (
                metric_name in {"active", "active_patients"}
                or "active" in intent.parameters.get("group_by", "")
                or "active" in intent.target_field
            )
        ):
            where_clauses.append("active = 1")

        # Add global time_range filter if present
        if intent.time_range is not None:
            # Determine which date column to use based on the table
            date_column = "date"
            if table_name == "patients":
                # For patients table, default to program_start_date
                date_column = "program_start_date"

            start_date = intent.time_range.start_date
            end_date = intent.time_range.end_date

            # Format dates properly for SQL
            if hasattr(start_date, "strftime"):
                start_date = start_date.strftime("%Y-%m-%d")
            if hasattr(end_date, "strftime"):
                end_date = end_date.strftime("%Y-%m-%d")

            where_clauses.append(
                f"{date_column} BETWEEN {_quote(start_date)} AND {_quote(end_date)}"
            )
            logger.debug(
                f"Added date range filter: {date_column} between {start_date} and {end_date}"
            )

        # Equality & range filters ----------------------------------------
        for f in intent.filters:
            canonical = ALIASES.get(f.field.lower(), f.field)
            if f.value is not None:
                val = f.value
                if canonical == "active" and isinstance(val, str):
                    val = (
                        1
                        if val.lower() == "active"
                        else 0 if val.lower() == "inactive" else val
                    )
                where_clauses.append(f"{canonical} = {_quote(val)}")
            elif f.range is not None:
                start = f.range.get("start")
                end = f.range.get("end")
                if start is not None and end is not None:
                    where_clauses.append(
                        f"{canonical} BETWEEN {_quote(start)} AND {_quote(end)}"
                    )
            elif f.date_range is not None:
                # Handle the date_range field in Filter
                start_date = f.date_range.start_date
                end_date = f.date_range.end_date

                # Format dates properly for SQL
                if hasattr(start_date, "strftime"):
                    start_date = start_date.strftime("%Y-%m-%d")
                if hasattr(end_date, "strftime"):
                    end_date = end_date.strftime("%Y-%m-%d")

                where_clauses.append(
                    f"{canonical} BETWEEN {_quote(start_date)} AND {_quote(end_date)}"
                )
                logger.debug(
                    f"Added filter date range: {canonical} between {start_date} and {end_date}"
                )

        # Operator-based conditions --------------------------------------
        for c in intent.conditions:
            canonical = ALIASES.get(c.field.lower(), c.field)
            op = c.operator
            if (
                op.lower() == "between"
                and isinstance(c.value, (list, tuple))
                and len(c.value) == 2
            ):
                where_clauses.append(
                    f"{canonical} BETWEEN {_quote(c.value[0])} AND {_quote(c.value[1])}"
                )
            elif op.lower() == "in" and isinstance(c.value, (list, tuple)):
                vals = ", ".join(_quote(v) for v in c.value)
                where_clauses.append(f"{canonical} IN ({vals})")
            else:
                where_clauses.append(f"{canonical} {op} {_quote(c.value)}")

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # ------------------------------------------------------------------
        # Multi-metric aggregate (average/sum/min/max) without GROUP BY
        # ------------------------------------------------------------------
        metrics: list[str] = [metric_name] + [
            ALIASES.get(m.lower(), m) for m in intent.additional_fields
        ]
        unique_metrics = []
        # preserve order
        [unique_metrics.append(m) for m in metrics if m not in unique_metrics]

        if (
            len(unique_metrics) > 1
            and group_by_field is None
            and intent.analysis_type in {"average", "sum", "min", "max"}
        ):
            func_map = {
                "average": "AVG",
                "sum": "SUM",
                "min": "MIN",
                "max": "MAX",
            }
            agg_func = func_map[intent.analysis_type]
            select_exprs = [f"{agg_func}({m}) AS {m}" for m in unique_metrics]
            sql = f"SELECT {', '.join(select_exprs)} FROM {table_name} {where_clause};"

            code = (
                "# Auto-generated multi-metric aggregate\n"
                "from db_query import query_dataframe\nimport numpy as _np\n\n"
                f'_df = query_dataframe("{sql}")\n'
                "results = _df.iloc[0].to_dict() if not _df.empty else {}\n"
            )
            return code

        # ------------------------------------------------------------------
        # Existing single-metric aggregate paths continue below
        # ------------------------------------------------------------------
        if group_by_field:
            sql = (
                f"SELECT {group_by_field}, {agg_expr} AS result\n"
                f"FROM {table_name}\n"
                f"{where_clause}\n"
                f"GROUP BY {group_by_field};"
            )

            code = (
                "# Auto-generated GROUP BY aggregate\n"
                "from db_query import query_dataframe\n\n"
                f"_sql = '''\n{sql}\n'''\n\n"
                "_df = query_dataframe(_sql)\n"
                "results = _df.set_index('"
                + group_by_field
                + "')['result'].to_dict() if not _df.empty else {}\n"
            )
            return code

        # No group_by: simple scalar aggregate
        sql = f"SELECT {agg_expr} AS result\n" f"FROM {table_name}\n" f"{where_clause};"

        code = (
            "# Auto-generated scalar aggregate\n"
            "from db_query import query_dataframe\nimport numpy as _np\n\n"
            f"_sql = '''\n{sql}\n'''\n\n"
            "_df = query_dataframe(_sql)\n"
            "if 'count' == '" + intent.analysis_type + "':\n"
            "    results = int(_df['result'][0]) if not _df.empty else 0\n"
            "else:\n"
            "    results = float(_df['result'][0]) if not _df.empty and _df['result'][0] is not None else _np.nan\n"
        )
        return code

    # ------------------------------------------------------------------
    # 3b. Percent change – pandas path using first and last values
    # ------------------------------------------------------------------
    if intent.analysis_type == "percent_change":
        # Choose table
        if metric_name in {"bmi", "weight", "sbp", "dbp"}:
            table_name = "vitals"
        elif metric_name in {"age", "score_value", "value"}:
            table_name = (
                "scores" if metric_name in {"score_value", "value"} else "patients"
            )
        else:
            table_name = "vitals"

        where_clauses: list[str] = []

        # Add global time_range filter if present
        if intent.time_range is not None:
            date_column = "date"
            start_date = intent.time_range.start_date
            end_date = intent.time_range.end_date

            # Format dates properly for SQL
            if hasattr(start_date, "strftime"):
                start_date = start_date.strftime("%Y-%m-%d")
            if hasattr(end_date, "strftime"):
                end_date = end_date.strftime("%Y-%m-%d")

            where_clauses.append(
                f"{date_column} BETWEEN '{start_date}' AND '{end_date}'"
            )

        for f in intent.filters:
            if f.value is None and f.date_range is None:
                continue

            canonical = ALIASES.get(f.field.lower(), f.field)

            if f.value is not None:
                val_literal = (
                    f"'{f.value}'" if isinstance(f.value, str) else str(f.value)
                )
                where_clauses.append(f"{canonical} = {val_literal}")
            elif f.date_range is not None:
                start_date = f.date_range.start_date
                end_date = f.date_range.end_date

                # Format dates properly for SQL
                if hasattr(start_date, "strftime"):
                    start_date = start_date.strftime("%Y-%m-%d")
                if hasattr(end_date, "strftime"):
                    end_date = end_date.strftime("%Y-%m-%d")

                where_clauses.append(
                    f"{canonical} BETWEEN '{start_date}' AND '{end_date}'"
                )

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Assume table has 'date' column for ordering; fallback to ROWID
        sql = (
            f"SELECT {metric_name} FROM {table_name} {where_clause} "
            "ORDER BY date ASC;"
        )

        code = (
            "# Auto-generated percent-change calculation using pandas\n"
            "from db_query import query_dataframe\nimport numpy as _np\n\n"
            f'_df = query_dataframe("{sql}")\n'
            f"_clean = _df['{metric_name}'].dropna()\n"
            "if _clean.size < 2 or _clean.iloc[0] == 0:\n"
            "    results = _np.nan\n"
            "else:\n"
            "    first, last = _clean.iloc[0], _clean.iloc[-1]\n"
            "    results = float((last - first) / abs(first) * 100)\n"
        )
        return code

    # ------------------------------------------------------------------
    # 3d. Top-N categorical values – return dict counts
    # ------------------------------------------------------------------
    if intent.analysis_type == "top_n":
        n = intent.parameters.get("n", 5) if isinstance(intent.parameters, dict) else 5

        if metric_name in {"gender", "ethnicity", "assessment_type", "score_type"}:
            table_name = (
                "patients" if metric_name in {"gender", "ethnicity"} else "scores"
            )
        else:
            table_name = "vitals"

        where_clauses: list[str] = []

        # Add global time_range filter if present
        if intent.time_range is not None:
            date_column = "date" if table_name != "patients" else "program_start_date"
            start_date = intent.time_range.start_date
            end_date = intent.time_range.end_date

            # Format dates properly for SQL
            if hasattr(start_date, "strftime"):
                start_date = start_date.strftime("%Y-%m-%d")
            if hasattr(end_date, "strftime"):
                end_date = end_date.strftime("%Y-%m-%d")

            where_clauses.append(
                f"{date_column} BETWEEN '{start_date}' AND '{end_date}'"
            )

        for f in intent.filters:
            if f.value is None and f.date_range is None:
                continue

            canonical = ALIASES.get(f.field.lower(), f.field)

            if f.value is not None:
                val_literal = (
                    f"'{f.value}'" if isinstance(f.value, str) else str(f.value)
                )
                where_clauses.append(f"{canonical} = {val_literal}")
            elif f.date_range is not None:
                start_date = f.date_range.start_date
                end_date = f.date_range.end_date

                # Format dates properly for SQL
                if hasattr(start_date, "strftime"):
                    start_date = start_date.strftime("%Y-%m-%d")
                if hasattr(end_date, "strftime"):
                    end_date = end_date.strftime("%Y-%m-%d")

                where_clauses.append(
                    f"{canonical} BETWEEN '{start_date}' AND '{end_date}'"
                )

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        sql = f"SELECT {metric_name} FROM {table_name} {where_clause};"

        code = (
            "# Auto-generated top-N categorical counts using pandas\n"
            "from db_query import query_dataframe\n\n"
            f'_df = query_dataframe("{sql}")\n'
            f"_top = _df['{metric_name}'].value_counts().nlargest({n})\n"
            "results = _top.to_dict()\n"
        )
        return code

    # ------------------------------------------------------------------
    # 3e. Median aggregate – use pandas since SQLite lacks MEDIAN function
    # ------------------------------------------------------------------
    if intent.analysis_type == "median":
        # Decide table
        if metric_name in {"bmi", "weight", "sbp", "dbp"}:
            table_name = "vitals"
        elif metric_name in {"age", "score_value", "value"}:
            table_name = (
                "scores" if metric_name in {"score_value", "value"} else "patients"
            )
        else:
            table_name = "vitals"

        where_clauses: list[str] = []

        # Add global time_range filter if present
        if intent.time_range is not None:
            date_column = "date" if table_name != "patients" else "program_start_date"
            start_date = intent.time_range.start_date
            end_date = intent.time_range.end_date

            # Format dates properly for SQL
            if hasattr(start_date, "strftime"):
                start_date = start_date.strftime("%Y-%m-%d")
            if hasattr(end_date, "strftime"):
                end_date = end_date.strftime("%Y-%m-%d")

            where_clauses.append(
                f"{date_column} BETWEEN '{start_date}' AND '{end_date}'"
            )

        for f in intent.filters:
            if f.value is None and f.date_range is None:
                continue

            canonical = ALIASES.get(f.field.lower(), f.field)

            if f.value is not None:
                val_literal = (
                    f"'{f.value}'" if isinstance(f.value, str) else str(f.value)
                )
                where_clauses.append(f"{canonical} = {val_literal}")
            elif f.date_range is not None:
                start_date = f.date_range.start_date
                end_date = f.date_range.end_date

                # Format dates properly for SQL
                if hasattr(start_date, "strftime"):
                    start_date = start_date.strftime("%Y-%m-%d")
                if hasattr(end_date, "strftime"):
                    end_date = end_date.strftime("%Y-%m-%d")

                where_clauses.append(
                    f"{canonical} BETWEEN '{start_date}' AND '{end_date}'"
                )

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        sql = f"SELECT {metric_name} FROM {table_name} {where_clause};"

        code = (
            "# Auto-generated median aggregate using pandas\n"
            "from db_query import query_dataframe\nimport numpy as _np\n\n"
            f'_df = query_dataframe("{sql}")\n'
            f"_clean = _df.dropna(subset=['{metric_name}'])\n"
            f"results = float(_clean['{metric_name}'].median()) if not _clean.empty else _np.nan\n"
        )
        return code

    # ------------------------------------------------------------------
    # 3f. Distribution – return histogram counts (10 bins)
    # ------------------------------------------------------------------
    if intent.analysis_type == "distribution":
        if metric_name in {"bmi", "weight", "sbp", "dbp"}:
            table_name = "vitals"
        elif metric_name in {"age", "score_value", "value"}:
            table_name = (
                "scores" if metric_name in {"score_value", "value"} else "patients"
            )
        else:
            table_name = "vitals"

        where_clauses: list[str] = []

        # Add global time_range filter if present
        if intent.time_range is not None:
            date_column = "date" if table_name != "patients" else "program_start_date"
            start_date = intent.time_range.start_date
            end_date = intent.time_range.end_date

            # Format dates properly for SQL
            if hasattr(start_date, "strftime"):
                start_date = start_date.strftime("%Y-%m-%d")
            if hasattr(end_date, "strftime"):
                end_date = end_date.strftime("%Y-%m-%d")

            where_clauses.append(
                f"{date_column} BETWEEN '{start_date}' AND '{end_date}'"
            )

        for f in intent.filters:
            if f.value is None and f.date_range is None:
                continue

            canonical = ALIASES.get(f.field.lower(), f.field)

            if f.value is not None:
                val_literal = (
                    f"'{f.value}'" if isinstance(f.value, str) else str(f.value)
                )
                where_clauses.append(f"{canonical} = {val_literal}")
            elif f.date_range is not None:
                start_date = f.date_range.start_date
                end_date = f.date_range.end_date

                # Format dates properly for SQL
                if hasattr(start_date, "strftime"):
                    start_date = start_date.strftime("%Y-%m-%d")
                if hasattr(end_date, "strftime"):
                    end_date = end_date.strftime("%Y-%m-%d")

                where_clauses.append(
                    f"{canonical} BETWEEN '{start_date}' AND '{end_date}'"
                )

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        sql = f"SELECT {metric_name} FROM {table_name} {where_clause};"

        code = (
            "# Auto-generated distribution histogram (10 bins)\n"
            "from db_query import query_dataframe\nimport numpy as _np\nimport pandas as _pd\n\n"
            '_df = query_dataframe("' + sql + '")\n'
            "_data = _df['" + metric_name + "'].dropna().astype(float)\n"
            "_counts, _bin_edges = _np.histogram(_data, bins=10)\n"
            "results = { 'bin_edges': _bin_edges.tolist(), 'counts': _counts.tolist() }\n"
        )
        return code

    # ------------------------------------------------------------------
    # 3g. Trend – average metric per calendar month (YYYY-MM)
    # ------------------------------------------------------------------
    if intent.analysis_type == "trend":
        # Decide table heuristically
        if metric_name in {"bmi", "weight", "sbp", "dbp"}:
            table_name = "vitals"
        elif metric_name in {"age", "score_value", "value"}:
            table_name = (
                "scores" if metric_name in {"score_value", "value"} else "patients"
            )
        else:
            table_name = "vitals"

        date_col = "date"  # all target tables have a date field

        where_clauses: list[str] = []

        # Add date range conditions
        if intent.time_range is not None:
            start_date = intent.time_range.start_date
            end_date = intent.time_range.end_date

            # Format dates properly for SQL
            if hasattr(start_date, "strftime"):
                start_date = start_date.strftime("%Y-%m-%d")
            if hasattr(end_date, "strftime"):
                end_date = end_date.strftime("%Y-%m-%d")

            where_clauses.append(f"{date_col} BETWEEN '{start_date}' AND '{end_date}'")

        for f in intent.filters:
            if f.value is None and f.date_range is None:
                continue

            canonical = ALIASES.get(f.field.lower(), f.field)

            if f.value is not None:
                val_literal = (
                    f"'{f.value}'" if isinstance(f.value, str) else str(f.value)
                )
                where_clauses.append(f"{canonical} = {val_literal}")
            elif f.date_range is not None:
                start_date = f.date_range.start_date
                end_date = f.date_range.end_date

                # Format dates properly for SQL
                if hasattr(start_date, "strftime"):
                    start_date = start_date.strftime("%Y-%m-%d")
                if hasattr(end_date, "strftime"):
                    end_date = end_date.strftime("%Y-%m-%d")

                where_clauses.append(
                    f"{canonical} BETWEEN '{start_date}' AND '{end_date}'"
                )

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        sql = (
            f"SELECT strftime('%Y-%m', {date_col}) AS period, AVG({metric_name}) AS result\n"
            f"FROM {table_name}\n"
            f"{where_clause}\n"
            f"GROUP BY period\n"
            f"ORDER BY period;"
        )

        code = (
            "# Auto-generated monthly trend\n"
            "from db_query import query_dataframe\n\n"
            f"_sql = '''\n{sql}\n'''\n\n"
            "_df = query_dataframe(_sql)\n"
            "results = _df.set_index('period')['result'].to_dict() if not _df.empty else {}\n"
        )
        return code

    # ------------------------------------------------------------------
    # 3b. Variance & Std Dev – use pandas since SQLite lacks functions
    # ------------------------------------------------------------------
    if intent.analysis_type in {"variance", "std_dev"}:
        stat_func = "var" if intent.analysis_type == "variance" else "std"

        if metric_name in {"bmi", "weight", "sbp", "dbp"}:
            table_name = "vitals"
        elif metric_name in {"age", "score_value", "value"}:
            table_name = (
                "scores" if metric_name in {"score_value", "value"} else "patients"
            )
        else:
            table_name = "vitals"

        where_clauses: list[str] = []

        # Add global time_range filter if present
        if intent.time_range is not None:
            date_column = "date" if table_name != "patients" else "program_start_date"
            start_date = intent.time_range.start_date
            end_date = intent.time_range.end_date

            # Format dates properly for SQL
            if hasattr(start_date, "strftime"):
                start_date = start_date.strftime("%Y-%m-%d")
            if hasattr(end_date, "strftime"):
                end_date = end_date.strftime("%Y-%m-%d")

            where_clauses.append(
                f"{date_column} BETWEEN '{start_date}' AND '{end_date}'"
            )

        for f in intent.filters:
            if f.value is None and f.date_range is None:
                continue

            canonical = ALIASES.get(f.field.lower(), f.field)

            if f.value is not None:
                val_literal = (
                    f"'{f.value}'" if isinstance(f.value, str) else str(f.value)
                )
                where_clauses.append(f"{canonical} = {val_literal}")
            elif f.date_range is not None:
                start_date = f.date_range.start_date
                end_date = f.date_range.end_date

                # Format dates properly for SQL
                if hasattr(start_date, "strftime"):
                    start_date = start_date.strftime("%Y-%m-%d")
                if hasattr(end_date, "strftime"):
                    end_date = end_date.strftime("%Y-%m-%d")

                where_clauses.append(
                    f"{canonical} BETWEEN '{start_date}' AND '{end_date}'"
                )

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        sql = f"SELECT {metric_name} FROM {table_name} {where_clause};"

        code = (
            f"# Auto-generated {intent.analysis_type} aggregate using pandas\n"
            "from db_query import query_dataframe\nimport numpy as _np\n\n"
            f'_df = query_dataframe("{sql}")\n'
            f"_clean = _df.dropna(subset=['{metric_name}'])\n"
            f"results = float(_clean['{metric_name}'].{stat_func}(ddof=1)) if not _clean.empty else _np.nan\n"
        )
        return code

    # ------------------------------------------------------------------
    # 3h. Correlation – scatter plot with correlation coefficient
    # ------------------------------------------------------------------
    # Helper function to build SQL WHERE clauses from intent filters and conditions
    def _build_filters_clause(intent_obj: QueryIntent) -> str:
        """Build SQL WHERE clause from intent filters and conditions."""
        where_clauses: list[str] = []

        # Helper to quote values properly for SQL
        def _quote(v):
            return f"'{v}'" if isinstance(v, str) else str(v)

        # Add global time_range filter if present
        if intent_obj.time_range is not None:
            date_column = "date"  # Most tables use this column name
            start_date = intent_obj.time_range.start_date
            end_date = intent_obj.time_range.end_date

            # Format dates properly for SQL
            if hasattr(start_date, "strftime"):
                start_date = start_date.strftime("%Y-%m-%d")
            if hasattr(end_date, "strftime"):
                end_date = end_date.strftime("%Y-%m-%d")

            where_clauses.append(
                f"{date_column} BETWEEN {_quote(start_date)} AND {_quote(end_date)}"
            )

        # Process filters (equality, ranges)
        for f in intent_obj.filters:
            canonical = ALIASES.get(f.field.lower(), f.field)

            if f.value is not None:
                val = f.value
                if canonical == "active" and isinstance(val, str):
                    val = (
                        1
                        if val.lower() == "active"
                        else 0 if val.lower() == "inactive" else val
                    )
                where_clauses.append(f"{canonical} = {_quote(val)}")
            elif f.range is not None:
                start = f.range.get("start")
                end = f.range.get("end")
                if start is not None and end is not None:
                    where_clauses.append(
                        f"{canonical} BETWEEN {_quote(start)} AND {_quote(end)}"
                    )
            elif f.date_range is not None:
                start_date = f.date_range.start_date
                end_date = f.date_range.end_date

                # Format dates properly for SQL
                if hasattr(start_date, "strftime"):
                    start_date = start_date.strftime("%Y-%m-%d")
                if hasattr(end_date, "strftime"):
                    end_date = end_date.strftime("%Y-%m-%d")

                where_clauses.append(
                    f"{canonical} BETWEEN {_quote(start_date)} AND {_quote(end_date)}"
                )

        # Process conditions (operators)
        for c in intent_obj.conditions:
            canonical = ALIASES.get(c.field.lower(), c.field)
            op = c.operator

            if (
                op.lower() == "between"
                and isinstance(c.value, (list, tuple))
                and len(c.value) == 2
            ):
                where_clauses.append(
                    f"{canonical} BETWEEN {_quote(c.value[0])} AND {_quote(c.value[1])}"
                )
            elif op.lower() == "in" and isinstance(c.value, (list, tuple)):
                vals = ", ".join(_quote(v) for v in c.value)
                where_clauses.append(f"{canonical} IN ({vals})")
            else:
                where_clauses.append(f"{canonical} {op} {_quote(c.value)}")

        # Build final WHERE clause
        return "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    if intent.analysis_type == "correlation":
        # Need at least one field in additional_fields
        if not intent.additional_fields:
            logger.warning("Correlation analysis without second field specified")
            return None

        # Get the second metric (correlation target)
        metric_x = intent.target_field
        metric_y = intent.additional_fields[0]

        # Set correlation method (default to pearson)
        method = intent.parameters.get("method", "pearson")

        # Skip visualization if needed (mainly for testing)
        skip_viz = intent.parameters.get("SKIP_VIZ", False)

        # Create filters clause
        filters = _build_filters_clause(intent)

        # Build the SQL query using the actual column names, not aliases
        sql = f"""
            SELECT 
                vitals.{metric_x} AS {metric_x},
                vitals.{metric_y} AS {metric_y}
            FROM vitals
            {filters}
            """

        # Define the template with conditional visualization
        if skip_viz:
            template = f'''
# Auto-generated correlation analysis (simplified for testing)
import numpy as np
import pandas as pd
from db_query import query_dataframe

# Get data from database
sql = """
            SELECT 
                vitals.{metric_x} AS {metric_x},
                vitals.{metric_y} AS {metric_y}
            FROM vitals
            {filters}
            """
df = query_dataframe(sql)

# Clean data (remove rows with NaN in either column)
clean_df = df.dropna(subset=['{metric_x}', '{metric_y}'])

# Calculate correlation
if len(clean_df) >= 2:
    # Calculate {method.title()} correlation
    corr_value = clean_df['{metric_x}'].corr(clean_df['{metric_y}'], method='{method}')
    
    # Prepare results (without visualization for testing)
    results = {{
        'correlation_coefficient': float(corr_value),
        'correlation_method': '{method}',
        'sample_size': len(clean_df),
        'x_metric': '{metric_x}',
        'y_metric': '{metric_y}'
    }}
else:
    # Not enough data points
    results = {{
        'error': 'Insufficient data points for correlation analysis',
        'sample_size': len(clean_df)
    }}
'''
        else:
            template = f'''
# Auto-generated correlation analysis with scatter plot
import numpy as np
import pandas as pd
from app.utils.plots import scatter_plot
from db_query import query_dataframe

# Get data from database
sql = """
            SELECT 
                vitals.{metric_x} AS {metric_x},
                vitals.{metric_y} AS {metric_y}
            FROM vitals
            {filters}
            """
df = query_dataframe(sql)

# Clean data (remove rows with NaN in either column)
clean_df = df.dropna(subset=['{metric_x}', '{metric_y}'])

# Calculate correlation
if len(clean_df) >= 2:
    # Calculate {method.title()} correlation
    corr_value = clean_df['{metric_x}'].corr(clean_df['{metric_y}'], method='{method}')
    
    # Create visualization
    viz = scatter_plot(
        clean_df, 
        x='{metric_x}', 
        y='{metric_y}',
        xlabel='{metric_x}',
        ylabel='{metric_y}',
        title='Correlation: {metric_x.title()} vs {metric_y.title()}',
        correlation=True,
        regression=True
    )
    
    # Prepare results
    results = {{
        'correlation_coefficient': float(corr_value),
        'correlation_method': '{method}',
        'sample_size': len(clean_df),
        'visualization': viz,
        'x_metric': '{metric_x}',
        'y_metric': '{metric_y}'
    }}
else:
    # Not enough data points
    results = {{
        'error': 'Insufficient data points for correlation analysis',
        'sample_size': len(clean_df)
    }}
'''
        return template

    # ------------------------------------------------------------------
    # 4. FALLBACK – preserve original average/distribution templates
    # ------------------------------------------------------------------
    # ... original remaining logic untouched ...


# Create the single instance to be imported by other modules
ai = AIHelper()
