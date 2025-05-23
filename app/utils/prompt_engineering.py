"""
Prompt Engineering, Schema Description, and Example Query Logic for AI Assistant

This module centralizes all prompt construction, schema formatting, and example query logic for the AI Assistant.
"""

from typing import Dict, Any, List

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
        "List all patients with high engagement scores (>80)",
    ],
    "Lab Results": [
        "Find patients with A1C over 8 in their first lab test",
        "Show me female patients with high cholesterol (>240)",
        "List patients whose A1C improved by more than 1 point",
    ],
    "Vitals": [
        "Find patients with systolic BP over 140",
        "Show me patients who lost more than 10 pounds during the program",
        "List patients with BMI over 30 at program start",
    ],
    "Combined Queries": [
        "Find female patients over 50 with A1C over 9 and high blood pressure",
        "Show men with healthy BMI (18.5-24.9) and good heart fitness scores",
        "List patients who improved both A1C and blood pressure during the program",
    ],
}


def get_query_examples() -> Dict[str, List[str]]:
    """
    Return the example queries grouped by category.
    """
    return QUERY_EXAMPLES


def describe_schema(
    table_details: Dict[str, Any], table_relationships: List[str]
) -> str:
    """
    Create an enhanced description of the database schema for prompt construction.

    Args:
        table_details: Dict mapping table names to their columns/types.
        table_relationships: List of relationship strings.

    Returns:
        A formatted string describing the schema and relationships.
    """
    schema_parts = []
    essential_tables = [
        "patients",
        "vitals",
        "lab_results",
        "scores",
        "pmh",
        "patient_visit_metrics",
        "mental_health",
    ]
    for table_name in essential_tables:
        if table_name.lower() in table_details:
            table_info = table_details[table_name.lower()]
            columns_info = []
            for col_name, col_type in table_info.get("column_types", {}).items():
                columns_info.append(f"{col_name} ({col_type})")
            schema_parts.append(
                f"Table: {table_name}\nColumns: {', '.join(columns_info)}"
            )
    if table_relationships:
        schema_parts.append("Relationships:\n" + "\n".join(table_relationships))
    return "\n\n".join(schema_parts)


def build_prompt(query_text: str, schema_description: str) -> Dict[str, str]:
    """
    Build the system and user prompt for the LLM, including schema and examples.

    Args:
        query_text: The user's natural language question.
        schema_description: The formatted schema string.

    Returns:
        Dict with 'system_prompt' and 'user_prompt' keys.
    """
    # Example-based user prompt
    user_prompt = f"""Here are some examples of natural language questions and their corresponding SQL queries:\n\nExample 1:\nUser: Show me all female patients over 65\nSQL:\nSELECT p.id as patient_id, p.first_name, p.last_name, p.birth_date\nFROM patients p\nWHERE p.gender = 'F' AND (date('now') - p.birth_date) > 65\nORDER BY p.birth_date ASC\n\nExample 2:\nUser: Find patients with A1C over 8\nSQL:\nSELECT p.id as patient_id, p.first_name, p.last_name, l.value as a1c_value\nFROM patients p\nJOIN lab_results l ON p.id = l.patient_id\nWHERE l.test_name = 'HbA1c' AND l.value > 8\nORDER BY l.value DESC\n\nExample 3:\nUser: Show me patients who improved their blood pressure during the program\nSQL:\nWITH first_bp AS (\n    SELECT patient_id, MIN(date) as first_date, sbp as first_sbp, dbp as first_dbp\n    FROM vitals\n    GROUP BY patient_id\n),\nlast_bp AS (\n    SELECT patient_id, MAX(date) as last_date, sbp as last_sbp, dbp as last_dbp\n    FROM vitals\n    GROUP BY patient_id\n)\nSELECT p.id as patient_id, p.first_name, p.last_name, \n       f.first_sbp, f.first_dbp, l.last_sbp, l.last_dbp\nFROM patients p\nJOIN first_bp f ON p.id = f.patient_id\nJOIN last_bp l ON p.id = l.patient_id\nWHERE (f.first_sbp > l.last_sbp OR f.first_dbp > l.last_dbp)\nORDER BY (f.first_sbp - l.last_sbp) + (f.first_dbp - l.last_dbp) DESC\n\nExample 4:\nUser: Find patients with high blood pressure readings\nSQL:\nSELECT p.id as patient_id, p.first_name, p.last_name, v.sbp, v.dbp, v.date as test_date\nFROM patients p\nJOIN vitals v ON p.id = v.patient_id\nWHERE v.sbp > 140 OR v.dbp > 90\nORDER BY v.sbp DESC\n\nExample 5:\nUser: Show me patients who lost weight during the program\nSQL:\nWITH first_weight AS (\n    SELECT patient_id, MIN(date) as first_date, weight as initial_weight\n    FROM vitals\n    GROUP BY patient_id\n),\nlast_weight AS (\n    SELECT patient_id, MAX(date) as last_date, weight as final_weight\n    FROM vitals\n    GROUP BY patient_id\n)\nSELECT p.id as patient_id, p.first_name, p.last_name, \n       fw.initial_weight, lw.final_weight,\n       (fw.initial_weight - lw.final_weight) as weight_loss,\n       ((fw.initial_weight - lw.final_weight) / fw.initial_weight * 100) as pct_loss\nFROM patients p\nJOIN first_weight fw ON p.id = fw.patient_id\nJOIN last_weight lw ON p.id = lw.patient_id\nWHERE lw.final_weight < fw.initial_weight\nORDER BY pct_loss DESC\n\nNow, generate ONLY a SQL query for this question:\n{query_text}\n"""
    system_prompt = f"""You are an expert SQL generator specializing in healthcare database queries. \n\nDATABASE SCHEMA:\n{schema_description}\n\nIMPORTANT RULES:\n1. Generate ONLY valid SQLite SQL queries\n2. All table names are in PLURAL form (patients, not patient; vitals, not vital)\n3. Use only tables and columns that exist in the schema\n4. When joining tables, always ensure the join conditions are correct\n5. Format dates using datetime() function when needed\n6. Return ONLY the SQL query with no explanation or comments\n7. Use table aliases for readability (p for patients, v for vitals, etc.)\n8. The vitals table does NOT have a test_name column - it has direct columns for sbp, dbp, weight, etc.\n\nThe query should be straightforward, focused, and follow SQLite syntax exactly.\n"""
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}
