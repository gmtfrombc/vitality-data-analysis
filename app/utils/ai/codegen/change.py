"""
change.py

Code generation for relative/percent change analysis types.
"""


def generate_relative_change_code(intent, parameters=None):
    """Generate code for relative/percent change analysis."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", None)
    group_by = getattr(intent, "group_by", []) or []
    if not target_field:
        return "# Error: percent change analysis requires target_field\nresults = {'error': 'Missing target_field'}\n"
    if group_by:
        group_col = group_by[0]
        code = f"""# Auto-generated percent change analysis
from app.db_query import query_dataframe
import pandas as pd

# Query all data for percent change
sql = 'SELECT v.{group_col}, v.{target_field}, v.date FROM vitals v'
df = query_dataframe(sql)
if df.empty or df['{target_field}'].dropna().empty:
    results = {{'error': 'No data available for percent change analysis'}}
else:
    df = df.dropna(subset=['{target_field}', '{group_col}'])
    if 'date' in df.columns:
        df = df.dropna(subset=['date'])
        df = df.sort_values(['date'])
    percent_changes = {{}}
    for group, group_df in df.groupby('{group_col}'):
        group_df = group_df.dropna(subset=['{target_field}'])
        if 'date' in group_df.columns:
            group_df = group_df.dropna(subset=['date'])
            group_df = group_df.sort_values(['date'])
        if group_df.empty:
            percent_changes[group] = None
            continue
        first = group_df.iloc[0]['{target_field}']
        last = group_df.iloc[-1]['{target_field}']
        if first == 0 or pd.isna(first) or pd.isna(last):
            percent_changes[group] = None
        else:
            percent_changes[group] = 100 * (last - first) / abs(first)
    results = percent_changes
"""
    else:
        code = f"""# Auto-generated percent change analysis
from app.db_query import query_dataframe
import pandas as pd

# Query all data for percent change
sql = 'SELECT v.{target_field}, v.date FROM vitals v'
df = query_dataframe(sql)
if df.empty or df['{target_field}'].dropna().empty:
    results = {{'error': 'No data available for percent change analysis'}}
else:
    df = df.dropna(subset=['{target_field}'])
    if 'date' in df.columns:
        df = df.dropna(subset=['date'])
        df = df.sort_values('date')
    if df.empty:
        results = None
    else:
        first = df.iloc[0]['{target_field}']
        last = df.iloc[-1]['{target_field}']
        if first == 0 or pd.isna(first) or pd.isna(last):
            results = None
        else:
            results = 100 * (last - first) / abs(first)
"""
    return code.replace(
        "from db_query import query_dataframe",
        "from app.db_query import query_dataframe",
    )
