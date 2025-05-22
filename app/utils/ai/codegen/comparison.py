"""
comparison.py

Code generation for group comparison analysis types.
"""


def generate_comparison_code(intent, parameters=None):
    """Generate code for group comparison analysis."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", None)
    group_by = getattr(intent, "group_by", []) or []
    if not (group_by and target_field):
        return "# Error: comparison analysis requires group_by and target_field\nresults = {'error': 'Missing group_by or target_field'}\n"
    sql = f"SELECT v.{group_by[0]} as compare_group, AVG(v.{target_field}) as avg_value, COUNT(*) as count FROM vitals v GROUP BY v.{group_by[0]}"
    code = (
        "# Auto-generated comparison analysis\n"
        "from db_query import query_dataframe\n"
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
