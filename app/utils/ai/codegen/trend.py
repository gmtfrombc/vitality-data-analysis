"""
trend.py

Code generation for trend/time series analysis types.
"""

from app.utils.ai.sql_builder import build_filters_clause


def generate_trend(intent, parameters=None):
    """Generate code for trend/time series analysis."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", "weight")
    period = parameters.get("period", "month")
    sql_where = build_filters_clause(intent)
    sql_where_clause = sql_where[6:] if sql_where.startswith("WHERE ") else sql_where
    code = "# Query data for trend analysis\n"
    code += f'sql = """SELECT v.{target_field}, v.date FROM vitals v'
    if sql_where_clause:
        code += f" WHERE {sql_where_clause}"
    code += '"""\n'
    code += "df = query_dataframe(sql)\n"
    code += "# Convert date to pandas datetime\n"
    code += "df['date'] = pd.to_datetime(df['date'])\n"
    if period == "month":
        code += "# Group by month using strftime('%Y-%m')\n"
        code += "df['period'] = df['date'].dt.strftime('%Y-%m')\n"
    elif period == "week":
        code += "df['period'] = df['date'].dt.strftime('%Y-%U')\n"
    else:
        code += f"df['period'] = df['date'].dt.{period}\n"
    code += f"# Aggregate by period\nresults = df.groupby('period')['{target_field}'].mean().to_dict()\n"
    code += "# SQL equivalent:\n"
    code += f"# SELECT strftime('%Y-%m', v.date) as period, AVG(v.{target_field}) FROM vitals v"
    if sql_where_clause:
        code += f" WHERE {sql_where_clause}"
    code += " GROUP BY period\n"
    return code
