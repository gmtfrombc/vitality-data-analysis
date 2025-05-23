"""
top_n.py

Code generation for top-N and histogram/distribution analysis types.
"""

from app.utils.ai.sql_builder import build_filters_clause


def generate_top_n(intent, parameters=None):
    """Generate code for top-N analysis."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", "weight")
    N = parameters.get("N", 10)
    sql_where = build_filters_clause(intent)
    sql_where_clause = sql_where[6:] if sql_where.startswith("WHERE ") else sql_where
    code = "# Query data for top-N analysis\n"

    # Check if we need a JOIN for patient filters
    needs_patient_join = False
    patient_fields = {"active", "gender", "ethnicity", "age"}
    if hasattr(intent, "filters") and intent.filters:
        for f in intent.filters:
            if f.field.lower() in patient_fields:
                needs_patient_join = True
                break

    if needs_patient_join:
        # Use JOIN when we need patient filters with vitals data
        code += f'sql = """SELECT v.{target_field} FROM vitals v JOIN patients p ON v.patient_id = p.id'
        if sql_where_clause:
            # Fix table prefixes in WHERE clause
            fixed_where_clause = sql_where_clause.replace("patients.", "p.")
            code += f" WHERE {fixed_where_clause}"
        code += '"""\n'
    else:
        # Use simple vitals query when no patient filters
        code += f'sql = """SELECT v.{target_field} FROM vitals v'
        if sql_where_clause:
            code += f" WHERE {sql_where_clause}"
        code += '"""\n'
    code += "df = query_dataframe(sql)\n"
    code += f"# Compute value counts and get top {N}\n"
    code += f"results = df['{target_field}'].value_counts().nlargest({N}).to_dict()\n"
    code += "# SQL equivalent:\n"
    code += f"# SELECT v.{target_field}, COUNT(*) as count FROM vitals v"
    if sql_where_clause:
        code += f" WHERE {sql_where_clause}"
    code += f" GROUP BY v.{target_field} ORDER BY count DESC LIMIT {N}\n"
    return code


def generate_histogram(intent, parameters=None):
    """Generate code for histogram/distribution analysis."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", "weight")
    bins = parameters.get("bins", 10)
    sql_where = build_filters_clause(intent)
    sql_where_clause = sql_where[6:] if sql_where.startswith("WHERE ") else sql_where
    code = "# Query data for histogram analysis\n"

    # Check if we need a JOIN for patient filters
    needs_patient_join = False
    patient_fields = {"active", "gender", "ethnicity", "age"}
    if hasattr(intent, "filters") and intent.filters:
        for f in intent.filters:
            if f.field.lower() in patient_fields:
                needs_patient_join = True
                break

    if needs_patient_join:
        # Use JOIN when we need patient filters with vitals data
        code += f'sql = """SELECT v.{target_field} FROM vitals v JOIN patients p ON v.patient_id = p.id'
        if sql_where_clause:
            # Fix table prefixes in WHERE clause
            fixed_where_clause = sql_where_clause.replace("patients.", "p.")
            code += f" WHERE {fixed_where_clause}"
        code += '"""\n'
    else:
        # Use simple vitals query when no patient filters
        code += f'sql = """SELECT v.{target_field} FROM vitals v'
        if sql_where_clause:
            code += f" WHERE {sql_where_clause}"
        code += '"""\n'
    code += "df = query_dataframe(sql)\n"
    code += f"# Compute histogram with {bins} bins\n"
    code += f"import numpy as np\ncounts, bin_edges = np.histogram(df['{target_field}'], bins={bins})\nresults = {{'histogram': counts.tolist(), 'bin_edges': bin_edges.tolist()}}\n"
    code += "# SQL equivalent:\n"
    code += f"# SELECT v.{target_field} FROM vitals v"
    if sql_where_clause:
        code += f" WHERE {sql_where_clause}"
    code += "\n# Histogram computed in pandas/numpy\n"
    return code
