"""
correlation.py

Code generation for correlation analysis types.
"""


def generate_correlation_code(intent, parameters=None):
    """Generate code for correlation analysis."""
    # Extract metrics for correlation
    if hasattr(intent, "additional_fields") and intent.additional_fields:
        metric_x = intent.target_field
        metric_y = intent.additional_fields[0]
    else:
        metric_x = intent.target_field
        metric_y = "bmi" if metric_x != "bmi" else "weight"

    method = getattr(intent, "parameters", {}).get("method", "pearson")
    correlation_type = getattr(intent, "parameters", {}).get(
        "correlation_type", "simple"
    )
    period = getattr(intent, "parameters", {}).get("period", "month")
    rolling_window = getattr(intent, "parameters", {}).get("rolling_window", None)

    # Basic correlation
    if correlation_type == "simple":
        code = f"""
# Calculate correlation between {metric_x} and {metric_y}
import pandas as pd
from app.db_query import query_dataframe
from app.utils.plots import scatter_plot

sql = '''SELECT v.{metric_x}, v.{metric_y} FROM vitals v'''
df = query_dataframe(sql)
correlation = df['{metric_x}'].corr(df['{metric_y}'], method='{method}')
viz = scatter_plot(df, x='{metric_x}', y='{metric_y}', title='Correlation: {metric_x} vs {metric_y}', correlation=True, regression=True)
results = {{
    'correlation_coefficient': correlation,
    'metrics': ['{metric_x}', '{metric_y}'],
    'method': '{method}',
    'visualization': viz
}}
"""
        return code

    # Conditional correlation
    if (
        correlation_type == "conditional"
        and hasattr(intent, "group_by")
        and intent.group_by
    ):
        group_col = intent.group_by[0]
        code = f"""
# Calculate conditional correlations between {metric_x} and {metric_y} by {group_col}
import pandas as pd
from app.db_query import query_dataframe
from app.utils.advanced_correlation import conditional_correlation, conditional_correlation_heatmap

sql = '''SELECT v.{metric_x}, v.{metric_y}, p.{group_col} FROM vitals v JOIN patients p ON v.patient_id = p.id'''
df = query_dataframe(sql)
results = conditional_correlation(df, metric_x='{metric_x}', metric_y='{metric_y}', condition_field='{group_col}', method='{method}')
overall_corr = df['{metric_x}'].corr(df['{metric_y}'], method='{method}')
viz = conditional_correlation_heatmap(results, main_correlation=overall_corr, title='Correlation between {metric_x} and {metric_y} by {group_col}')
results = {{
    'correlation_by_group': {{k: v[0] for k, v in results.items()}},
    'p_values': {{k: v[1] for k, v in results.items()}},
    'overall_correlation': overall_corr,
    'method': '{method}',
    'visualization': viz
}}
"""
        return code

    # Time-series correlation
    if correlation_type == "time_series":
        rolling_window_param = (
            f", rolling_window={rolling_window}" if rolling_window else ""
        )
        code = f"""
# Calculate how correlation between {metric_x} and {metric_y} changes over time
import pandas as pd
from app.db_query import query_dataframe
from app.utils.advanced_correlation import time_series_correlation, time_series_correlation_plot

sql = '''SELECT v.{metric_x}, v.{metric_y}, v.date FROM vitals v'''
df = query_dataframe(sql)
results_df = time_series_correlation(df, metric_x='{metric_x}', metric_y='{metric_y}', date_column='date', period='{period}'{rolling_window_param}, method='{method}')
viz = time_series_correlation_plot(results_df, title='Correlation between {metric_x} and {metric_y} Over Time')
correlations_over_time = dict(zip(results_df['period'], results_df['correlation']))
p_values_over_time = dict(zip(results_df['period'], results_df['p_value']))
results = {{
    'correlations_over_time': correlations_over_time,
    'p_values': p_values_over_time,
    'method': '{method}',
    'period': '{period}',
    'visualization': viz
}}
"""
        return code

    # Fallback
    return "# Unable to generate correlation code for the requested analysis type.\nresults = {'error': 'Unknown or unsupported correlation type.'}\n"
