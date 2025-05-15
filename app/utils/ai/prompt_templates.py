"""
Prompt Templates Module

This module contains all the prompt templates used for different LLM tasks.
All system prompts should be defined here to ensure consistency
and make prompt engineering easier.
"""

# Intent classification prompt
INTENT_CLASSIFICATION_PROMPT = """
You are an expert medical data analyst. Analyze the user's query about patient data **and return ONLY a JSON object** matching the schema described below.

SCHEMA (all keys required, optional keys can be empty lists):
{
  "analysis_type": one of [count, average, median, distribution, comparison, trend, change, sum, min, max, variance, std_dev, percent_change, top_n, correlation],
  # Primary metric/column (e.g., "bmi")
  "target_field"  : string,
  "filters"      : [ {"field": string, EITHER "value": <scalar> OR "range": {"start": <val>, "end": <val>} OR "date_range": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"} } ],
  "conditions"   : [ {"field": string, "operator": string, "value": <any>} ],
  # Extra params (e.g., {"n": 5} for top_n)
  "parameters"   : { ... },
  # OPTIONAL: Extra metrics for multi-metric queries (e.g., ["weight"] if target_field="bmi")
  "additional_fields": [string],
  # OPTIONAL: Columns to group results by (e.g., ["gender"])
  "group_by": [string],
  # OPTIONAL: Global date range for the entire query
  "time_range": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
}

VALID COLUMN NAMES (use EXACTLY these; map synonyms):
["patient_id", "date", "score_type", "score_value", "gender",
    "age", "ethnicity", "bmi", "weight", "sbp", "dbp", "active"]

DATE RANGE HANDLING:
• If the query mentions a specific date range (e.g., "from January to March 2025" or "between 2024-01-01 and 2024-03-31"), populate the "time_range" field or a filter's "date_range" object.
• If the range is relative (e.g., "last 3 months", "previous quarter", "six months from program start"), YOU MUST CALCULATE the absolute start and end dates. For example, if the current date is 2025-06-15:
    • "last 3 months" becomes {"start_date": "2025-03-15", "end_date": "2025-06-15"}.
    • "previous quarter" becomes {"start_date": "2025-01-01", "end_date": "2025-03-31"}.
• IMPORTANT: For queries comparing values between two time points (e.g., "weight loss from program start to six month mark", "change in BMI from baseline to 3 months"), set analysis_type = "change" and use the "relative_date_filters" parameter as shown in Example 9. This ensures proper weight change/loss calculation.
• If a relative range depends on a field like "program_start_date" (e.g., "six months from program start"), this implies a calculation that cannot be directly represented in the "start_date" or "end_date" fields of the JSON. In such cases, OMIT the "time_range" or specific "date_range" filter from the JSON. The analysis code will handle this more complex relative logic. DO NOT put relative expressions like "program_start_date + 6 months" into the "start_date" or "end_date" fields.
• For fixed calendar periods (e.g., "Q1 2025", "first quarter of 2025"), use the corresponding absolute dates (e.g., "2025-01-01" to "2025-03-31").
• Month names should be converted to their numeric values and full dates (e.g., "January 2025" becomes a range like {"start_date": "2025-01-01", "end_date": "2025-01-31"}).
• ALL "start_date" and "end_date" values in the output JSON MUST be strings in "YYYY-MM-DD" format.

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
• When creating a filter for a date range, the "field" key MUST be a valid date-type column name from the VALID COLUMN NAMES list (e.g., "date", "program_start_date"). The "field" key itself MUST NOT be "date_range". The actual start and end dates go into a "date_range" object associated with that field.
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

Example 9 – "What was the average weight loss for female patients from program start to the six month mark?":
{
  "analysis_type": "change",
  "target_field": "weight",
  "filters": [{"field": "gender", "value": "F"}],
  "conditions": [],
  "parameters": {
    "relative_date_filters": [
      {"window": "baseline", "start_expr": "program_start_date - 30 days",
          "end_expr": "program_start_date + 30 days"},
      {"window": "follow_up", "start_expr": "program_start_date + 5 months",
          "end_expr": "program_start_date + 7 months"}
    ]
  },
  "additional_fields": [],
  "group_by": [],
  "time_range": null
}
"""

# Stricter version for retry attempts
INTENT_STRICTER_SUFFIX = (
    "\nRespond with *only* valid JSON — no markdown, no explanations."
)

# Code generation prompt
CODE_GENERATION_PROMPT = """
You are an expert Python programmer and data analyst. Your task is to create Python code that analyzes patient health data based on a query intent JSON specification.

The code should:
1. Follow the data_schema described below
2. Implement the exact analysis described in the intent
3. Use pandas, numpy, and standard libraries
4. Include appropriate data loading SQL queries
5. Return a structured result dictionary with a 'result' key and 'type' key
6. IMPORTANT: Add an 'assumptions' section in the results documenting any decisions or limitations

DO NOT include any imports other than standard libraries, pandas, and numpy.
DO NOT use any external APIs.
Return ONLY the working Python code without explanations or markdown.

The code will load data from a SQLite database connection provided as the 'db_conn' variable.
Use SQL queries to select data, then process using pandas.
"""

# Clarifying questions prompt
CLARIFYING_QUESTIONS_PROMPT = """
You are an expert healthcare data analyst. Based on the user's query about patient data, generate 4 relevant clarifying questions that would help provide a more precise analysis.

The questions should address potential ambiguities about:
- Time period or date ranges
- Specific patient demographics or subgroups
- Inclusion/exclusion criteria
- Preferred metrics or visualization types

Return the questions as a JSON array of strings.
"""

# Results interpretation prompt
RESULTS_INTERPRETATION_PROMPT = """
You are an expert healthcare data analyst and medical professional. Based on the patient data analysis results, provide a clear, insightful interpretation that:

1. Directly answers the user's original question
2. Highlights key findings and patterns in the data
3. Provides relevant clinical context or healthcare implications
4. Suggests potential follow-up analyses if appropriate

Your response should be concise (3-5 sentences) but comprehensive, focusing on the most important insights.
"""

# Default clarifying questions for offline mode
DEFAULT_CLARIFYING_QUESTIONS = [
    "Could you clarify the time period of interest?",
    "Which patient subgroup (e.g., gender, age) should we focus on?",
    "Are you interested in averages, counts, or trends?",
    "Do you need any visualizations?",
]

# Default results interpretation for offline mode
DEFAULT_RESULTS_INTERPRETATION = (
    "Here is a concise summary of the analysis results based on the provided data."
)
