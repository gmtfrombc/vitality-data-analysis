import logging
import re
from typing import Any, Dict, Optional, Set


logger = logging.getLogger(__name__)


def generate_sql(
    query_text: str, client: Any, schema_description: str, ui: Optional[Any] = None
) -> Dict[str, Any]:
    """Generate SQL from natural language using OpenAI client and schema description.

    Args:
        query_text: The user's natural language question.
        client: The OpenAI client instance.
        schema_description: The database schema description for the prompt.
        ui: Optional UI object for status updates.

    Returns:
        Dict with keys 'sql' (str) and 'error' (str or None).
    """
    if not client:
        msg = "OpenAI client not initialized"
        if ui:
            ui.update_status(msg, type="error")
        return {"sql": "", "error": msg}

    if not query_text.strip():
        msg = "Please enter a question first"
        if ui:
            ui.update_status(msg, type="warning")
        return {"sql": "", "error": msg}

    try:
        logger.info(f"Generating SQL for query: {query_text}")
        logger.debug(f"Schema description for prompt:\n{schema_description}")

        # Build the system prompt
        system_prompt = f"""You are an expert SQL generator specializing in healthcare database queries. \n\nDATABASE SCHEMA:\n{schema_description}\n\nIMPORTANT RULES:\n1. Generate ONLY valid SQLite SQL queries\n2. All table names are in PLURAL form (patients, not patient; vitals, not vital)\n3. Use only tables and columns that exist in the schema\n4. When joining tables, always ensure the join conditions are correct\n5. Format dates using datetime() function when needed\n6. Return ONLY the SQL query with no explanation or comments\n7. Use table aliases for readability (p for patients, v for vitals, etc.)\n8. The vitals table does NOT have a test_name column - it has direct columns for sbp, dbp, weight, etc.\n\nThe query should be straightforward, focused, and follow SQLite syntax exactly.\n"""

        # Example-based user prompt (could be parameterized if needed)
        user_prompt = f"""Here are some examples of natural language questions and their corresponding SQL queries:\n\nExample 1:\nUser: Show me all female patients over 65\nSQL:\nSELECT p.id as patient_id, p.first_name, p.last_name, p.birth_date\nFROM patients p\nWHERE p.gender = 'F' AND (date('now') - p.birth_date) > 65\nORDER BY p.birth_date ASC\n\nExample 2:\nUser: Find patients with A1C over 8\nSQL:\nSELECT p.id as patient_id, p.first_name, p.last_name, l.value as a1c_value\nFROM patients p\nJOIN lab_results l ON p.id = l.patient_id\nWHERE l.test_name = 'HbA1c' AND l.value > 8\nORDER BY l.value DESC\n\nExample 3:\nUser: Show me patients who improved their blood pressure during the program\nSQL:\nWITH first_bp AS (\n    SELECT patient_id, MIN(date) as first_date, sbp as first_sbp, dbp as first_dbp\n    FROM vitals\n    GROUP BY patient_id\n),\nlast_bp AS (\n    SELECT patient_id, MAX(date) as last_date, sbp as last_sbp, dbp as last_dbp\n    FROM vitals\n    GROUP BY patient_id\n)\nSELECT p.id as patient_id, p.first_name, p.last_name, \n       f.first_sbp, f.first_dbp, l.last_sbp, l.last_dbp\nFROM patients p\nJOIN first_bp f ON p.id = f.patient_id\nJOIN last_bp l ON p.id = l.patient_id\nWHERE (f.first_sbp > l.last_sbp OR f.first_dbp > l.last_dbp)\nORDER BY (f.first_sbp - l.last_sbp) + (f.first_dbp - l.last_dbp) DESC\n\nExample 4:\nUser: Find patients with high blood pressure readings\nSQL:\nSELECT p.id as patient_id, p.first_name, p.last_name, v.sbp, v.dbp, v.date as test_date\nFROM patients p\nJOIN vitals v ON p.id = v.patient_id\nWHERE v.sbp > 140 OR v.dbp > 90\nORDER BY v.sbp DESC\n\nExample 5:\nUser: Show me patients who lost weight during the program\nSQL:\nWITH first_weight AS (\n    SELECT patient_id, MIN(date) as first_date, weight as initial_weight\n    FROM vitals\n    GROUP BY patient_id\n),\nlast_weight AS (\n    SELECT patient_id, MAX(date) as last_date, weight as final_weight\n    FROM vitals\n    GROUP BY patient_id\n)\nSELECT p.id as patient_id, p.first_name, p.last_name, \n       fw.initial_weight, lw.final_weight,\n       (fw.initial_weight - lw.final_weight) as weight_loss,\n       ((fw.initial_weight - lw.final_weight) / fw.initial_weight * 100) as pct_loss\nFROM patients p\nJOIN first_weight fw ON p.id = fw.patient_id\nJOIN last_weight lw ON p.id = lw.patient_id\nWHERE lw.final_weight < fw.initial_weight\nORDER BY pct_loss DESC\n\nNow, generate ONLY a SQL query for this question:\n{query_text}\n"""

        if ui:
            ui.update_status("Generating SQL query... please wait.", type="info")

        response = client.chat.completions.create(
            model="gpt-4",  # Or use a parameter/constant
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        sql = response.choices[0].message.content.strip()
        logger.debug(f"Raw AI response: {sql}")
        return {"sql": sql, "error": None}
    except Exception as e:
        logger.error(f"Error generating SQL: {str(e)}")
        if ui:
            ui.update_status(f"ERROR: Failed to generate SQL: {str(e)}", type="error")
        return {"sql": "", "error": str(e)}


def clean_generated_sql(sql: str) -> str:
    """Clean the generated SQL by removing markdown formatting and comments, and fixing common issues."""
    # Extract SQL from markdown code blocks if present
    if "```sql" in sql:
        match = re.search(r"```sql\n(.*?)\n```", sql, re.DOTALL)
        if match:
            sql = match.group(1).strip()
    elif "```" in sql:
        match = re.search(r"```\n(.*?)\n```", sql, re.DOTALL)
        if match:
            sql = match.group(1).strip()
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"\bpatient\b", "patients", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bvital\b", "vitals", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\blab\b(?!_)", "lab_results", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bscore\b", "scores", sql, flags=re.IGNORECASE)
    sql = re.sub(
        r"FROM\s+vitals\s+WHERE\s+test_name\s*=\s*[\'\"]blood_pressure[\'\"]",
        "FROM vitals",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"FROM\s+vitals\s+WHERE\s+test_name\s*=\s*[\'\"]weight[\'\"]",
        "FROM vitals",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"FROM\s+vitals\s+WHERE\s+test_name\s*=\s*[\'\"]bmi[\'\"]",
        "FROM vitals",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(r"vitals\.test_date", "vitals.date", sql, flags=re.IGNORECASE)
    logger.debug(f"Cleaned SQL: {sql}")
    return sql.strip()


def extract_sql_references(sql_query: str) -> Dict[str, Set[str]]:
    """Extract table and column references from an SQL query."""
    logger.info("Extracting table and column references from SQL query")
    sql_lower = sql_query.lower()
    tables = set()
    from_matches = re.finditer(r"from\s+([a-z0-9_]+)", sql_lower)
    for match in from_matches:
        tables.add(match.group(1))
    join_matches = re.finditer(r"join\s+([a-z0-9_]+)", sql_lower)
    for match in join_matches:
        tables.add(match.group(1))
    qualified_matches = re.finditer(r"([a-z0-9_]+)\.", sql_lower)
    for match in qualified_matches:
        tables.add(match.group(1))
    columns = set()
    select_match = re.search(r"select\s+(.*?)\s+from", sql_lower, re.DOTALL)
    if select_match:
        select_clause = select_match.group(1)
        select_clause = re.sub(r"count\s*\(\s*\*\s*\)", "", select_clause)
        select_clause = re.sub(r"[a-z0-9_]+\s*\(([^)]*)\)", r"\1", select_clause)
        select_clause = re.sub(r"as\s+[a-z0-9_]+", "", select_clause)
        for item in select_clause.split(","):
            item = item.strip()
            if "." in item:
                cols = re.findall(r"[a-z0-9_]+\.([a-z0-9_]+)", item)
                columns.update(cols)
            elif item and item != "*":
                columns.add(item)
    clause_matches = re.finditer(
        r"(where|group\s+by|order\s+by|having)\s+(.*?)(?:limit|$|\s+(?:where|group\s+by|order\s+by|having))",
        sql_lower,
        re.DOTALL,
    )
    for clause_match in clause_matches:
        clause = clause_match.group(2).strip()
        qualified_cols = re.findall(r"([a-z0-9_]+)\.([a-z0-9_]+)", clause)
        for _, col in qualified_cols:
            columns.add(col)
        unqualified_cols = re.findall(
            r"(?<![a-z0-9_\.])[a-z0-9_]+(?=\s*[=<>!]|\s+(?:is|like|in|between))",
            clause,
        )
        columns.update(unqualified_cols)
    logger.info(f"Extracted tables: {tables}")
    logger.info(f"Extracted columns: {columns}")
    return {"tables": tables, "columns": columns}


def validate_sql(
    sql_query: str,
    table_details: Dict[str, Any],
    db_query: Any,
    validate_schema_references: Any,
) -> Dict[str, Any]:
    """Validate SQL syntax and schema references without executing the query."""
    if not sql_query:
        return {"valid": False, "error": "Empty SQL query"}
    logger.info(f"Validating SQL: {sql_query}")
    query_references = extract_sql_references(sql_query)
    schema_validation = validate_schema_references(query_references, table_details)
    if not schema_validation["valid"]:
        return schema_validation
    # Pre-check for common errors that SQLite might not catch clearly
    if (
        "JOIN" in sql_query.upper()
        and "vitals" in sql_query.lower()
        and "test_name" in sql_query.lower()
    ):
        logger.warning(
            "Detected potential error: JOIN with 'test_name' in vitals table"
        )
        fixed_query = re.sub(
            r"FROM\s+vitals\s+WHERE\s+test_name\s*=\s*[\'\"]([^\'\"]+)[\'\"]",
            "FROM vitals",
            sql_query,
            flags=re.IGNORECASE,
        )
        if fixed_query != sql_query:
            logger.info(f"Automatically fixed vitals table query: {fixed_query}")
            sql_query = fixed_query
    singular_to_plural = {
        r"\bpatient\b": "patients",
        r"\bvital\b": "vitals",
        r"\blab\b(?!_)": "lab_results",
        r"\bscore\b": "scores",
    }
    for singular, plural in singular_to_plural.items():
        if re.search(singular, sql_query, re.IGNORECASE):
            logger.warning(
                f"Detected singular table name: {singular.strip('\\b')} should be {plural}"
            )
            sql_query = re.sub(singular, plural, sql_query, flags=re.IGNORECASE)
            logger.info(
                f"Automatically converted singular table name to plural: {singular.strip('\\b')}  {plural}"
            )
    try:
        db_query.query_dataframe(f"EXPLAIN QUERY PLAN {sql_query}")
        return {"valid": True, "error": None}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error validating SQL: {error_msg}")
        return {"valid": False, "error": f"Validation error: {error_msg}"}


def attempt_sql_fix(
    sql_query: str,
    error_msg: str,
    table_details: Dict[str, Any],
    suggest_similar_names: Any,
) -> Optional[str]:
    """Attempt to fix common SQL errors automatically using schema information."""
    logger.info(f"Attempting to fix SQL: {sql_query}")
    logger.info(f"Error message: {error_msg}")
    original_query = sql_query
    replacements = {
        r"\bpatient\b": "patients",
        r"\bvital\b": "vitals",
        r"\blab\b(?!_)": "lab_results",
        r"\bscore\b": "scores",
        r"\bpm\b(?!h)": "pmh",
        r"vitals\.test_date": "vitals.date",
        r"vitals\.test_name": "",
        r"patient\.patient_id": "patient.id",
        r"patients\.patient_id": "patients.id",
        r"DATEDIFF\(": "julianday(",
        r"DATEDIFF\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)": "julianday(\2) - julianday(\1)",
        r"DATE_DIFF\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)": "julianday(\2) - julianday(\1)",
    }
    if "no such table" in error_msg.lower():
        table_match = re.search(r"no such table:\s*([^\s,]+)", error_msg.lower())
        if table_match:
            bad_table = table_match.group(1).strip()
            logger.info(f"Attempting to fix unknown table: {bad_table}")
            if bad_table + "s" in table_details:
                pattern = r"\b" + re.escape(bad_table) + r"\b"
                sql_query = re.sub(
                    pattern, bad_table + "s", sql_query, flags=re.IGNORECASE
                )
                logger.info(f"Fixed singular table name: {bad_table} -> {bad_table}s")
            else:
                similar_tables = suggest_similar_names(
                    bad_table, list(table_details.keys())
                )
                if similar_tables:
                    best_match = similar_tables[0]
                    pattern = r"\b" + re.escape(bad_table) + r"\b"
                    sql_query = re.sub(
                        pattern, best_match, sql_query, flags=re.IGNORECASE
                    )
                    logger.info(
                        f"Replaced unknown table with similar one: {bad_table} -> {best_match}"
                    )
    elif "no such column" in error_msg.lower():
        col_match = re.search(r"no such column:\s*([^\s,]+)", error_msg.lower())
        if col_match:
            bad_column = col_match.group(1).strip()
            logger.info(f"Attempting to fix unknown column: {bad_column}")
            if "." in bad_column:
                table_name, col_name = bad_column.split(".")
                if table_name.lower() in table_details:
                    table_columns = table_details[table_name.lower()]["columns"]
                    similar_cols = suggest_similar_names(col_name, table_columns)
                    if similar_cols:
                        best_match = similar_cols[0]
                        pattern = r"\b" + re.escape(bad_column) + r"\b"
                        replacement = f"{table_name}.{best_match}"
                        sql_query = re.sub(
                            pattern, replacement, sql_query, flags=re.IGNORECASE
                        )
                        logger.info(
                            f"Fixed column reference: {bad_column} -> {replacement}"
                        )
            else:
                for table_name, table_info in table_details.items():
                    table_columns = table_info["columns"]
                    similar_cols = suggest_similar_names(bad_column, table_columns)
                    if similar_cols:
                        best_match = similar_cols[0]
                        pattern = r"\b" + re.escape(bad_column) + r"\b"
                        sql_query = re.sub(
                            pattern, best_match, sql_query, flags=re.IGNORECASE
                        )
                        logger.info(
                            f"Fixed column reference: {bad_column} -> {best_match}"
                        )
                        break
                if (
                    bad_column.lower() == "patient_id"
                    and "patients" in sql_query.lower()
                ):
                    sql_query = re.sub(
                        r"\bpatient_id\b", "id", sql_query, flags=re.IGNORECASE
                    )
                    logger.info(
                        "Fixed column reference: patient_id -> id in patients table"
                    )
                elif (
                    bad_column.lower() == "test_date" and "vitals" in sql_query.lower()
                ):
                    sql_query = re.sub(
                        r"\btest_date\b", "date", sql_query, flags=re.IGNORECASE
                    )
                    logger.info(
                        "Fixed column reference: test_date -> date in vitals table"
                    )
    # (Ambiguous column handling omitted for brevity)
    return sql_query if sql_query != original_query else None


def suggest_similar_names(
    name: str, options: list, max_suggestions: int = 3, threshold: float = 0.6
) -> list:
    """Suggest similar names from available options based on string similarity."""
    import difflib

    name = name.lower()
    options_lower = [opt.lower() for opt in options]
    similar = difflib.get_close_matches(
        name, options_lower, n=max_suggestions, cutoff=threshold
    )
    result = []
    for sim in similar:
        idx = options_lower.index(sim)
        result.append(options[idx])
    return result
