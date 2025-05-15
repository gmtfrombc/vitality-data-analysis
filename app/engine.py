"""
Analysis Engine for Data Analysis Assistant

This module handles the core pipeline for transforming natural language queries into
executable code and analyzing results. It separates the query processing, code generation,
and execution logic from the UI components.

The engine is responsible for:
1. Processing natural language queries into structured intents
2. Generating executable Python code based on query intents
3. Safely executing analysis code in a sandbox environment
4. Extracting and processing analysis results
5. Generating visualizations and explanations
"""

import logging
import time
from pathlib import Path

from app.ai_helper import ai, get_data_schema
from app.utils.sandbox import run_snippet
from app.utils.query_intent import QueryIntent, compute_intent_confidence

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

    The engine maintains the state of the current analysis process and provides
    methods to execute each step of the pipeline independently.
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

        # Parse the query intent (step 1)
        return self.get_query_intent()

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

            # Calculate confidence if possible
            if isinstance(self.intent, QueryIntent):
                confidence = compute_intent_confidence(self.intent)
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
            if confidence < 0.7:  # Arbitrary threshold
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

        # Get data schema for code generation
        data_schema = get_data_schema()

        # Handle non-QueryIntent responses (dictionaries)
        if isinstance(self.intent, dict):
            # Fallback to simple code that returns the error
            analysis_type = self.intent.get("analysis_type", "unknown")
            error_msg = self.intent.get("error", "Unknown error")

            self.generated_code = self.generate_fallback_code()
            return self.generated_code

        # Generate code from AI based on intent
        try:
            self.generated_code = ai.generate_analysis_code(self.intent, data_schema)
            return self.generated_code
        except Exception as e:
            logger.error(f"Error generating analysis code: {e}", exc_info=True)
            self.generated_code = self.generate_fallback_code()
            return self.generated_code

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
            # Execute the code in the sandbox
            result = run_snippet(safe_code)
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
            return "No results available to interpret."

        try:
            # Use AI to interpret the results
            interpretation = ai.interpret_results(
                self.query, self.execution_results, self.visualizations
            )
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
                return f"The analysis resulted in a value of {self.execution_results}."

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
