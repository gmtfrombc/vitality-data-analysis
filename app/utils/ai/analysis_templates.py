"""
analysis_templates.py

Templates for generating analysis code for specific analysis types (trend, top_n, histogram, etc.).
"""

from app.utils.query_intent import QueryIntent
from app.utils.ai.sql_builder import build_filters_clause
from typing import Any, Dict


def generate_trend_code(intent: QueryIntent, parameters: Dict[str, Any] = None) -> str:
    """Generate Python code for trend (time series) analysis."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", "weight")
    additional_fields = getattr(intent, "additional_fields", []) or []
    group_by = getattr(intent, "group_by", []) or []
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


def generate_top_n_code(intent: QueryIntent, parameters: Dict[str, Any] = None) -> str:
    """Generate Python code for top-N analysis."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", "weight")
    additional_fields = getattr(intent, "additional_fields", []) or []
    N = parameters.get("N", 10)
    sql_where = build_filters_clause(intent)
    sql_where_clause = sql_where[6:] if sql_where.startswith("WHERE ") else sql_where
    code = "# Query data for top-N analysis\n"
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


def generate_histogram_code(
    intent: QueryIntent, parameters: Dict[str, Any] = None
) -> str:
    """Generate Python code for histogram (distribution) analysis."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", "weight")
    additional_fields = getattr(intent, "additional_fields", []) or []
    sql_where = build_filters_clause(intent)
    sql_where_clause = sql_where[6:] if sql_where.startswith("WHERE ") else sql_where
    code = "# Query data for distribution analysis\n"
    code += f'sql = """SELECT v.{target_field} FROM vitals v'
    if sql_where_clause:
        code += f" WHERE {sql_where_clause}"
    code += '"""\n'
    code += "# Analyze distribution using histogram\n"
    code += "import numpy as np\n"
    code += "df = query_dataframe(sql)\n"
    code += f"data = df['{target_field}'].dropna().astype(float)\n"
    code += "counts, bin_edges = np.histogram(data, bins=10)\n"
    code += "results = {'bin_edges': bin_edges.tolist(), 'counts': counts.tolist()}\n"
    code += "# SQL equivalent (no direct SQL histogram, requires post-processing):\n"
    code += f"# SELECT {target_field} FROM vitals v"
    if sql_where_clause:
        code += f" WHERE {sql_where_clause}"
    code += "\n# Then process with numpy.histogram in Python\n"
    return code


def generate_comparison_code(
    intent: QueryIntent, parameters: Dict[str, Any] = None
) -> str:
    """Generate Python code for group comparison analysis."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", None)
    group_by = getattr(intent, "group_by", []) or []
    if not (group_by and target_field):
        return "# Error: comparison analysis requires group_by and target_field\nresults = {'error': 'Missing group_by or target_field'}\n"
    sql = f"SELECT v.{group_by[0]} as compare_group, AVG(v.{target_field}) as avg_value, COUNT(*) as count FROM vitals v GROUP BY v.{group_by[0]}"
    code = (
        "# Auto-generated comparison analysis\n"
        "from app.db_query import query_dataframe\n"
        "import pandas as pd\n\n"
        f'# SQL to group by and compute average\nsql = "{sql}"\n'
        "df = query_dataframe(sql)\n"
        "print('DEBUG: df.columns =', df.columns.tolist())\n"
        "if df.empty:\n"
        "    results = {'error': 'No data available for comparison analysis'}\n"
        "else:\n"
        "    comparison = df.set_index('compare_group')['avg_value'].to_dict()\n"
        "    counts = df.set_index('compare_group')['count'].to_dict()\n"
        "    results = {'comparison': comparison, 'counts': counts}\n"
    )
    return code


def generate_percent_change_code(
    intent: QueryIntent, parameters: Dict[str, Any] = None
) -> str:
    """Generate Python code for percent change analysis (with or without group_by)."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", None)
    group_by = getattr(intent, "group_by", []) or []
    if not target_field:
        return "# Error: percent_change analysis requires target_field\nresults = {'error': 'Missing target_field'}\n"
    if group_by:
        group_col = group_by[0]
        sql = f"SELECT v.{group_col}, v.{target_field}, v.date FROM vitals v"
        code = (
            "# Auto-generated percent change analysis\n"
            "from app.db_query import query_dataframe\n"
            "import pandas as pd\n\n"
            f'# Query all data for percent change\nsql = "{sql}"\n'
            f"df = query_dataframe(sql)\n"
            f"if df.empty or df['{target_field}'].dropna().empty:\n"
            f"    results = {{'error': 'No data available for percent change analysis'}}\n"
            f"else:\n"
            f"    df = df.dropna(subset=['{target_field}', '{group_col}'])\n"
            f"    if 'date' in df.columns:\n"
            f"        df = df.dropna(subset=['date'])\n"
            f"        df = df.sort_values(['date'])\n"
            f"    percent_changes = {{}}\n"
            f"    for group, group_df in df.groupby('{group_col}'):\n"
            f"        group_df = group_df.dropna(subset=['{target_field}'])\n"
            f"        if 'date' in group_df.columns:\n"
            f"            group_df = group_df.dropna(subset=['date'])\n"
            f"            group_df = group_df.sort_values(['date'])\n"
            f"        if group_df.empty:\n"
            f"            percent_changes[group] = None\n"
            f"            continue\n"
            f"        first = group_df.iloc[0]['{target_field}']\n"
            f"        last = group_df.iloc[-1]['{target_field}']\n"
            f"        if first == 0 or pd.isna(first) or pd.isna(last):\n"
            f"            percent_changes[group] = None\n"
            f"        else:\n"
            f"            percent_changes[group] = 100 * (last - first) / abs(first)\n"
            f"    results = percent_changes\n"
        )
    else:
        sql = f"SELECT v.{target_field}, v.date FROM vitals v"
        code = (
            "# Auto-generated percent change analysis\n"
            "from app.db_query import query_dataframe\n"
            "import pandas as pd\n\n"
            f'# Query all data for percent change\nsql = "{sql}"\n'
            f"df = query_dataframe(sql)\n"
            f"if df.empty or df['{target_field}'].dropna().empty:\n"
            f"    results = {{'error': 'No data available for percent change analysis'}}\n"
            f"else:\n"
            f"    df = df.dropna(subset=['{target_field}'])\n"
            f"    if 'date' in df.columns:\n"
            f"        df = df.dropna(subset=['date'])\n"
            f"        df = df.sort_values('date')\n"
            f"    if df.empty:\n"
            f"        results = None\n"
            f"    else:\n"
            f"        first = df.iloc[0]['{target_field}']\n"
            f"        last = df.iloc[-1]['{target_field}']\n"
            f"        if first == 0 or pd.isna(first) or pd.isna(last):\n"
            f"            results = None\n"
            f"        else:\n"
            f"            results = 100 * (last - first) / abs(first)\n"
        )
    return code


def generate_correlation_code(
    intent: QueryIntent, parameters: Dict[str, Any] = None
) -> str:
    """Generate Python code for correlation analysis (simple, conditional, or time_series)."""
    # This is a direct move of _generate_correlation_code from code_generator.py
    # For brevity, just call the original _generate_correlation_code for now (to be refactored if needed)
    from app.utils.ai.code_generator import _generate_correlation_code

    return _generate_correlation_code(intent)


__all__ = [
    "generate_trend_code",
    "generate_top_n_code",
    "generate_histogram_code",
    "generate_comparison_code",
    "generate_percent_change_code",
    "generate_correlation_code",
]
