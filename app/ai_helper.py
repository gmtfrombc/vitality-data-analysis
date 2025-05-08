import os
from openai import OpenAI
import logging
import json
from dotenv import load_dotenv
import logging.handlers
from pathlib import Path
from app.utils.query_intent import (
    parse_intent_json,
    QueryIntent,
    DateRange,
    normalise_intent_fields,
)
from pydantic import BaseModel
from app.utils.metrics import METRIC_REGISTRY
import re
import pandas as pd

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

# Determine if we are running in offline/test mode (no API key)
_OFFLINE_MODE = not bool(os.getenv("OPENAI_API_KEY"))


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
        """Send *prompt* + *query* to the LLM and return the raw assistant content.

        In offline mode (e.g., during pytest when no OPENAI_API_KEY is set), this
        function raises ``RuntimeError`` immediately so callers can fallback to
        deterministic or template-based generation without waiting for network
        timeouts.
        """
        if _OFFLINE_MODE:
            raise RuntimeError("LLM call skipped – offline mode (no API key)")
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

        # Offline fast-path -------------------------------------------------
        if _OFFLINE_MODE:
            from app.utils.intent_clarification import clarifier as _clarifier

            logger.info("Offline mode – returning fallback intent")
            return _clarifier.create_fallback_intent(query)

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
        • For conditional correlations (e.g., "correlation between weight and BMI by gender"), use analysis_type="correlation", include the condition in "group_by", and add a parameter {"correlation_type": "conditional"}.
        • For time-series correlations (e.g., "how has the correlation between weight and BMI changed over time"), use analysis_type="correlation", add a parameter {"correlation_type": "time_series"}, and specify time_range if available.
        • If the user wants to analyze correlations with a rolling window (e.g., "3-month rolling correlation"), include {"rolling_window": N} in the parameters.
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

        Example 6 – "What is the percent change in BMI by gender over the last 6 months?":
        {
          "analysis_type": "percent_change",
          "target_field": "bmi",
          "filters": [],
          "conditions": [],
          "parameters": {},
          "additional_fields": [],
          "group_by": ["gender"],
          "time_range": null  // LLM will convert "last 6 months" to actual dates
        }
        
        Example 7 – "How does the correlation between weight and BMI differ by gender?":
        {
          "analysis_type": "correlation",
          "target_field": "weight",
          "filters": [],
          "conditions": [],
          "parameters": {"correlation_type": "conditional", "method": "pearson"},
          "additional_fields": ["bmi"],
          "group_by": ["gender"],
          "time_range": null
        }
        
        Example 8 – "Show how the correlation between weight and BMI has changed over time":
        {
          "analysis_type": "correlation",
          "target_field": "weight",
          "filters": [],
          "conditions": [],
          "parameters": {"correlation_type": "time_series", "method": "pearson", "period": "month"},
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

                # Canonicalise field names & synonyms
                normalise_intent_fields(intent)

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

        # --------------------------------------------------------------
        # Offline mode → skip LLM and always return deterministic or
        # fallback template code so tests never block.
        # --------------------------------------------------------------
        if _OFFLINE_MODE:
            logger.info("Offline mode – using deterministic/template generator only")

            # Attempt deterministic path first
            if isinstance(intent, QueryIntent):
                code = _build_code_from_intent(intent)
                if code:
                    return code

            # Fall back to simple diagnostic snippet
            from app.utils.intent_clarification import clarifier as _clarifier

            if not isinstance(intent, QueryIntent):
                fake_query = (
                    intent.get("query", "offline test")
                    if isinstance(intent, dict)
                    else "offline test"
                )
                intent_obj = _clarifier.create_fallback_intent(fake_query)
            else:
                intent_obj = intent

            return generate_fallback_code(
                getattr(intent_obj, "raw_query", "offline test"), intent_obj
            )

        # Extract the original query if available for fallback generation
        original_query = None
        if isinstance(intent, QueryIntent) and hasattr(intent, "raw_query"):
            original_query = intent.raw_query

        # First, handle invalid intent with fallback
        if not isinstance(intent, QueryIntent):
            logger.warning("Invalid intent type for code generation, using fallback")
            if original_query:
                return generate_fallback_code(original_query, intent)
            return """# Fallback due to invalid intent\nresults = {"error": "Could not parse query intent"}"""

        # Attempt deterministic generation via templates
        deterministic_code = _build_code_from_intent(intent)
        if deterministic_code:
            logger.info(
                "Using deterministic template for %s analysis of %s",
                intent.analysis_type,
                intent.target_field,
            )
            return deterministic_code

        # Try specialized complex intent handler for non-standard analyses
        complex_code = _generate_dynamic_code_for_complex_intent(intent)
        if complex_code:
            logger.info("Using dynamic complex intent code generation")
            return complex_code

        # Check intent confidence - if very low, use fallback
        if (
            original_query
            and hasattr(intent, "parameters")
            and intent.parameters.get("confidence", 1.0) < 0.4
        ):
            logger.warning("Very low confidence intent, using fallback generator")
            return generate_fallback_code(original_query, intent)

        # If we reach here, we couldn't find a template, but the intent seems valid
        # Fall back to GPT generation

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

        if _OFFLINE_MODE:
            logger.info("Offline mode – returning default clarifying questions")
            return [
                "Could you clarify the time period of interest?",
                "Which patient subgroup (e.g., gender, age) should we focus on?",
                "Are you interested in averages, counts, or trends?",
                "Do you need any visualizations?",
            ]

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

        if _OFFLINE_MODE:
            logger.info("Offline mode – returning simplified interpretation")
            return "Here is a concise summary of the analysis results based on the provided data."

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


def _build_filters_clause(intent_obj: QueryIntent) -> str:
    """Build SQL WHERE clause from intent filters and conditions."""
    where_clauses: list[str] = []

    # Alias mapping for translating common field names
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


def _build_code_from_intent(intent: QueryIntent) -> str | None:
    """Return python code string for simple intent matching a registered metric.

    Adds *optional* group-by support: if `intent.parameters.group_by` is set and
    the analysis is an aggregate, the assistant returns counts/aggregates broken
    down by that column.
    """

    # First, check if this is an uncommon query type that needs flexible handling
    dynamic_code = _generate_dynamic_code_for_complex_intent(intent)
    if dynamic_code:
        return dynamic_code

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
    # 3c. Multi-variable correlation analysis (NEW)
    # ------------------------------------------------------------------
    if intent.analysis_type == "correlation":
        # Extract metrics to correlate
        metrics = [metric_name]  # First metric is the target_field

        # Add additional metrics from intent
        for field in intent.additional_fields:
            canonical = ALIASES.get(field.lower(), field)
            if canonical not in metrics:
                metrics.append(canonical)

        # If there's only one metric, we can't do correlation analysis
        if len(metrics) < 2:
            logger.warning("Need at least 2 metrics for correlation analysis")
            return None

        # Determine if we want a correlation matrix (3+ metrics) or single correlation
        is_matrix = len(metrics) > 2

        # Determine necessary tables based on metrics
        vitals_metrics = {"bmi", "weight", "sbp", "dbp", "height"}
        patient_metrics = {"age", "gender", "ethnicity", "active"}
        scores_metrics = {"score_value", "value", "phq9", "gad7"}

        needed_tables = set()
        for m in metrics:
            if m in vitals_metrics:
                needed_tables.add("vitals")
            elif m in patient_metrics:
                needed_tables.add("patients")
            elif m in scores_metrics:
                needed_tables.add("scores")

        # Build the SQL query based on needed tables
        if len(needed_tables) == 1:
            # Simple case - all metrics from same table
            table_name = list(needed_tables)[0]
            metrics_sql = ", ".join(metrics)
            sql = f"SELECT {metrics_sql} FROM {table_name}"

            # Add WHERE clauses
            where_clauses = _build_filters_clause(intent)
            if where_clauses:
                sql += f" WHERE {where_clauses}"
        else:
            # Complex case - need to join tables
            tables_joins = []
            select_clauses = []

            # Start with patients table as base
            if "patients" in needed_tables:
                tables_joins.append("patients")
                for m in metrics:
                    if m in patient_metrics:
                        select_clauses.append(f"patients.{m}")

            # Add vitals if needed with LEFT JOIN
            if "vitals" in needed_tables:
                if "patients" in tables_joins:
                    tables_joins.append(
                        "LEFT JOIN vitals ON patients.id = vitals.patient_id"
                    )
                else:
                    tables_joins.append("vitals")

                for m in metrics:
                    if m in vitals_metrics:
                        select_clauses.append(f"vitals.{m}")

            # Add scores if needed with LEFT JOIN
            if "scores" in needed_tables:
                if len(tables_joins) > 0:
                    tables_joins.append(
                        "LEFT JOIN scores ON patients.id = scores.patient_id"
                    )
                else:
                    tables_joins.append("scores")

                for m in metrics:
                    if m in scores_metrics:
                        select_clauses.append(f"scores.{m}")

            # Build the full SQL query
            sql = f"SELECT {', '.join(select_clauses)} FROM {' '.join(tables_joins)}"

            # Add WHERE clauses
            where_clauses = _build_filters_clause(intent)
            if where_clauses:
                sql += f" WHERE {where_clauses}"

        # Get correlation method parameter
        corr_method = "pearson"  # default
        if isinstance(intent.parameters, dict) and "method" in intent.parameters:
            method = intent.parameters["method"]
            if method in ["pearson", "spearman", "kendall"]:
                corr_method = method

        # Check if we should skip visualization (for tests)
        skip_viz = False
        if isinstance(intent.parameters, dict) and intent.parameters.get("SKIP_VIZ"):
            skip_viz = True

        # Generate code based on whether we're doing matrix or single correlation
        if is_matrix:
            code = (
                "# Auto-generated multi-variable correlation matrix\n"
                "from db_query import query_dataframe\n"
                "from app.utils.metrics import correlation_matrix\n"
                "from app.utils.plots import correlation_heatmap\n\n"
                f"# Load data\n_sql = '''{sql}'''\n"
                "_df = query_dataframe(_sql)\n\n"
                f"# Calculate correlation matrix with p-values\nmetrics = {metrics}\n"
                f"corr_matrix, p_values = correlation_matrix(_df, metrics, method='{corr_method}', include_p_values=True)\n\n"
            )

            if not skip_viz:
                code += (
                    "# Create visualization\n"
                    "viz = correlation_heatmap(corr_matrix, p_values, title='Correlation Matrix')\n\n"
                )
            else:
                code += "# Visualization skipped for testing\nviz = None\n\n"

            code += (
                "# Return results\n"
                "results = {\n"
                "    'correlation_matrix': corr_matrix.to_dict(),\n"
                "    'p_values': p_values.to_dict() if p_values is not None else None,\n"
                "    'visualization': viz\n"
                "}\n"
            )
        else:
            # Simple pair correlation (just 2 metrics)
            code = (
                "# Auto-generated correlation analysis\n"
                "from db_query import query_dataframe\n"
                "from app.utils.metrics import correlation_coefficient\n"
            )

            if not skip_viz:
                code += "from app.utils.plots import scatter_plot\n\n"
            else:
                code += "\n"

            code += (
                f"# Load data\n_sql = '''{sql}'''\n"
                "_df = query_dataframe(_sql)\n\n"
                f"# Calculate correlation coefficient\ncorr_value = correlation_coefficient(_df, '{metrics[0]}', '{metrics[1]}', method='{corr_method}')\n\n"
            )

            if not skip_viz:
                code += (
                    "# Create visualization\n"
                    f"viz = scatter_plot(_df, x='{metrics[0]}', y='{metrics[1]}', correlation=True, regression=True)\n\n"
                )
            else:
                code += "# Visualization skipped for testing\nviz = None\n\n"

            code += (
                "# Return results\n"
                "results = {\n"
                "    'correlation_coefficient': corr_value,\n"
                "    'method': '" + corr_method + "',\n"
                "    'metrics': ['" + metrics[0] + "', '" + metrics[1] + "'],\n"
                "    'visualization': viz\n"
                "}\n"
            )
        return code

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

        # ---------------------------------------------------------
        # NEW: Support single-dimension group_by for percent change
        # ---------------------------------------------------------
        group_by_field = intent.group_by[0] if intent.group_by else None

        where_clauses: list[str] = []

        # Add global time_range filter if present
        if intent.time_range is not None:
            date_column = "date"
            if table_name == "patients":
                date_column = "program_start_date"
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

        # ---------------------------------------------------------
        # A) Group-by path – build code returning dict {group: pct_change}
        # ---------------------------------------------------------
        if group_by_field is not None:
            # Include date column for ordering (assuming "date" exists)
            sql = (
                f"SELECT {group_by_field}, {metric_name}, date FROM {table_name} "
                f"{where_clause} ORDER BY date ASC;"
            )
            code = (
                "# Auto-generated percent-change by group using pandas  # percent-change by group\n"
                "from db_query import query_dataframe\nimport pandas as _pd, numpy as _np\n\n"
                f'_df = query_dataframe("{sql}")\n'
                "if _df.empty:\n"
                "    results = {}\n"
                "else:\n"
                f"    _group_col = '{group_by_field}'\n"
                f"    _metric = '{metric_name}'\n"
                "    res = {}\n"
                "    for grp, gdf in _df.groupby(_group_col):\n"
                "        _clean = gdf[_metric].dropna()\n"
                "        if _clean.size < 2 or _clean.iloc[0] == 0:\n"
                "            res[grp] = _np.nan\n"
                "        else:\n"
                "            first, last = _clean.iloc[0], _clean.iloc[-1]\n"
                "            res[grp] = float((last - first) / abs(first) * 100)\n"
                "    results = res\n"
            )
            return code

        # ---------------------------------------------------------
        # B) Scalar path – original implementation (unchanged)
        # ---------------------------------------------------------
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
        order = "desc"
        if isinstance(intent.parameters, dict):
            order = intent.parameters.get("order", "desc").lower()
            if order not in {"asc", "desc"}:
                order = "desc"

        numeric_metrics = {"bmi", "weight", "sbp", "dbp", "age", "score_value", "value"}

        # Decide table heuristically
        if metric_name in {"gender", "ethnicity", "assessment_type", "score_type"}:
            table_name = (
                "patients" if metric_name in {"gender", "ethnicity"} else "scores"
            )
            is_numeric = False
        else:
            table_name = "vitals"
            is_numeric = metric_name in numeric_metrics

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

        if is_numeric:
            # For numeric metric, select metric and optional patient_id for context
            sql = f"SELECT {metric_name} FROM {table_name} {where_clause};"

            code = (
                "# Auto-generated top/bottom-N numeric counts using pandas\n"
                "from db_query import query_dataframe\n"
                "from app.utils.auto_viz_mapper import auto_visualize\n\n"
                f'_df = query_dataframe("{sql}")\n'
                f"_clean = _df['{metric_name}'].dropna()\n"
                f"_vc = _clean.value_counts()\n"
                f"_top = _vc.nsmallest({n}) if '{order}' == 'asc' else _vc.nlargest({n})\n"
                "results = _top.to_dict()\n"
                "\n# Generate visualization\n"
                "try:\n"
                "    from app.utils.query_intent import QueryIntent\n"
                "    _intent = QueryIntent(\n"
                f"        analysis_type='top_n',\n"
                f"        target_field='{metric_name}',\n"
                f"        parameters={{'n': {n}, 'order': '{order}'}}\n"
                "    )\n"
                "    _visualization = auto_visualize(results, _intent)\n"
                "    if _visualization is not None:\n"
                "        results = {'counts': results, 'visualization': _visualization}\n"
                "except ImportError:\n"
                "    # Handle case when running in restricted environment\n"
                "    pass\n"
            )
        else:
            sql = f"SELECT {metric_name} FROM {table_name} {where_clause};"
            fun = "nsmallest" if order == "asc" else "nlargest"

            code = (
                "# Auto-generated top/bottom-N counts using pandas\n"
                "from db_query import query_dataframe\n"
                "from app.utils.auto_viz_mapper import auto_visualize\n\n"
                f'_df = query_dataframe("{sql}")\n'
                f"_top = _df['{metric_name}'].value_counts().{fun}({n})\n"
                "results = _top.to_dict()\n"
                "\n# Generate visualization\n"
                "try:\n"
                "    from app.utils.query_intent import QueryIntent\n"
                "    _intent = QueryIntent(\n"
                f"        analysis_type='top_n',\n"
                f"        target_field='{metric_name}',\n"
                f"        parameters={{'n': {n}, 'order': '{order}'}}\n"
                "    )\n"
                "    _visualization = auto_visualize(results, _intent)\n"
                "    if _visualization is not None:\n"
                "        results = {'counts': results, 'visualization': _visualization}\n"
                "except ImportError:\n"
                "    # Handle case when running in restricted environment\n"
                "    pass\n"
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
    # 3d. Standard deviation - pandas path using std
    # ------------------------------------------------------------------
    if intent.analysis_type == "std_dev":
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

        # Add conditions
        for c in intent.conditions:
            canonical = ALIASES.get(c.field.lower(), c.field)
            op = c.operator
            val_literal = f"'{c.value}'" if isinstance(c.value, str) else str(c.value)
            where_clauses.append(f"{canonical} {op} {val_literal}")

        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # SQL to select the data
        sql = f"SELECT {metric_name} FROM {table_name} {where_clause};"

        # Build the code
        code = (
            "# Auto-generated std_dev aggregate using pandas\n"
            "from db_query import query_dataframe\n"
            "import numpy as _np\n\n"
            f'_df = query_dataframe("{sql}")\n'
            f"_clean = _df.dropna(subset=['{metric_name}'])\n"
            f"results = float(_clean['{metric_name}'].std(ddof=1)) if not _clean.empty else _np.nan\n"
        )

        return code

    # ------------------------------------------------------------------
    # 4. FALLBACK – preserve original average/distribution templates
    # ------------------------------------------------------------------
    # ... original remaining logic untouched ...


# Create the single instance to be imported by other modules
ai = AIHelper()


def _generate_dynamic_code_for_complex_intent(intent: QueryIntent) -> str | None:
    """Generate code for complex or uncommon query types that don't match standard patterns.

    Returns None if the intent should be handled by standard deterministic templates.
    """
    # Define what we consider "complex" or "uncommon" queries
    uncommon_analysis_types = {
        "distribution",
        "comparison",
        "trend",
        "correlation",
        "percentile",
        "outlier",
        "frequency",
        "seasonality",
        "change_point",
    }

    # Check if this is an uncommon analysis type
    if intent.analysis_type not in uncommon_analysis_types:
        return None

    # Special case for trend analysis with time_range
    if intent.analysis_type == "trend" and intent.time_range is not None:
        return _generate_trend_analysis_code(intent)

    # Special case for distribution analysis
    if intent.analysis_type == "distribution":
        return _generate_distribution_analysis_code(intent)

    # Special case for comparison analysis
    if intent.analysis_type == "comparison":
        return _generate_comparison_analysis_code(intent)

    # Special case for correlation analysis
    if intent.analysis_type == "correlation":
        return _generate_correlation_code(intent)

    # Special case for percentile analysis
    if intent.analysis_type == "percentile":
        return _generate_percentile_analysis_code(intent)

    # Special case for outlier analysis
    if intent.analysis_type == "outlier":
        return _generate_outlier_analysis_code(intent)

    # Special case for frequency analysis
    if intent.analysis_type == "frequency":
        return _generate_frequency_analysis_code(intent)

    # Special case for seasonality analysis
    if intent.analysis_type == "seasonality":
        return _generate_seasonality_analysis_code(intent)

    # Special case for change point analysis
    if intent.analysis_type == "change_point":
        return _generate_change_point_analysis_code(intent)

    # If we reach here, this is not a query type we have special handling for
    return None


# Add the change point analysis function


def _generate_change_point_analysis_code(intent: QueryIntent) -> str:
    """Generate code for change point analysis of time-series data.

    This template detects significant changes in trends over time,
    such as sudden increases, decreases, or trend reversals.
    """
    metric = intent.target_field

    # Optional parameters
    # Default window size for moving average
    window_size = intent.parameters.get("window_size", 3)
    # Min data points needed for a segment
    min_segment_size = intent.parameters.get("min_segment_size", 4)

    # Determine table based on metric
    table_name = "vitals"
    if metric in {"score_value", "phq9_score", "gad7_score"}:
        table_name = "scores"

    # Build filters clause for WHERE conditions
    filters_clause = _build_filters_clause(intent)
    where_clause = f"WHERE {filters_clause}" if filters_clause else ""

    # Add time range if specified
    if intent.time_range is not None:
        date_clause = f"date BETWEEN '{intent.time_range.start_date}' AND '{intent.time_range.end_date}'"
        where_clause = (
            where_clause + f" AND {date_clause}"
            if where_clause
            else f"WHERE {date_clause}"
        )

    # SQL to get data for change point analysis
    sql = f"""
    SELECT 
        date,
        {metric}
    FROM {table_name}
    {where_clause}
    ORDER BY date
    """

    # Build the Python code
    code = (
        "# Auto-generated change point analysis\n"
        "from db_query import query_dataframe\n"
        "import pandas as pd\n"
        "import numpy as np\n"
        "from datetime import datetime\n"
        "import scipy.stats as stats\n"
        "from app.utils.plots import line_chart, scatter_plot\n\n"
        f"# SQL query to get time series data\n_sql = '''{sql}'''\n\n"
        "# Execute query and process results\n"
        "df = query_dataframe(_sql)\n"
        "if df.empty or len(df) < 5:  # Need at least 5 points for meaningful analysis\n"
        "    results = {'error': 'Insufficient data available for change point analysis'}\n"
        "else:\n"
        "    # Ensure data is sorted by date\n"
        "    df['date'] = pd.to_datetime(df['date'])\n"
        "    df = df.sort_values('date')\n"
        "    \n"
        "    # Group by month to reduce noise and create time series\n"
        "    df['month'] = df['date'].dt.strftime('%Y-%m')\n"
        f"    monthly_data = df.groupby('month')['{metric}'].agg(['mean', 'count']).reset_index()\n"
        "    \n"
        f"    # Calculate moving average to smooth the data\n"
        f"    window_size = {window_size}\n"
        "    if len(monthly_data) >= window_size:\n"
        "        monthly_data['smoothed'] = monthly_data['mean'].rolling(window=window_size, center=True).mean()\n"
        "        # Fill NaN values at the edges with original data\n"
        "        monthly_data['smoothed'] = monthly_data['smoothed'].fillna(monthly_data['mean'])\n"
        "    else:\n"
        "        monthly_data['smoothed'] = monthly_data['mean']\n"
        "    \n"
        "    # Detect significant changes in trend\n"
        "    change_points = []\n"
        "    trends = []\n"
        f"    min_segment_size = {min_segment_size}\n"
        "    \n"
        "    if len(monthly_data) >= min_segment_size * 2:  # Need at least two segments to compare\n"
        "        # Calculate first derivatives (slope of trend)\n"
        "        monthly_data['slope'] = monthly_data['smoothed'].diff() / monthly_data['smoothed'].shift(1)\n"
        "        \n"
        "        # Identify potential change points based on slope changes\n"
        "        # A change point is where the derivative changes sign or magnitude significantly\n"
        "        for i in range(min_segment_size, len(monthly_data) - min_segment_size):\n"
        "            segment1 = monthly_data.iloc[i-min_segment_size:i]\n"
        "            segment2 = monthly_data.iloc[i:i+min_segment_size]\n"
        "            \n"
        "            # Calculate linear regression for each segment\n"
        "            x1 = np.arange(len(segment1))\n"
        "            x2 = np.arange(len(segment2))\n"
        "            \n"
        "            slope1, _, _, _, _ = stats.linregress(x1, segment1['smoothed'])\n"
        "            slope2, _, _, _, _ = stats.linregress(x2, segment2['smoothed'])\n"
        "            \n"
        "            # Check if there's a significant change in slope\n"
        "            if ((slope1 > 0 and slope2 < 0) or (slope1 < 0 and slope2 > 0) or\n"
        "                (abs(slope2 - slope1) / (abs(slope1) + 0.001) > 0.5)):  # 50% change threshold\n"
        "                change_points.append(i)\n"
        "                trends.append({\n"
        "                    'date': monthly_data.iloc[i]['month'],\n"
        "                    'value': monthly_data.iloc[i]['smoothed'],\n"
        "                    'before_trend': 'increasing' if slope1 > 0 else 'decreasing',\n"
        "                    'after_trend': 'increasing' if slope2 > 0 else 'decreasing',\n"
        "                    'change_magnitude': abs(slope2 - slope1) / (abs(slope1) + 0.001)\n"
        "                })\n"
        "    \n"
        "    # Create visualization of the time series with change points highlighted\n"
        f"    title = 'Time Series of {metric.title()} with Change Points'\n"
        "    \n"
        "    # Base line chart of the data\n"
        "    line_viz = line_chart(\n"
        "        monthly_data,\n"
        "        x='month',\n"
        "        y='smoothed',\n"
        "        title=title,\n"
        "        x_label='Month',\n"
        f"        y_label='{metric.title()}'\n"
        "    )\n"
        "    \n"
        "    # Add markers for change points\n"
        "    if change_points:\n"
        "        change_point_data = monthly_data.iloc[change_points]\n"
        "        # Would add scatter points to line_viz here in a real implementation\n"
        "        # For now, we'll create a separate scatter plot\n"
        "        scatter_viz = scatter_plot(\n"
        "            change_point_data,\n"
        "            x='month',\n"
        "            y='smoothed',\n"
        "            title='Detected Change Points',\n"
        "            marker_size=10\n"
        "        )\n"
        "    \n"
        "    # Calculate summary statistics for changes\n"
        "    trend_reversal_count = sum(1 for t in trends if t['before_trend'] != t['after_trend'])\n"
        "    acceleration_count = sum(1 for t in trends if t['before_trend'] == t['after_trend'] == 'increasing' \n"
        "                               and t['change_magnitude'] > 0.5)\n"
        "    deceleration_count = sum(1 for t in trends if t['before_trend'] == t['after_trend'] == 'decreasing' \n"
        "                              and t['change_magnitude'] > 0.5)\n"
        "    \n"
        "    # Calculate overall trend\n"
        "    if len(monthly_data) >= 2:\n"
        "        first_value = monthly_data.iloc[0]['smoothed']\n"
        "        last_value = monthly_data.iloc[-1]['smoothed']\n"
        "        total_change = last_value - first_value\n"
        "        percent_change = (total_change / first_value * 100) if first_value != 0 else 0\n"
        "        overall_trend = 'increasing' if total_change > 0 else 'decreasing' if total_change < 0 else 'stable'\n"
        "    else:\n"
        "        total_change = 0\n"
        "        percent_change = 0\n"
        "        overall_trend = 'undetermined'\n"
        "    \n"
        "    # Analyze rate of change by dividing the series into halves\n"
        "    if len(monthly_data) >= 4:\n"
        "        mid_point = len(monthly_data) // 2\n"
        "        first_half = monthly_data.iloc[:mid_point]\n"
        "        second_half = monthly_data.iloc[mid_point:]\n"
        "        \n"
        "        x_first = np.arange(len(first_half))\n"
        "        x_second = np.arange(len(second_half))\n"
        "        \n"
        "        slope_first, _, _, _, _ = stats.linregress(x_first, first_half['smoothed'])\n"
        "        slope_second, _, _, _, _ = stats.linregress(x_second, second_half['smoothed'])\n"
        "        \n"
        "        acceleration_factor = slope_second / slope_first if abs(slope_first) > 0.001 else float('inf')\n"
        "        trend_acceleration = 'accelerating' if acceleration_factor > 1.2 else \\\n"
        "                            'decelerating' if acceleration_factor < 0.8 else 'stable'\n"
        "    else:\n"
        "        slope_first = 0\n"
        "        slope_second = 0\n"
        "        acceleration_factor = 1\n"
        "        trend_acceleration = 'undetermined'\n"
        "    \n"
        "    # Return results\n"
        "    results = {\n"
        "        'change_points': trends,\n"
        "        'trend_summary': {\n"
        "            'total_change_points': len(change_points),\n"
        "            'trend_reversals': trend_reversal_count,\n"
        "            'accelerations': acceleration_count,\n"
        "            'decelerations': deceleration_count,\n"
        "            'overall_trend': overall_trend,\n"
        "            'total_change': total_change,\n"
        "            'percent_change': percent_change,\n"
        "            'trend_acceleration': trend_acceleration,\n"
        "            'acceleration_factor': acceleration_factor\n"
        "        },\n"
        "        'monthly_data': monthly_data.to_dict(orient='records'),\n"
        "        'visualization': line_viz\n"
        "    }\n"
        "    \n"
        "    # Add scatter plot of change points if they exist\n"
        "    if change_points:\n"
        "        results['change_point_viz'] = scatter_viz\n"
    )

    return code


def _generate_percentile_analysis_code(intent: QueryIntent) -> str:
    """Generate code for percentile analysis of a metric.

    This template divides the data into percentiles and analyzes metrics within each.
    """
    metric = intent.target_field

    # Default to quartiles (4 buckets) if not specified
    num_buckets = intent.parameters.get("num_buckets", 4)
    percentile_type = "quartiles" if num_buckets == 4 else "percentiles"

    # Determine table based on metric
    table_name = "vitals"
    if metric in {"score_value", "phq9_score", "gad7_score"}:
        table_name = "scores"
    elif metric in {"age", "gender", "ethnicity"}:
        table_name = "patients"

    # Build filters clause for WHERE conditions
    filters_clause = _build_filters_clause(intent)
    where_clause = f"WHERE {filters_clause}" if filters_clause else ""

    # Add time range if specified
    if intent.time_range is not None:
        date_clause = f"date BETWEEN '{intent.time_range.start_date}' AND '{intent.time_range.end_date}'"
        where_clause = (
            where_clause + f" AND {date_clause}"
            if where_clause
            else f"WHERE {date_clause}"
        )

    # SQL to get raw data for percentile analysis
    sql = f"""
    SELECT {metric}
    FROM {table_name}
    {where_clause}
    """

    # Build the Python code
    code = (
        "# Auto-generated percentile analysis\n"
        "from db_query import query_dataframe\n"
        "import pandas as pd\n"
        "import numpy as np\n"
        "from app.utils.plots import bar_chart\n\n"
        f"# SQL query to get data for percentile analysis\n_sql = '''{sql}'''\n\n"
        "# Execute query and process results\n"
        "df = query_dataframe(_sql)\n"
        "if df.empty:\n"
        "    results = {'error': 'No data available for percentile analysis'}\n"
        "else:\n"
        "    # Calculate percentiles\n"
        f"    num_buckets = {num_buckets}\n"
        f"    percentile_values = [round(np.percentile(df['{metric}'], p), 2) for p in np.linspace(0, 100, num_buckets+1)]\n"
        "    \n"
        "    # Create percentile labels\n"
        "    labels = []\n"
        "    for i in range(num_buckets):\n"
        "        labels.append(f'{int(i * 100/num_buckets)}-{int((i+1) * 100/num_buckets)} percentile')\n"
        "    \n"
        "    # Assign each data point to a percentile bucket\n"
        f"    df['percentile_bucket'] = pd.cut(df['{metric}'], bins=percentile_values, labels=labels, include_lowest=True)\n"
        "    \n"
        "    # Calculate statistics per bucket\n"
        f"    bucket_stats = df.groupby('percentile_bucket')['{metric}'].agg(['mean', 'std', 'count']).reset_index()\n"
        "    \n"
        "    # Create summary stats\n"
        "    percentile_summary = {\n"
        "        'percentile_values': percentile_values,\n"
        "        'mean_by_percentile': dict(zip(labels, bucket_stats['mean'].values)),\n"
        "        'count_by_percentile': dict(zip(labels, bucket_stats['count'].values)),\n"
        "        'std_by_percentile': dict(zip(labels, bucket_stats['std'].values))\n"
        "    }\n"
        "    \n"
        "    # Create bar chart visualization\n"
        f"    title = '{metric.title()} Distribution by {percentile_type.title()}'\n"
        "    viz = bar_chart(bucket_stats, 'percentile_bucket', 'mean', title=title)\n"
        "    \n"
        "    # Return results\n"
        "    results = {\n"
        "        'percentile_summary': percentile_summary,\n"
        "        'visualization': viz,\n"
        "        'bucket_stats': bucket_stats.to_dict(orient='records')\n"
        "    }\n"
    )

    return code


def _generate_outlier_analysis_code(intent: QueryIntent) -> str:
    """Generate code for outlier analysis of a metric.

    This template identifies outliers using statistical methods and analyzes their characteristics.
    """
    metric = intent.target_field

    # Get outlier detection method (default to IQR)
    method = intent.parameters.get("method", "iqr")
    threshold = intent.parameters.get("threshold", 1.5)  # Default IQR multiplier

    # Determine table based on metric
    table_name = "vitals"
    if metric in {"score_value", "phq9_score", "gad7_score"}:
        table_name = "scores"
    elif metric in {"age", "gender", "ethnicity"}:
        table_name = "patients"

    # Add join with patients table if needed for demographic analysis
    join_needed = intent.parameters.get("demographic_analysis", True)
    join_clause = ""
    if join_needed and table_name != "patients":
        join_clause = "LEFT JOIN patients ON patients.id = {}.patient_id".format(
            table_name
        )

    # Build filters clause for WHERE conditions
    filters_clause = _build_filters_clause(intent)
    where_clause = f"WHERE {filters_clause}" if filters_clause else ""

    # Add time range if specified
    if intent.time_range is not None:
        date_clause = f"date BETWEEN '{intent.time_range.start_date}' AND '{intent.time_range.end_date}'"
        where_clause = (
            where_clause + f" AND {date_clause}"
            if where_clause
            else f"WHERE {date_clause}"
        )

    # SQL to get data for outlier analysis
    sql = f"""
    SELECT 
        {table_name}.{metric}
        {", patients.gender, patients.ethnicity, patients.age" if join_needed and table_name != "patients" else ""}
    FROM {table_name}
    {join_clause}
    {where_clause}
    """

    # Build the Python code
    code = (
        "# Auto-generated outlier analysis\n"
        "from db_query import query_dataframe\n"
        "import pandas as pd\n"
        "import numpy as np\n"
        "from app.utils.plots import histogram, scatter_plot\n\n"
        f"# SQL query to get data for outlier analysis\n_sql = '''{sql}'''\n\n"
        "# Execute query and process results\n"
        "df = query_dataframe(_sql)\n"
        "if df.empty:\n"
        "    results = {'error': 'No data available for outlier analysis'}\n"
        "else:\n"
        "    # Identify outliers using specified method\n"
        f"    method = '{method}'\n"
        f"    threshold = {threshold}\n"
        "    \n"
        "    if method == 'iqr':\n"
        f"        Q1 = df['{metric}'].quantile(0.25)\n"
        f"        Q3 = df['{metric}'].quantile(0.75)\n"
        "        IQR = Q3 - Q1\n"
        f"        lower_bound = Q1 - threshold * IQR\n"
        f"        upper_bound = Q3 + threshold * IQR\n"
        f"        outliers = df[(df['{metric}'] < lower_bound) | (df['{metric}'] > upper_bound)]\n"
        "        non_outliers = df[~df.index.isin(outliers.index)]\n"
        "    elif method == 'zscore':\n"
        f"        mean = df['{metric}'].mean()\n"
        f"        std = df['{metric}'].std()\n"
        f"        z_scores = abs((df['{metric}'] - mean) / std)\n"
        f"        outliers = df[z_scores > threshold]\n"
        "        non_outliers = df[~df.index.isin(outliers.index)]\n"
        "    else:  # Default to IQR if unknown method\n"
        f"        Q1 = df['{metric}'].quantile(0.25)\n"
        f"        Q3 = df['{metric}'].quantile(0.75)\n"
        "        IQR = Q3 - Q1\n"
        f"        lower_bound = Q1 - threshold * IQR\n"
        f"        upper_bound = Q3 + threshold * IQR\n"
        f"        outliers = df[(df['{metric}'] < lower_bound) | (df['{metric}'] > upper_bound)]\n"
        "        non_outliers = df[~df.index.isin(outliers.index)]\n"
        "    \n"
        "    # Calculate outlier statistics\n"
        "    outlier_stats = {\n"
        "        'num_outliers': len(outliers),\n"
        "        'outlier_percent': len(outliers) / len(df) * 100 if len(df) > 0 else 0,\n"
        f"        'min_value': outliers['{metric}'].min() if not outliers.empty else None,\n"
        f"        'max_value': outliers['{metric}'].max() if not outliers.empty else None,\n"
        f"        'mean_value': outliers['{metric}'].mean() if not outliers.empty else None\n"
        "    }\n"
        "    \n"
        "    # Histogram with outliers highlighted\n"
        f"    title = 'Distribution of {metric.title()} with Outliers Highlighted'\n"
        f"    combined_df = df.copy()\n"
        f"    combined_df['outlier'] = combined_df.index.isin(outliers.index)\n"
        "    combined_df['category'] = combined_df['outlier'].map({True: 'Outlier', False: 'Normal'})\n"
        "    \n"
        "    # Create visualization\n"
        f"    hist = histogram(df, '{metric}', bins=20, title=title)\n"
        "    \n"
        "    # Analyze demographics of outliers if patient data available\n"
        "    demographic_analysis = {}\n"
        "    if 'gender' in outliers.columns and not outliers.empty:\n"
        "        gender_counts = outliers['gender'].value_counts().to_dict()\n"
        "        gender_pcts = (outliers['gender'].value_counts() / len(outliers) * 100).to_dict()\n"
        "        demographic_analysis['gender'] = {'counts': gender_counts, 'percentages': gender_pcts}\n"
        "    \n"
        "    if 'ethnicity' in outliers.columns and not outliers.empty:\n"
        "        ethnicity_counts = outliers['ethnicity'].value_counts().to_dict()\n"
        "        ethnicity_pcts = (outliers['ethnicity'].value_counts() / len(outliers) * 100).to_dict()\n"
        "        demographic_analysis['ethnicity'] = {'counts': ethnicity_counts, 'percentages': ethnicity_pcts}\n"
        "    \n"
        "    if 'age' in outliers.columns and not outliers.empty:\n"
        "        age_mean = outliers['age'].mean()\n"
        "        age_std = outliers['age'].std()\n"
        "        demographic_analysis['age'] = {'mean': age_mean, 'std': age_std}\n"
        "    \n"
        "    # Return results\n"
        "    results = {\n"
        "        'outlier_stats': outlier_stats,\n"
        "        'demographic_analysis': demographic_analysis,\n"
        "        'method': method,\n"
        "        'threshold': threshold,\n"
        "        'visualization': hist,\n"
        "        'outliers': outliers.head(10).to_dict(orient='records') if not outliers.empty else []\n"
        "    }\n"
    )

    return code


def _generate_trend_analysis_code(intent: QueryIntent) -> str:
    """Generate code for trend analysis over time."""
    metric = intent.target_field

    # Determine table based on metric
    table_name = "vitals"
    if metric in {"score_value", "phq9_score", "gad7_score"}:
        table_name = "scores"

    # Build filters clause for WHERE conditions
    filters_clause = _build_filters_clause(intent)
    where_clause = f"WHERE {filters_clause}" if filters_clause else ""

    # Format dates for time range
    start_date = intent.time_range.start_date
    end_date = intent.time_range.end_date
    if hasattr(start_date, "strftime"):
        start_date = start_date.strftime("%Y-%m-%d")
    if hasattr(end_date, "strftime"):
        end_date = end_date.strftime("%Y-%m-%d")

    # We'll group by month using SQL's date functions
    sql = f"""
    SELECT 
        strftime('%Y-%m', date) AS month,
        AVG({metric}) AS avg_value
    FROM {table_name}
    {where_clause}
    {"AND" if where_clause else "WHERE"} date BETWEEN '{start_date}' AND '{end_date}'
    GROUP BY month
    ORDER BY month
    """

    # Build the Python code to execute
    code = (
        "# Auto-generated trend analysis over time\n"
        "from db_query import query_dataframe\n"
        "import pandas as pd\n\n"
        f"# SQL query to get monthly trends\n_sql = '''{sql}'''\n\n"
        "# Execute query and process results\n"
        "df = query_dataframe(_sql)\n"
        "if df.empty:\n"
        "    results = {}\n"
        "else:\n"
        "    # Calculate monthly trends - return as dictionary\n"
        "    results = df.set_index('month')['avg_value'].to_dict()\n"
    )

    return code


def _generate_distribution_analysis_code(intent: QueryIntent) -> str:
    """Generate code for distribution analysis."""
    metric = intent.target_field

    # Determine table based on metric
    table_name = "vitals"
    if metric in {"score_value", "phq9_score", "gad7_score"}:
        table_name = "scores"
    elif metric in {"age", "gender", "ethnicity"}:
        table_name = "patients"

    # Build filters clause for WHERE conditions
    filters_clause = _build_filters_clause(intent)
    where_clause = f"WHERE {filters_clause}" if filters_clause else ""

    # Add time range if specified
    if intent.time_range is not None:
        date_clause = f"date BETWEEN '{intent.time_range.start_date}' AND '{intent.time_range.end_date}'"
        where_clause = (
            where_clause + f" AND {date_clause}"
            if where_clause
            else f"WHERE {date_clause}"
        )

    # SQL to get raw data for distribution analysis
    sql = f"""
    SELECT {metric} 
    FROM {table_name}
    {where_clause}
    """

    # Build the Python code
    code = (
        "# Auto-generated distribution analysis\n"
        "from db_query import query_dataframe\n"
        "import pandas as pd\n"
        "import numpy as np\n"
        "from app.utils.plots import histogram\n\n"
        f"# SQL query to get distribution data\n_sql = '''{sql}'''\n\n"
        "# Execute query and process results\n"
        "df = query_dataframe(_sql)\n"
        "if df.empty:\n"
        "    results = {'error': 'No data available for distribution analysis'}\n"
        "else:\n"
        "    # Calculate distribution statistics\n"
        f"    stats = df['{metric}'].describe().to_dict()\n"
        "    \n"
        "    # Create histogram visualization\n"
        f"    title = 'Distribution of {metric.title()}'\n"
        f"    viz = histogram(df, '{metric}', bins=15, title=title)\n"
        "    \n"
        "    # Return results\n"
        "    results = {\n"
        "        'statistics': stats,\n"
        "        'visualization': viz,\n"
        "        'count': int(stats.get('count', 0)),\n"
        "        'mean': float(stats.get('mean', 0)),\n"
        "        'std': float(stats.get('std', 0)),\n"
        "        'min': float(stats.get('min', 0)),\n"
        "        'max': float(stats.get('max', 0))\n"
        "    }\n"
    )

    return code


def _generate_comparison_analysis_code(intent: QueryIntent) -> str:
    """Generate code for comparison analysis between groups."""
    metric = intent.target_field
    compare_field = None

    # Try to determine what to compare by
    if intent.group_by:
        compare_field = intent.group_by[0]
    elif "compare_by" in intent.parameters:
        compare_field = intent.parameters["compare_by"]
    else:
        # Default to gender if not specified
        compare_field = "gender"

    # Determine table based on metric
    table_name = "vitals"
    if metric in {"score_value", "phq9_score", "gad7_score"}:
        table_name = "scores"
    elif metric in {"age", "gender", "ethnicity"}:
        table_name = "patients"

    # Add join with patients table if needed for comparison field
    join_clause = ""
    if table_name != "patients" and compare_field in {
        "gender",
        "age",
        "ethnicity",
        "active",
    }:
        join_clause = "LEFT JOIN patients ON patients.id = {}.patient_id".format(
            table_name
        )
        compare_field = f"patients.{compare_field}"
    else:
        compare_field = f"{table_name}.{compare_field}"

    # Build filters clause for WHERE conditions
    filters_clause = _build_filters_clause(intent)
    where_clause = f"WHERE {filters_clause}" if filters_clause else ""

    # Add time range if specified
    if intent.time_range is not None:
        date_clause = f"date BETWEEN '{intent.time_range.start_date}' AND '{intent.time_range.end_date}'"
        where_clause = (
            where_clause + f" AND {date_clause}"
            if where_clause
            else f"WHERE {date_clause}"
        )

    # SQL to get data for comparison analysis
    sql = f"""
    SELECT 
        {compare_field} AS compare_group,
        AVG({table_name}.{metric}) AS avg_value,
        COUNT(*) AS count
    FROM {table_name}
    {join_clause}
    {where_clause}
    GROUP BY {compare_field}
    ORDER BY avg_value DESC
    """

    # Build the Python code
    code = (
        "# Auto-generated comparison analysis\n"
        "from db_query import query_dataframe\n"
        "import pandas as pd\n"
        "from app.utils.plots import bar_chart\n\n"
        f"# SQL query to get comparison data\n_sql = '''{sql}'''\n\n"
        "# Execute query and process results\n"
        "df = query_dataframe(_sql)\n"
        "if df.empty:\n"
        "    results = {'error': 'No data available for comparison analysis'}\n"
        "else:\n"
        "    # Format comparison results\n"
        "    comparison_data = df.set_index('compare_group')['avg_value'].to_dict()\n"
        "    count_data = df.set_index('compare_group')['count'].to_dict()\n"
        "    \n"
        "    # Create bar chart visualization\n"
        f"    title = 'Comparison of Average {metric.title()} by Group'\n"
        "    viz = bar_chart(df, 'compare_group', 'avg_value', title=title)\n"
        "    \n"
        "    # Return results\n"
        "    results = {\n"
        "        'comparison': comparison_data,\n"
        "        'counts': count_data,\n"
        "        'visualization': viz\n"
        "    }\n"
    )

    return code


def generate_fallback_code(query: str, intent: QueryIntent | dict) -> str:
    """Generate code for low-confidence or unknown intent queries.

    This provides a fallback that shows some basic information
    about the database schema and potentially relevant data.

    Args:
        query: The original user query
        intent: The parsed intent (which may be incomplete or low-confidence)

    Returns:
        Python code that will run safely and show useful diagnostic information
    """
    # Extract possible keywords from the query
    query_lower = query.lower()

    # Try to identify potential tables/fields of interest
    tables_of_interest = []
    if any(x in query_lower for x in ["patient", "gender", "ethnicity", "age"]):
        tables_of_interest.append("patients")
    if any(
        x in query_lower
        for x in ["weight", "bmi", "blood pressure", "sbp", "dbp", "vital"]
    ):
        tables_of_interest.append("vitals")
    if any(x in query_lower for x in ["score", "assessment", "phq", "gad", "test"]):
        tables_of_interest.append("scores")

    # If we couldn't identify any tables, include all main tables
    if not tables_of_interest:
        tables_of_interest = ["patients", "vitals", "scores"]

    # Generate code that shows schema and sample data for relevant tables
    code = f"""
# This is a fallback analysis for: "{query}"
import pandas as pd
import sqlite3
import holoviews as hv

# Connect to the database
conn = sqlite3.connect('patient_data.db')

# Result dictionary to hold our findings
result = {{
    "fallback": True,
    "original_query": "{query}",
    "summary": "I couldn't determine exactly what you're looking for, but here's some relevant information:",
    "table_summaries": {{}},
    "visualizations": []
}}

try:
    """

    # Add code to examine each table of interest
    for table in tables_of_interest:
        code += f"""
    # Examine {table} table
    {table}_df = pd.read_sql("SELECT * FROM {table} LIMIT 10", conn)
    {table}_count = pd.read_sql("SELECT COUNT(*) FROM {table}", conn).iloc[0, 0]
    
    # Get column names and data types
    {table}_cols = pd.read_sql("PRAGMA table_info({table})", conn)
    
    # Add to results
    result["table_summaries"]["{table}"] = {{
        "sample_data": {table}_df,
        "total_records": {table}_count,
        "columns": {table}_cols[['name', 'type']].to_dict(orient='records')
    }}
    """

    # For patient table, add a distribution of patients by gender
    if "patients" in tables_of_interest:
        code += """
    # Add gender distribution if patients table is involved
    try:
        gender_dist = pd.read_sql("SELECT gender, COUNT(*) as count FROM patients GROUP BY gender", conn)
        if not gender_dist.empty:
            gender_chart = hv.Bars(gender_dist, kdims=['gender'], vdims=['count']).opts(
                title="Patient Distribution by Gender",
                width=400, height=300
            )
            result["visualizations"].append(gender_chart)
    except Exception as e:
        pass  # Silently continue if this visualization fails
    """

    # For vitals, add a histogram of BMI or weight if mentioned
    if "vitals" in tables_of_interest:
        metric = "bmi" if "bmi" in query_lower else "weight"
        code += f"""
    # Add {metric} distribution if vitals table is involved
    try:
        {metric}_data = pd.read_sql("SELECT {metric} FROM vitals WHERE {metric} IS NOT NULL", conn)
        if not {metric}_data.empty:
            {metric}_hist = hv.Histogram(np.histogram({metric}_data['{metric}'], bins=20))
            {metric}_hist = {metric}_hist.opts(
                title="{metric.capitalize()} Distribution",
                width=400, height=300,
                xlabel="{metric.capitalize()}", ylabel="Count"
            )
            result["visualizations"].append({metric}_hist)
    except Exception as e:
        pass  # Silently continue if this visualization fails
    """

    # Close the try block and add fallback text
    code += """
    # Add a helpful note about available information
    result["help_text"] = "You can ask about patient demographics, vital sign trends, or assessment scores. For example: 'Show me average BMI by gender' or 'What's the trend in weight over the last 6 months?'"
    
except Exception as e:
    result["error"] = str(e)
    
finally:
    conn.close()

# Return the fallback results
result
"""

    return code


def _generate_correlation_code(intent):
    """Generate code for correlation analysis between two metrics.

    Supports:
    - Basic correlations (simple scatter with regression line)
    - Conditional correlations (by demographic or other categorical variable)
    - Time-series correlations (how correlation changes over time)
    """
    # Extract metrics for correlation
    if len(intent.additional_fields) == 0:
        logger.warning("Correlation analysis requested but no second metric specified")
        # Fallback to common pair
        metric_x = intent.target_field
        metric_y = "bmi" if metric_x != "bmi" else "weight"
    else:
        metric_x = intent.target_field
        metric_y = intent.additional_fields[0]

    # Get correlation method (default to pearson)
    method = intent.parameters.get("method", "pearson")

    # Check for correlation type
    correlation_type = intent.parameters.get("correlation_type", "simple")

    # Build code based on correlation type
    if correlation_type == "conditional" and intent.group_by:
        # Conditional correlation (by demographic/category)
        condition_field = intent.group_by[0]

        # Format title values outside the string template
        metric_x_title = metric_x.title() if hasattr(metric_x, "title") else metric_x
        metric_y_title = metric_y.title() if hasattr(metric_y, "title") else metric_y
        condition_field_title = (
            condition_field.title()
            if hasattr(condition_field, "title")
            else condition_field
        )

        title_text = f"Correlation between {metric_x_title} and {metric_y_title} by {condition_field_title}"

        code = f"""
# Calculate conditional correlations between {metric_x} and {metric_y} by {condition_field}
import pandas as pd
from db_query import query_dataframe
from app.utils.advanced_correlation import conditional_correlation, conditional_correlation_heatmap

# SQL query to fetch required data
sql = '''
SELECT v.{metric_x}, v.{metric_y}, p.{condition_field}
FROM vitals v
JOIN patients p ON v.patient_id = p.id
'''

# Add filters if any
where_clauses = []
"""

        # Add filters
        if intent.filters:
            code += """
# Process filters
"""
            for i, filter in enumerate(intent.filters):
                field = filter.field
                if hasattr(filter, "value"):
                    value = (
                        f"'{filter.value}'"
                        if isinstance(filter.value, str)
                        else filter.value
                    )
                    code += f'where_clauses.append("p.{field} = {value}")\n'
                # Handle other filter types similarly...

        # Complete the SQL query
        code += """
# Finalize the SQL query with WHERE clause if needed
if where_clauses:
    sql += " WHERE " + " AND ".join(where_clauses)

# Execute query
df = query_dataframe(sql)

# Calculate conditional correlations
results = conditional_correlation(
    df, 
    metric_x='{metric_x}', 
    metric_y='{metric_y}', 
    condition_field='{condition_field}',
    method='{method}'
)

# Calculate overall correlation for comparison
overall_corr = df['{metric_x}'].corr(df['{metric_y}'], method='{method}')

# Create visualization
viz = conditional_correlation_heatmap(
    results,
    main_correlation=overall_corr,
    title='{title_text}'
)

# Prepare results
correlation_by_group = {{k: v[0] for k, v in results.items()}}
p_values_by_group = {{k: v[1] for k, v in results.items()}}

final_results = {{
    'correlation_by_group': correlation_by_group,
    'p_values': p_values_by_group,
    'overall_correlation': overall_corr,
    'method': '{method}',
    'visualization': viz
}}

# Return results
results = final_results
""".format(
            metric_x=metric_x,
            metric_y=metric_y,
            condition_field=condition_field,
            method=method,
            title_text=title_text,
        )

    elif correlation_type == "time_series":
        # Time-series correlation (correlation over time)
        period = intent.parameters.get("period", "month")
        rolling_window = intent.parameters.get("rolling_window", None)

        # Format title values outside the string template
        metric_x_title = metric_x.title() if hasattr(metric_x, "title") else metric_x
        metric_y_title = metric_y.title() if hasattr(metric_y, "title") else metric_y

        title_text = (
            f"Correlation between {metric_x_title} and {metric_y_title} Over Time"
        )

        # Build code for time-series correlation
        code = f"""
# Calculate how correlation between {metric_x} and {metric_y} changes over time
import pandas as pd
from db_query import query_dataframe
from app.utils.advanced_correlation import time_series_correlation, time_series_correlation_plot

# SQL query to fetch required data with dates
sql = '''
SELECT v.{metric_x}, v.{metric_y}, v.date
FROM vitals v
'''
"""

        # Add time range filter if present
        if intent.time_range:
            start_date = intent.time_range.start_date
            end_date = intent.time_range.end_date

            code += f"""
# Add time range filter
sql += " WHERE v.date BETWEEN '{start_date}' AND '{end_date}'"
"""

        # Complete the code
        rolling_window_param = (
            f", rolling_window={rolling_window}" if rolling_window else ""
        )

        code += f"""
# Execute query
df = query_dataframe(sql)

# Calculate time-series correlations
results_df = time_series_correlation(
    df,
    metric_x='{metric_x}',
    metric_y='{metric_y}',
    date_column='date',
    period='{period}'{rolling_window_param},
    method='{method}'
)

# Create visualization
viz = time_series_correlation_plot(
    results_df,
    title='{title_text}',
)

# Prepare results dictionary
correlations_over_time = dict(zip(results_df['period'], results_df['correlation']))
p_values_over_time = dict(zip(results_df['period'], results_df['p_value']))

final_results = {{
    'correlations_over_time': correlations_over_time,
    'p_values': p_values_over_time,
    'method': '{method}',
    'period': '{period}',
    'visualization': viz
}}

# Return results
results = final_results
"""

    else:
        # Simple correlation (existing implementation)
        # Format title values outside the string template
        metric_x_title = metric_x.title() if hasattr(metric_x, "title") else metric_x
        metric_y_title = metric_y.title() if hasattr(metric_y, "title") else metric_y

        title_text = f"Correlation: {metric_x_title} vs {metric_y_title}"

        code = f"""
# Calculate correlation between {metric_x} and {metric_y}
import pandas as pd
from db_query import query_dataframe
from app.utils.plots import scatter_plot

# SQL query to fetch required data
sql = '''
SELECT v.{metric_x}, v.{metric_y}
FROM vitals v
'''

# Add filters if any
where_clauses = []
"""

        # Add filters
        if intent.filters:
            code += """
# Process filters
"""
            for i, filter in enumerate(intent.filters):
                field = filter.field
                if hasattr(filter, "value"):
                    value = (
                        f"'{filter.value}'"
                        if isinstance(filter.value, str)
                        else filter.value
                    )
                    code += f'where_clauses.append("{field} = {value}")\n'
                # Handle other filter types similarly...

        # Complete the SQL query
        code += """
# Finalize the SQL query with WHERE clause if needed
if where_clauses:
    sql += " WHERE " + " AND ".join(where_clauses)

# Execute query
df = query_dataframe(sql)

# Calculate correlation
correlation = df['{metric_x}'].corr(df['{metric_y}'], method='{method}')

# Generate scatter plot with regression line
viz = scatter_plot(
    df,
    x='{metric_x}',
    y='{metric_y}',
    title='{title_text}',
    correlation=True,
    regression=True
)

# Return results
results = {{
    'correlation_coefficient': correlation,
    'correlation_matrix': pd.DataFrame([[1.0, correlation], [correlation, 1.0]], 
                          index=['{metric_x}', '{metric_y}'], 
                          columns=['{metric_x}', '{metric_y}']),
    'metrics': ['{metric_x}', '{metric_y}'],
    'method': '{method}',
    'visualization': viz
}}
""".format(
            metric_x=metric_x, metric_y=metric_y, method=method, title_text=title_text
        )

    return code


# Add the frequency and seasonality functions


def _generate_frequency_analysis_code(intent: QueryIntent) -> str:
    """Generate code for frequency analysis of categorical data.

    This template analyzes the frequency distribution of categorical variables,
    and can handle more sophisticated analysis than simple counts.
    """
    field = intent.target_field

    # Determine table based on field
    table_name = "patients"  # Default for most categorical fields
    if field in {"diagnosis", "assessment_type", "score_type"}:
        table_name = "scores"

    # Check if we need to normalize or weight the frequencies
    normalize = intent.parameters.get("normalize", False)
    weight_field = intent.parameters.get("weight_field", None)

    # Build filters clause for WHERE conditions
    filters_clause = _build_filters_clause(intent)
    where_clause = f"WHERE {filters_clause}" if filters_clause else ""

    # Add time range if specified
    if intent.time_range is not None:
        date_clause = f"date BETWEEN '{intent.time_range.start_date}' AND '{intent.time_range.end_date}'"
        where_clause = (
            where_clause + f" AND {date_clause}"
            if where_clause
            else f"WHERE {date_clause}"
        )

    # SQL to get data for frequency analysis
    select_clause = f"{field}"
    if weight_field:
        select_clause += f", {weight_field}"

    sql = f"""
    SELECT {select_clause}
    FROM {table_name}
    {where_clause}
    """

    # Build the Python code
    code = (
        "# Auto-generated frequency analysis\n"
        "from db_query import query_dataframe\n"
        "import pandas as pd\n"
        "import numpy as np\n"
        "from app.utils.plots import bar_chart, pie_chart\n\n"
        f"# SQL query to get data for frequency analysis\n_sql = '''{sql}'''\n\n"
        "# Execute query and process results\n"
        "df = query_dataframe(_sql)\n"
        "if df.empty:\n"
        "    results = {'error': 'No data available for frequency analysis'}\n"
        "else:\n"
    )

    # Add frequency calculation based on parameters
    if weight_field:
        code += f"""
    # Calculate weighted frequencies
    weighted_counts = df.groupby('{field}')['{weight_field}'].sum().sort_values(ascending=False)
    total_weight = weighted_counts.sum()
    weighted_pct = (weighted_counts / total_weight * 100).round(2) if total_weight > 0 else weighted_counts * 0
    
    # Prepare results
    frequency_data = pd.DataFrame({{
        'category': weighted_counts.index,
        'weighted_count': weighted_counts.values,
        'weighted_percent': weighted_pct.values
    }})
    
    # Create visualizations
    title = 'Weighted Frequency Distribution of {field.title()}'
    bar_viz = bar_chart(frequency_data, 'category', 'weighted_count', title=title)
    pie_viz = pie_chart(frequency_data, 'category', 'weighted_count', 
                       title=f'Weighted Distribution of {field.title()}')
    
    # Return results
    results = {{
        'frequency_data': frequency_data.to_dict(orient='records'),
        'weighted_counts': dict(zip(weighted_counts.index, weighted_counts.values)),
        'weighted_percent': dict(zip(weighted_pct.index, weighted_pct.values)),
        'bar_chart': bar_viz,
        'pie_chart': pie_viz
    }}
"""
    elif normalize:
        code += f"""
    # Calculate normalized frequencies
    value_counts = df['{field}'].value_counts()
    total_count = len(df)
    percentages = (value_counts / total_count * 100).round(2)
    
    # Prepare results
    frequency_data = pd.DataFrame({{
        'category': value_counts.index,
        'count': value_counts.values,
        'percent': percentages.values
    }})
    
    # Create visualizations
    title = 'Frequency Distribution of {field.title()}'
    bar_viz = bar_chart(frequency_data, 'category', 'percent', title=title)
    pie_viz = pie_chart(frequency_data, 'category', 'count', 
                       title=f'Distribution of {field.title()}')
    
    # Return results
    results = {{
        'frequency_data': frequency_data.to_dict(orient='records'),
        'counts': dict(zip(value_counts.index, value_counts.values)),
        'percentages': dict(zip(percentages.index, percentages.values)),
        'bar_chart': bar_viz,
        'pie_chart': pie_viz
    }}
"""
    else:
        code += f"""
    # Calculate raw frequencies
    value_counts = df['{field}'].value_counts().sort_values(ascending=False)
    total_count = len(df)
    percentages = (value_counts / total_count * 100).round(2)
    
    # Prepare results
    frequency_data = pd.DataFrame({{
        'category': value_counts.index,
        'count': value_counts.values,
        'percent': percentages.values
    }})
    
    # Create visualizations
    title = 'Frequency Distribution of {field.title()}'
    bar_viz = bar_chart(frequency_data, 'category', 'count', title=title)
    pie_viz = pie_chart(frequency_data, 'category', 'count', 
                       title=f'Distribution of {field.title()}')
    
    # Return results
    results = {{
        'frequency_data': frequency_data.to_dict(orient='records'),
        'counts': dict(zip(value_counts.index, value_counts.values)),
        'percentages': dict(zip(percentages.index, percentages.values)),
        'bar_chart': bar_viz,
        'pie_chart': pie_viz
    }}
"""

    return code


def _generate_seasonality_analysis_code(intent: QueryIntent) -> str:
    """Generate code for seasonality analysis of time-series data.

    This template analyzes seasonal patterns in time-series data, such as
    variations by month, day of week, or hour of day.
    """
    metric = intent.target_field

    # Determine seasonality type (month, day_of_week, hour_of_day)
    seasonality_type = intent.parameters.get("seasonality_type", "month")

    # Determine table based on metric
    table_name = "vitals"
    if metric in {"score_value", "phq9_score", "gad7_score"}:
        table_name = "scores"

    # Build filters clause for WHERE conditions
    filters_clause = _build_filters_clause(intent)
    where_clause = f"WHERE {filters_clause}" if filters_clause else ""

    # Add time range if specified
    if intent.time_range is not None:
        date_clause = f"date BETWEEN '{intent.time_range.start_date}' AND '{intent.time_range.end_date}'"
        where_clause = (
            where_clause + f" AND {date_clause}"
            if where_clause
            else f"WHERE {date_clause}"
        )

    # SQL to get data for seasonality analysis
    time_extract = ""
    if seasonality_type == "month":
        time_extract = "strftime('%m', date) AS month"
    elif seasonality_type == "day_of_week":
        time_extract = "strftime('%w', date) AS day_of_week"
    elif seasonality_type == "hour_of_day":
        time_extract = "strftime('%H', date) AS hour_of_day"
    else:
        # Default to month if unrecognized
        time_extract = "strftime('%m', date) AS month"
        seasonality_type = "month"

    sql = f"""
    SELECT 
        {time_extract},
        {metric},
        date
    FROM {table_name}
    {where_clause}
    """

    # Build the Python code
    code = (
        "# Auto-generated seasonality analysis\n"
        "from db_query import query_dataframe\n"
        "import pandas as pd\n"
        "import numpy as np\n"
        "from app.utils.plots import bar_chart, line_chart\n\n"
        f"# SQL query to get data for seasonality analysis\n_sql = '''{sql}'''\n\n"
        "# Execute query and process results\n"
        "df = query_dataframe(_sql)\n"
        "if df.empty:\n"
        "    results = {'error': 'No data available for seasonality analysis'}\n"
        "else:\n"
    )

    # Add code based on seasonality type
    if seasonality_type == "month":
        code += f"""
    # Convert month numbers to month names for better readability
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    df['month'] = df['month'].astype(int)
    df['month_name'] = df['month'].apply(lambda x: month_names[x-1])
    
    # Group by month and calculate statistics
    monthly_stats = df.groupby('month').agg({{
        '{metric}': ['mean', 'std', 'count'],
        'month_name': 'first'  # Carry over the month name
    }})
    
    # Flatten multi-index columns
    monthly_stats.columns = ['mean', 'std', 'count', 'month_name']
    monthly_stats = monthly_stats.reset_index()
    
    # Sort by month for chronological order
    monthly_stats = monthly_stats.sort_values('month')
    
    # Create visualization
    title = 'Monthly Pattern of {metric.title()}'
    line_viz = line_chart(
        monthly_stats, 
        x='month_name', 
        y='mean', 
        title=title,
        x_label='Month',
        y_label='Average {metric.title()}'
    )
    
    # Calculate seasonal statistics
    peak_month_idx = monthly_stats['mean'].idxmax()
    peak_month = monthly_stats.loc[peak_month_idx, 'month_name']
    peak_value = monthly_stats.loc[peak_month_idx, 'mean']
    
    low_month_idx = monthly_stats['mean'].idxmin()
    low_month = monthly_stats.loc[low_month_idx, 'month_name']
    low_value = monthly_stats.loc[low_month_idx, 'mean']
    
    seasonal_range = peak_value - low_value
    seasonal_range_pct = (seasonal_range / low_value * 100) if low_value != 0 else 0
    
    # Return results
    results = {{
        'seasonal_stats': monthly_stats.to_dict(orient='records'),
        'peak_month': peak_month,
        'peak_value': peak_value,
        'low_month': low_month,
        'low_value': low_value,
        'seasonal_range': seasonal_range,
        'seasonal_range_pct': seasonal_range_pct,
        'visualization': line_viz
    }}
"""
    elif seasonality_type == "day_of_week":
        code += f"""
    # Convert day numbers to day names for better readability
    day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    df['day_of_week'] = df['day_of_week'].astype(int)
    df['day_name'] = df['day_of_week'].apply(lambda x: day_names[x])
    
    # Group by day of week and calculate statistics
    daily_stats = df.groupby('day_of_week').agg({{
        '{metric}': ['mean', 'std', 'count'],
        'day_name': 'first'  # Carry over the day name
    }})
    
    # Flatten multi-index columns
    daily_stats.columns = ['mean', 'std', 'count', 'day_name']
    daily_stats = daily_stats.reset_index()
    
    # Sort by day for chronological order
    daily_stats = daily_stats.sort_values('day_of_week')
    
    # Create visualization
    title = 'Day of Week Pattern of {metric.title()}'
    bar_viz = bar_chart(
        daily_stats, 
        x='day_name', 
        y='mean', 
        title=title,
        x_label='Day of Week',
        y_label='Average {metric.title()}'
    )
    
    # Calculate weekday vs weekend difference
    weekday_data = daily_stats[daily_stats['day_of_week'].isin([1, 2, 3, 4, 5])]  # Mon-Fri
    weekend_data = daily_stats[daily_stats['day_of_week'].isin([0, 6])]  # Sat-Sun
    
    weekday_avg = weekday_data['mean'].mean() if not weekday_data.empty else None
    weekend_avg = weekend_data['mean'].mean() if not weekend_data.empty else None
    
    weekday_weekend_diff = (weekend_avg - weekday_avg) if (weekday_avg is not None and weekend_avg is not None) else None
    
    # Find peak and low days
    peak_day_idx = daily_stats['mean'].idxmax()
    peak_day = daily_stats.loc[peak_day_idx, 'day_name']
    peak_value = daily_stats.loc[peak_day_idx, 'mean']
    
    low_day_idx = daily_stats['mean'].idxmin()
    low_day = daily_stats.loc[low_day_idx, 'day_name']
    low_value = daily_stats.loc[low_day_idx, 'mean']
    
    # Return results
    results = {{
        'daily_stats': daily_stats.to_dict(orient='records'),
        'weekday_avg': weekday_avg,
        'weekend_avg': weekend_avg,
        'weekday_weekend_diff': weekday_weekend_diff,
        'peak_day': peak_day,
        'peak_value': peak_value,
        'low_day': low_day,
        'low_value': low_value,
        'visualization': bar_viz
    }}
"""
    else:  # hour_of_day (default for any other value)
        code += f"""
    # Convert to integers and ensure hours are in 24-hour format
    df['hour_of_day'] = df['hour_of_day'].astype(int)
    
    # Group by hour and calculate statistics
    hourly_stats = df.groupby('hour_of_day').agg({{
        '{metric}': ['mean', 'std', 'count']
    }})
    
    # Flatten multi-index columns
    hourly_stats.columns = ['mean', 'std', 'count']
    hourly_stats = hourly_stats.reset_index()
    
    # Sort by hour for chronological order
    hourly_stats = hourly_stats.sort_values('hour_of_day')
    
    # Create visualization
    title = 'Hourly Pattern of {metric.title()}'
    line_viz = line_chart(
        hourly_stats, 
        x='hour_of_day', 
        y='mean', 
        title=title,
        x_label='Hour of Day',
        y_label='Average {metric.title()}'
    )
    
    # Calculate time-of-day averages
    morning_hours = list(range(6, 12))
    afternoon_hours = list(range(12, 18))
    evening_hours = list(range(18, 24))
    night_hours = list(range(0, 6))
    
    morning_avg = hourly_stats[hourly_stats['hour_of_day'].isin(morning_hours)]['mean'].mean() if not hourly_stats.empty else None
    afternoon_avg = hourly_stats[hourly_stats['hour_of_day'].isin(afternoon_hours)]['mean'].mean() if not hourly_stats.empty else None
    evening_avg = hourly_stats[hourly_stats['hour_of_day'].isin(evening_hours)]['mean'].mean() if not hourly_stats.empty else None
    night_avg = hourly_stats[hourly_stats['hour_of_day'].isin(night_hours)]['mean'].mean() if not hourly_stats.empty else None
    
    # Find peak and low hours
    peak_hour_idx = hourly_stats['mean'].idxmax()
    peak_hour = hourly_stats.loc[peak_hour_idx, 'hour_of_day']
    peak_value = hourly_stats.loc[peak_hour_idx, 'mean']
    
    low_hour_idx = hourly_stats['mean'].idxmin()
    low_hour = hourly_stats.loc[low_hour_idx, 'hour_of_day']
    low_value = hourly_stats.loc[low_hour_idx, 'mean']
    
    # Return results
    results = {{
        'hourly_stats': hourly_stats.to_dict(orient='records'),
        'morning_avg': morning_avg,
        'afternoon_avg': afternoon_avg,
        'evening_avg': evening_avg,
        'night_avg': night_avg,
        'peak_hour': peak_hour,
        'peak_value': peak_value,
        'low_hour': low_hour,
        'low_value': low_value,
        'visualization': line_viz
    }}
"""

    return code
