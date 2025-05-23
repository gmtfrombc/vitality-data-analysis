"""
Analysis Engine for Data Analysis Assistant

This module handles the core pipeline for transforming natural language queries into
executable code and analyzing results. It separates the query processing, code generation,
and execution logic from the UI components.

Example:
    >>> from app.engine import AnalysisEngine
    >>> engine = AnalysisEngine()
    >>> intent = engine.process_query("average BMI of active patients")
    >>> code = engine.generate_code()
    >>> results = engine.execute_analysis()
"""

import logging
import time
import re
from pathlib import Path
from app.utils.assumptions import CLARIFICATION_CONFIDENCE_THRESHOLD
from app.utils.schema import get_data_schema
from app.utils.sandbox import run_snippet
from app.utils.query_intent import QueryIntent, compute_intent_confidence
from app.utils.assumptions import (
    resolve_gender_filter,
    resolve_time_window,
    resolve_patient_status,
    resolve_metric_source,
    get_default_aggregator,
)
from app.utils.ai_helper import AIHelper

ai = AIHelper()


# Configure logging
logger = logging.getLogger("data_assistant.engine")


class AnalysisEngine:
    """
    Core engine for processing natural language queries into analysis results

    This class handles the entire pipeline from query processing to result generation,
    including:

    - Intent parsing from natural language queries
    - Clarification of ambiguous queries
    - Code generation based on query intent
    - Safe execution of generated code in a sandbox environment
    - Result extraction and visualization generation
    - Data sample generation for context

    Example:
        >>> engine = AnalysisEngine()
        >>> intent = engine.process_query("average BMI of active patients")
        >>> code = engine.generate_code()
        >>> results = engine.execute_analysis()
    """

    def __init__(self):
        """
        Initialize the analysis engine

        Sets up the initial state of the engine with empty/null values for
        all analysis artifacts that will be populated during processing.
        """
        self.query = ""  # The original natural language query
        self.intent = None  # Parsed intent from the query
        self.generated_code = ""  # Python code generated for analysis
        self.execution_results = None  # Results from code execution
        self.visualizations = []  # Visualizations generated from results
        self.start_time = None  # Timestamp when processing started
        self.end_time = None  # Timestamp when processing finished
        self.threshold_info = None  # Information about threshold queries
        self.parameters = {}  # Additional parameters for query handling

    def process_query(self, query):
        """
        Entry point - process a natural language query

        This is the main entry point for the analysis process. It resets
        the engine state and starts the analysis pipeline with the new query.

        Args:
            query (str): The natural language query to process

        Returns:
            QueryIntent: The parsed intent from the query
        """
        self.start_time = time.perf_counter()
        self.query = query
        self.intent = None
        self.generated_code = ""
        self.execution_results = None
        self.visualizations = []
        self.threshold_info = None
        self.parameters = {}

        # Check for threshold queries
        self.threshold_info = self.detect_threshold_query(query)

        # Check for active/inactive patient filters
        self.detect_active_inactive_filter(query)

        # Gender filter (using assumptions module)
        gender = resolve_gender_filter(query)
        self.parameters["gender"] = gender

        # Time window resolution (use helper for default/fallback)
        self.parameters["window"] = resolve_time_window(self.parameters)

        # Patient status (active/all) using resolve_patient_status
        patient_status = resolve_patient_status(query)
        self.parameters["patient_status"] = patient_status

        # Metric instance (e.g., most recent or earliest) using resolve_metric_source
        self.parameters["metric_instance"] = resolve_metric_source(query)

        # Aggregator (average/min/max) using get_default_aggregator
        self.parameters["aggregator"] = get_default_aggregator(query)

        # Parse the query intent (step 1)
        return self.get_query_intent()

    def detect_threshold_query(self, query_text):
        """
        Detect if a query is asking for a threshold comparison
        (e.g., "BMI above 30", "patients with weight below 150")

        Args:
            query_text (str): The query text to analyze

        Returns:
            dict: Threshold information if detected, None otherwise
            {
                'direction': 'above'|'below',
                'value': float,
                'field': str  # The field being compared (if detectable)
            }
        """
        query = query_text.lower()
        threshold_info = {"direction": None, "value": None, "field": None}

        # Check for threshold direction words
        if any(
            word in query for word in ["above", "over", "greater than", "higher than"]
        ):
            threshold_info["direction"] = "above"
        elif any(
            word in query for word in ["below", "under", "less than", "lower than"]
        ):
            threshold_info["direction"] = "below"
        else:
            return None  # Not a threshold query

        # Extract numeric value from query
        numbers = re.findall(r"\d+(?:\.\d+)?", query)
        if not numbers:
            return None  # No threshold value found

        threshold_info["value"] = float(numbers[0])

        # Try to determine field being compared
        common_fields = {
            "bmi": ["bmi", "body mass index"],
            "weight": ["weight", "pounds", "lbs", "kg"],
            "sbp": ["sbp", "systolic", "systolic blood pressure"],
            "dbp": ["dbp", "diastolic", "diastolic blood pressure"],
            "a1c": ["a1c", "hba1c", "glycated hemoglobin"],
        }

        for field, terms in common_fields.items():
            if any(term in query for term in terms):
                threshold_info["field"] = field
                break

        return threshold_info

    def detect_active_inactive_filter(self, query_text):
        """
        Detect if a query explicitly mentions active or inactive patients

        Args:
            query_text (str): The query text to analyze

        Returns:
            bool: True if active/inactive filter is explicitly mentioned
        """

        query = query_text.lower()

        # Detect explicit mentions of all patients or inactive patients
        if "all patients" in query or "inactive" in query:
            logger.info(
                "Detected explicit request for all patients (including inactive)"
            )
            self.parameters["include_inactive"] = True
            return True

        # Detect explicit mentions of active patients
        if "active" in query and "inactive" not in query:
            logger.info("Detected explicit request for only active patients")
            self.parameters["include_inactive"] = False
            return True

        # If not explicitly mentioned, we'll need to clarify with the user
        return False

    def get_query_intent(self):
        """
        Get the intent of the query using AI

        Processes the natural language query to extract a structured intent
        that includes the analysis type, target fields, filters, and parameters.
        Uses the AI helper module to generate the intent.

        Returns:
            QueryIntent: A structured representation of the query intent

        Raises:
            Exception: If there is an error during intent parsing
        """

        logger.info(f"Getting intent for query: {self.query}")
        try:
            self.intent = ai.get_query_intent(self.query)

            # Store the original query in the intent for reference
            if isinstance(self.intent, QueryIntent):
                self.intent.raw_query = self.query

                # Gender filter: override/add to intent using resolve_gender_filter
                gender = self.parameters.get(
                    "gender", resolve_gender_filter(self.query)
                )
                if hasattr(self.intent, "filters"):
                    # Remove any existing gender filter
                    self.intent.filters = [
                        f
                        for f in self.intent.filters
                        if getattr(f, "field", None) != "gender"
                    ]
                    if gender != "all":
                        try:
                            from app.utils.query_intent import Filter

                            self.intent.filters.append(
                                Filter(field="gender", value=gender)
                            )
                        except Exception as e:
                            logger.error(f"Could not add gender filter: {e}")

                # Time window: ensure intent.parameters has the resolved time window
                if not hasattr(self.intent, "parameters") or not isinstance(
                    self.intent.parameters, dict
                ):
                    self.intent.parameters = {}
                # Always use the helper to resolve the time window
                self.intent.parameters["window"] = resolve_time_window(self.parameters)

                # Patient status filter: control active/all logic
                patient_status = self.parameters.get("patient_status", "active")
                if hasattr(self.intent, "filters"):
                    # Remove any existing 'active' filter
                    self.intent.filters = [
                        f
                        for f in self.intent.filters
                        if getattr(f, "field", None) != "active"
                    ]
                    if patient_status == "active":
                        try:
                            from app.utils.query_intent import Filter

                            self.intent.filters.append(Filter(field="active", value=1))
                        except Exception as e:
                            logger.error(f"Could not add active filter: {e}")
                    # If 'all', do NOT add any filter for active/inactive

                # Metric instance: ensure intent.parameters has the resolved metric instance
                self.intent.parameters["metric_instance"] = self.parameters[
                    "metric_instance"
                ]

                # Aggregator: ensure intent.parameters has the resolved aggregator
                self.intent.parameters["aggregator"] = self.parameters["aggregator"]

            # Calculate confidence if possible
            if isinstance(self.intent, QueryIntent):
                confidence = compute_intent_confidence(self.intent, self.query)
                if isinstance(self.intent.parameters, dict):
                    self.intent.parameters["confidence"] = confidence
                else:
                    self.intent.parameters = {"confidence": confidence}

            return self.intent
        except Exception as e:
            logger.error(f"Error getting query intent: {e}", exc_info=True)
            return {"analysis_type": "unknown", "error": str(e)}

    def is_low_confidence_intent(self, intent):
        """
        Check if the intent has low confidence and needs clarification

        Evaluates the parsed intent to determine if it is ambiguous or has
        low confidence, indicating that clarification questions should be asked.

        Args:
            intent (QueryIntent or dict): The intent to evaluate

        Returns:
            bool: True if the intent needs clarification, False otherwise
        """
        # In dict form = intent parsing failed
        if isinstance(intent, dict):
            return True

        if not isinstance(intent, QueryIntent):
            return True

        # Check for unknown analysis type or target field
        if intent.analysis_type == "unknown" or intent.target_field == "unknown":
            return True

        # Check confidence score if available
        if hasattr(intent, "parameters") and isinstance(intent.parameters, dict):
            confidence = intent.parameters.get("confidence", 1.0)
        """
        Clarification confidence threshold is set in assumptions.py (CLARIFICATION_CONFIDENCE_THRESHOLD).
        """
        if confidence < CLARIFICATION_CONFIDENCE_THRESHOLD:  # See assumptions.py
            return True

        return False

    def generate_clarifying_questions(self):
        """
        Generate clarifying questions based on the query

        Creates questions to ask the user when the query is ambiguous or
        missing essential information. Uses the AI helper module to generate
        appropriate questions based on the current query and intent.

        Returns:
            list: A list of clarifying questions to ask the user
        """
        try:
            return ai.generate_clarifying_questions(self.query)
        except Exception as e:
            logger.error(f"Error generating clarifying questions: {e}", exc_info=True)
            return [
                "Could you rephrase your question?",
                "What specific aspect of the data are you interested in?",
                "Which patient group should the analysis focus on?",
                "What time period are you interested in?",
            ]

    def process_clarification(self, clarification_text):
        """
        Process the clarification response from the user

        Takes the user's response to clarifying questions and uses it to
        refine the original query, then re-processes the intent with this
        additional context.

        Args:
            clarification_text (str): The user's response to clarifying questions

        Returns:
            QueryIntent: The updated query intent with clarification incorporated
        """
        # Check if clarification contains active/inactive preference
        clarification_lower = clarification_text.lower()
        if "all patient" in clarification_lower or "inactive" in clarification_lower:
            # User wants all patients (both active and inactive)
            self.parameters["include_inactive"] = True
            logger.info("Clarification indicates ALL patients (including inactive)")
        elif "active" in clarification_lower and "only" in clarification_lower:
            # User explicitly specified only active patients
            self.parameters["include_inactive"] = False
            logger.info("Clarification indicates ONLY active patients")

        # Combine original query with clarification
        combined_query = f"{self.query}\n\nAdditional info: {clarification_text}"
        logger.info(f"Processing clarified query: {combined_query}")

        # Re-process with the clarified query
        self.query = combined_query
        return self.get_query_intent()

    def generate_analysis_code(self):
        """
        Generate analysis code based on the intent

        Creates executable Python code that will analyze the data according to
        the parsed query intent. Uses the AI helper to generate appropriate
        code based on the intent and database schema.

        Returns:
            str: The generated Python code for data analysis

        Raises:
            ValueError: If there is no query intent available
        """
        if not self.intent:
            raise ValueError("Query intent not available. Process a query first.")

        logger.info(f"Generating analysis code for intent: {self.intent}")

        # Apply active/inactive filter preference from parameters if available
        if isinstance(self.intent, QueryIntent):
            include_inactive = self.parameters.get("include_inactive", None)
            if include_inactive is not None:
                # Add or modify the active filter in the intent based on user's clarification
                if not include_inactive:
                    # Add explicit active=1 filter if user wants only active patients
                    has_active_filter = False
                    for filter in self.intent.filters:
                        if filter.field == "active":
                            has_active_filter = True
                            filter.value = 1
                            break

                    if not has_active_filter:
                        try:
                            # Add active=1 filter
                            from app.utils.query_intent import Filter

                            self.intent.filters.append(Filter(field="active", value=1))
                            logger.info("Added active=1 filter based on clarification")
                        except Exception as e:
                            logger.error(f"Could not add active filter: {e}")
                else:
                    # If user wants all patients, remove any active filter
                    self.intent.filters = [
                        f for f in self.intent.filters if f.field != "active"
                    ]
                    logger.info("Removed active filter based on clarification")

        # Check for threshold query patterns
        custom_prompt = None
        if (
            self.threshold_info
            and self.threshold_info["field"]
            and self.threshold_info["value"]
        ):
            # Store threshold info in context for result formatting later
            custom_prompt = f"Generate code to find patients with {self.threshold_info['field']} {self.threshold_info['direction']} {self.threshold_info['value']}"
            logger.info(f"Using threshold-specific prompt: {custom_prompt}")

        # Get data schema for code generation
        data_schema = get_data_schema()

        # Handle non-QueryIntent responses (dictionaries)
        if isinstance(self.intent, dict):
            # Fallback to simple code that returns the error
            self.generated_code = self.generate_fallback_code()
            return self.generated_code

        # Generate code from AI based on intent
        try:
            self.generated_code = ai.generate_analysis_code(
                self.intent, data_schema, custom_prompt=custom_prompt
            )

            # If this is a threshold query, ensure the code includes proper visualization
            if self.threshold_info:
                self.generated_code = self._enhance_threshold_visualization(
                    self.generated_code
                )

            return self.generated_code
        except Exception as e:
            logger.error(f"Error generating analysis code: {e}", exc_info=True)
            self.generated_code = self.generate_fallback_code()
            return self.generated_code

    def _enhance_threshold_visualization(self, code):
        """
        Enhance code with threshold visualization if needed

        If the query involves a threshold (e.g., "BMI above 30"), add code to
        create a visualization that includes a vertical line at the threshold.

        Args:
            code (str): The generated code

        Returns:
            str: Enhanced code with threshold visualization
        """
        if not self.threshold_info:
            return code

        # Check if the code already includes visualization
        if "histogram(" in code or "hvplot.hist" in code:
            # The code already has visualization, likely handled by AI
            return code

        # Get details from threshold info
        field = self.threshold_info["field"]
        direction = self.threshold_info["direction"]
        value = self.threshold_info["value"]

        # Add visualization code - safely with try/except
        viz_code = f"""
# Ensure results is a dictionary for threshold metadata
if not isinstance(results, dict):
    # Wrap scalar result in a dictionary
    original_value = results
    results = {{'scalar': original_value}}

# Add threshold visualization
try:
    # Try to create threshold visualization
    results['threshold_info'] = {self.threshold_info}
    
    import numpy as np
    import pandas as pd
    
    # Find the data to visualize
    data_to_viz = None
    for var_name in dir():
        var = locals()[var_name]
        if isinstance(var, pd.DataFrame) and '{field}' in var.columns:
            data_to_viz = var
            break
    
    # If we found data with the threshold field, create visualization
    if data_to_viz is not None:
        # Create histogram data
        hist_data, bin_edges = np.histogram(data_to_viz['{field}'].dropna(), bins=20)
        results['hist_data'] = hist_data.tolist()
        results['bin_edges'] = bin_edges.tolist()
        results['threshold_value'] = {value}
        results['threshold_direction'] = '{direction}'
        
        # Calculate stats
        matching_condition = data_to_viz['{field}'] {'>' if direction == 'above' else '<'} {value}
        results['matching_count'] = matching_condition.sum()
        results['total_count'] = len(data_to_viz)
        results['percentage'] = (results['matching_count'] / results['total_count']) * 100 if results['total_count'] > 0 else 0
except Exception as viz_error:
    # If visualization fails, continue without it
    results['viz_error'] = str(viz_error)
"""

        # Insert visualization code before the final return or at the end
        if "return results" in code:
            # Insert before return
            return code.replace("return results", viz_code + "\nreturn results")
        else:
            # Append to end
            return code + "\n" + viz_code

    def add_sandbox_safety(self, code):
        """
        Add safety boundaries to the code for sandbox execution

        Wraps the generated code with safeguards like timeouts, exception handling,
        and result validation to ensure it runs safely in the sandbox environment.

        Args:
            code (str): The raw generated code

        Returns:
            str: The code with safety wrappers added
        """
        # Ensure results variable is defined
        if "results =" not in code and "results=" not in code:
            code += "\n\nresults = None"

        # Add timeout handling
        safe_code = (
            "import signal\n"
            "import time\n\n"
            "class TimeoutException(Exception):\n"
            "    pass\n\n"
            "def timeout_handler(signum, frame):\n"
            "    raise TimeoutException('Execution timed out')\n\n"
            "# Set timeout to 30 seconds\n"
            "signal.signal(signal.SIGALRM, timeout_handler)\n"
            "signal.alarm(30)\n\n"
            "start_time = time.time()\n\n"
            "try:\n"
        )

        # Indent the original code
        indented_code = "\n".join(f"    {line}" for line in code.split("\n"))
        safe_code += indented_code

        # Add exception handling
        safe_code += (
            "\n\nexcept TimeoutException:\n"
            "    results = {'error': 'Execution timed out (30 seconds)'}\n"
            "except Exception as e:\n"
            "    import traceback\n"
            "    results = {'error': str(e), 'traceback': traceback.format_exc()}\n"
            "finally:\n"
            "    # Cancel the alarm\n"
            "    signal.alarm(0)\n"
            "    execution_time = time.time() - start_time\n"
            "    if 'results' not in locals() or results is None:\n"
            "        results = {'error': 'No results were generated'}\n"
            "    if isinstance(results, dict) and 'execution_time' not in results:\n"
            "        results['execution_time'] = execution_time\n"
        )

        return safe_code

    def execute_analysis(self):
        """
        Execute the generated code in a sandbox environment

        Runs the generated Python code in a sandboxed environment, captures
        the results, and extracts any visualizations that were created during
        execution.

        Returns:
            Any: The results from executing the code

        Raises:
            ValueError: If no code has been generated yet
        """
        if not self.generated_code:
            raise ValueError("No code has been generated. Generate code first.")

        # Add safety wrappers to the code
        safe_code = self.add_sandbox_safety(self.generated_code)

        # Create a temporary file for the code
        # This helps with debugging by preserving the exact code that was executed
        with Path("last_executed_code.py").open("w") as f:
            f.write(safe_code)

        logger.info("Executing analysis code in sandbox")

        try:
            # TEMP: Debugging aid – dump code before execution
            print("\n====== BEGIN EXECUTED CODE ======\n")
            print(safe_code)
            print("\n======= END EXECUTED CODE =======\n")
            # Execute the code in the sandbox
            result = run_snippet(safe_code)

            # If the result is a dictionary, add any active/inactive preference from the engine
            if isinstance(result, dict) and "include_inactive" not in result:
                include_inactive = self.parameters.get("include_inactive", None)
                if include_inactive is not None:
                    result["include_inactive"] = include_inactive

            self.execution_results = result

            # Extract visualizations if any
            self.extract_visualizations()

            return result
        except Exception as e:
            logger.error(f"Error executing analysis: {e}", exc_info=True)
            error_result = {"error": str(e)}
            self.execution_results = error_result
            return error_result

    def extract_visualizations(self):
        """Extract visualizations from execution results if present"""
        self.visualizations = []

        # Check if results contain visualizations
        if isinstance(self.execution_results, dict):
            # Direct visualization
            if "visualization" in self.execution_results:
                viz = self.execution_results["visualization"]
                if viz is not None:
                    self.visualizations.append(viz)

            # Multiple visualizations in a list
            if "visualizations" in self.execution_results:
                vizs = self.execution_results["visualizations"]
                if isinstance(vizs, list):
                    self.visualizations.extend([v for v in vizs if v is not None])

        return self.visualizations

    def interpret_results(self):
        """Generate a human-readable interpretation of the results"""
        if not self.execution_results:
            from app.utils.assumptions import NO_DATA_MESSAGE

            return NO_DATA_MESSAGE

        try:
            # Gather active/inactive status information for AI interpretation
            patient_status_info = {}
            include_inactive = self.parameters.get("include_inactive", None)
            if include_inactive is not None:
                patient_status_info["include_inactive"] = include_inactive

            # Add this context to the results dictionary if it's a dictionary
            results_for_ai = self.execution_results
            if isinstance(results_for_ai, dict):
                # Add active/inactive status if not already in the results
                if (
                    "include_inactive" not in results_for_ai
                    and include_inactive is not None
                ):
                    # Make a copy to avoid modifying original
                    results_for_ai = results_for_ai.copy()
                    results_for_ai["include_inactive"] = include_inactive
            else:
                # Wrap scalar results with active/inactive information
                if include_inactive is not None:
                    results_for_ai = {
                        "scalar": self.execution_results,
                        "include_inactive": include_inactive,
                    }

            # Use AI to interpret the results
            interpretation = ai.interpret_results(
                self.query, results_for_ai, self.visualizations
            )

            # Add patient status to interpretation if not already mentioned
            if include_inactive is not None and interpretation:
                patient_status_text = ""
                if not include_inactive and "active" not in interpretation.lower():
                    patient_status_text = " for active patients"
                elif (
                    include_inactive
                    and "all patient" not in interpretation.lower()
                    and "inactive" not in interpretation.lower()
                ):
                    patient_status_text = " for all patients (including inactive)"

                if patient_status_text:
                    # Add the status info at the end of the first sentence
                    if "." in interpretation:
                        first_sentence, rest = interpretation.split(".", 1)
                        interpretation = (
                            first_sentence + patient_status_text + "." + rest
                        )
                    else:
                        interpretation += patient_status_text

            return interpretation
        except Exception as e:
            logger.error(f"Error interpreting results: {e}", exc_info=True)

            # Fallback interpretation based on result type
            if (
                isinstance(self.execution_results, dict)
                and "error" in self.execution_results
            ):
                return f"The analysis encountered an error: {self.execution_results['error']}"

            if isinstance(self.execution_results, (int, float)):
                # Include active/inactive status in the fallback message if available
                patient_status_text = ""
                include_inactive = self.parameters.get("include_inactive", None)
                if include_inactive is not None:
                    if not include_inactive:
                        patient_status_text = " for active patients"
                    else:
                        patient_status_text = " for all patients (including inactive)"

                return f"The analysis resulted in a value of {self.execution_results}{patient_status_text}."

            return "Analysis complete. Results are displayed below."

    def generate_fallback_code(self):
        """Generate fallback code when intent parsing or code generation fails"""
        # Create safe fallback code that shows database schema and common tables
        fallback_code = f"""
# Fallback analysis for query: "{self.query}"
import pandas as pd
import numpy as np
import sqlite3

def fallback_analysis():
    # Connect to database and get basic information
    conn = sqlite3.connect('patient_data.db')
    
    # Check what tables are available
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
    
    # Get sample data from main tables
    samples = {{}}
    
    try:
        samples['patients'] = pd.read_sql("SELECT * FROM patients LIMIT 5", conn)
    except:
        samples['patients'] = "Not available"
        
    try:
        samples['vitals'] = pd.read_sql("SELECT * FROM vitals LIMIT 5", conn)
    except:
        samples['vitals'] = "Not available"
        
    try:
        samples['scores'] = pd.read_sql("SELECT * FROM scores LIMIT 5", conn)
    except:
        samples['scores'] = "Not available"
    
    result = {{
        'message': 'Could not generate specific analysis for your query.',
        'available_tables': tables['name'].tolist(),
        'samples': samples
    }}
    
    conn.close()
    return result

# Call the fallback analysis
results = fallback_analysis()
"""
        return fallback_code

    def generate_data_samples(self):
        """Generate data samples relevant to the query intent"""
        samples = {}

        try:
            import app.db_query as db_query

            # Get a few patient records
            patients = db_query.get_all_patients()
            if not patients.empty:
                samples["patients"] = patients.head(5)

            # Get vital signs if query mentions them
            if self.query and any(
                term in self.query.lower()
                for term in ["bmi", "weight", "blood pressure", "vitals"]
            ):
                vitals = db_query.get_all_vitals()
                if not vitals.empty:
                    samples["vitals"] = vitals.head(5)

                    # Calculate BMI stats if BMI is mentioned
                    if "bmi" in self.query.lower():
                        bmi_stats = vitals["bmi"].describe()
                        samples["bmi_stats"] = bmi_stats

            # Get active patients if mentioned
            if "active" in self.query.lower():
                active = db_query.get_active_patients()
                if not active.empty:
                    samples["active_patients"] = active.head(5)
                    samples["active_count"] = len(active)

        except Exception as e:
            logger.error(f"Error generating data samples: {e}", exc_info=True)
            samples["error"] = str(e)

        return samples
