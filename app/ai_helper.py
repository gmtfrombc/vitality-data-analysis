import os
from openai import OpenAI
import logging
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ai_helper')

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
        You are an expert medical data analyst. Analyze the user's query about patient data to determine:
        1. What type of analysis is being requested (counting, statistics, comparison, trend, threshold, etc.)
        2. What data fields are relevant (BMI, weight, blood pressure, age, gender, etc.)
        3. What filters should be applied (gender, age range, activity status, etc.)
        4. What thresholds or conditions apply (above/below a value, top N, etc.)
        
        Return your analysis as a structured JSON object with these fields:
        - analysis_type: The primary type of analysis (count, average, distribution, comparison, etc.)
        - target_field: The main data field to analyze
        - filters: List of filters to apply
        - conditions: Any thresholds or conditions
        - parameters: Any additional parameters needed
        
        For example, the query "How many female patients have a BMI over 30?" would return:
        {
          "analysis_type": "count",
          "target_field": "bmi",
          "filters": [{"field": "gender", "value": "F"}],
          "conditions": [{"field": "bmi", "operator": ">", "value": 30}],
          "parameters": {}
        }
        """

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

            # Extract and parse the response
            intent_json = response.choices[0].message.content

            # Clean the response in case it has markdown code blocks
            if "```json" in intent_json:
                intent_json = intent_json.split(
                    "```json")[1].split("```")[0].strip()
            elif "```" in intent_json:
                intent_json = intent_json.split(
                    "```")[1].split("```")[0].strip()

            intent = json.loads(intent_json)
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

        # Prepare the system prompt with information about available data
        system_prompt = f"""
        You are an expert Python developer specializing in data analysis. Generate executable Python code to analyze patient data based on the specified intent. 
        
        The available data schema is:
        {data_schema}
        
        The code should use pandas and should be clean, efficient, and well-commented. Return only the Python code, no explanations or markdown.
        
        Include proper error handling and make sure to handle edge cases like empty dataframes and missing values.
        """

        try:
            # Call OpenAI API for code generation
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",
                        "content": f"Generate Python code for this analysis intent: {json.dumps(intent)}"}
                ],
                temperature=0.2,  # Lower temperature for more deterministic code
                max_tokens=1000
            )

            # Extract the code from the response
            code = response.choices[0].message.content

            # Clean the response if it contains markdown code blocks
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()

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


# Create the single instance to be imported by other modules
ai = AIHelper()
