"""
basic.py

Code generation for basic aggregate analysis types (count, sum, average, min, max, median, variance, std_dev).
"""

from app.utils.ai.sql_builder import build_filters_clause, sql_select


def generate_basic_code(intent, parameters=None):
    """Generate code for basic aggregate analysis types."""
    analysis_type = getattr(intent, "analysis_type", None)
    target_field = getattr(intent, "target_field", None)
    group_by = getattr(intent, "group_by", []) or []
    additional_fields = getattr(intent, "additional_fields", []) or []
    parameters = parameters or getattr(intent, "parameters", {}) or {}

    sql_where = build_filters_clause(intent)
    sql_where_clause = sql_where[6:] if sql_where.startswith("WHERE ") else sql_where

    # COUNT, SUM, AVG, MIN, MAX (single or multi-metric, with/without group_by)
    if analysis_type in {"count", "sum", "average", "min", "max"}:
        metrics = [target_field] if target_field else []
        metrics += [f for f in additional_fields if f not in metrics]
        if not metrics:
            metrics = ["weight"]
        agg_map = {
            "count": "COUNT",
            "sum": "SUM",
            "average": "AVG",
            "min": "MIN",
            "max": "MAX",
        }
        pandas_agg_map = {
            "count": "count",
            "sum": "sum",
            "average": "mean",
            "min": "min",
            "max": "max",
        }
        agg_func = pandas_agg_map[analysis_type]
        sql_agg_func = agg_map[analysis_type]
        code = f"# SQL equivalent: SELECT {sql_agg_func}({metrics[0]}) FROM vitals v\n"
        code += "# Query data\n"
        select_fields = metrics.copy()
        if group_by:
            select_fields += group_by
        # Special case for count: use COUNT(*) in SQL
        if analysis_type == "count" and not group_by:
            if sql_where_clause:
                code += f'sql = """SELECT COUNT(*) as count FROM vitals v WHERE {sql_where_clause}"""\n'
            else:
                code += 'sql = """SELECT COUNT(*) as count FROM vitals v"""\n'
            code += "# SQL equivalent: SELECT COUNT(*) FROM vitals v"
            if sql_where_clause:
                code += f" WHERE {sql_where_clause}"
            code += "\ndf = query_dataframe(sql)\n"
            code += "if not df.empty and 'count' in df.columns:\n    results = int(df['count'].iloc[0])\nelse:\n    results = 0\n"
            return code
        code += f'sql = """SELECT {sql_select(select_fields)} FROM vitals v'
        if sql_where_clause:
            code += f" WHERE {sql_where_clause}"
        code += '"""\n'
        code += "df = query_dataframe(sql)\n"
        if group_by:
            code += f"# Group by: {group_by}\n"
            code += "results = {}\n"
            if len(metrics) == 1:
                code += (
                    f"grouped = df.groupby({group_by})['{metrics[0]}'].{agg_func}()\n"
                    f"results = grouped.to_dict()\n"
                )
            else:
                code += (
                    f"grouped = df.groupby({group_by})[{metrics}].agg('{agg_func}')\n"
                    "results = grouped.reset_index().to_dict(orient='records')\n"
                )
            code += (
                f"# SQL equivalent:\n"
                f"# SELECT {', '.join([f'v.{g}' for g in group_by])}, "
                f"{', '.join([f'{sql_agg_func}(v.{m})' for m in metrics])
                   } FROM vitals v"
            )
            if sql_where_clause:
                code += f" WHERE {sql_where_clause}"
            code += f" GROUP BY {', '.join([f'v.{g}' for g in group_by])}\n"
        else:
            code += "# Aggregate metrics\n"
            if len(metrics) == 1:
                code += f"metric_value = df['{metrics[0]}'].{agg_func}()\n"
                code += f"results = {{'{metrics[0]}_{agg_func}': metric_value}}\n"
            else:
                code += "results = {}\n"
                for m in metrics:
                    code += f"results['{m}_{agg_func}'] = df['{m}'].{agg_func}()\n"
        code += "# Output is a dictionary of computed metrics\n"
        return code

    # MEDIAN, VARIANCE, STD_DEV (single or multi-metric, with/without group_by)
    if analysis_type in {"median", "variance", "std_dev"}:
        metrics = [target_field] if target_field else []
        metrics += [f for f in additional_fields if f not in metrics]
        if not metrics:
            metrics = ["weight"]
        agg_map = {
            "median": "median",
            "variance": "var",
            "std_dev": "std",
        }
        agg_func = agg_map[analysis_type]
        code = "# Query data\n"
        select_fields = [f"v.{m}" for m in metrics]
        if group_by:
            select_fields += [f"v.{g}" for g in group_by]
        code += f'sql = """SELECT {', '.join(select_fields)} FROM vitals v'
        if sql_where_clause:
            code += f" WHERE {sql_where_clause}"
        code += '"""\n'
        code += "df = query_dataframe(sql)\n"
        if group_by:
            code += f"# Group by: {group_by}\n"
            code += "results = {}\n"
            if len(metrics) == 1:
                code += (
                    f"grouped = df.groupby({group_by})['{metrics[0]}'].{agg_func}()  # {agg_func}()\n"
                    f"results = grouped.to_dict()\n"
                )
            else:
                code += (
                    f"grouped = df.groupby({group_by})[{metrics}].agg('{agg_func}')  # {agg_func}()\n"
                    "results = grouped.reset_index().to_dict(orient='records')\n"
                )
            code += (
                f"# SQL equivalent:\n"
                f"# SELECT {', '.join([f'v.{g}' for g in group_by])}, "
                f"{', '.join([f'{agg_func.upper()}(v.{m})' for m in metrics])
                   } FROM vitals v"
            )
            if sql_where_clause:
                code += f" WHERE {sql_where_clause}"
            code += f" GROUP BY {', '.join([f'v.{g}' for g in group_by])}\n"
        else:
            code += "# Aggregate metrics\n"
            if len(metrics) == 1:
                code += (
                    f"metric_value = df['{metrics[0]}'].{agg_func}()  # {agg_func}()\n"
                )
                code += "results = float(metric_value) if metric_value is not None else None\n"
            else:
                code += "results = {}\n"
                for m in metrics:
                    code += f"results['{m}_{agg_func}'] = df['{m}'].{agg_func}()  # {agg_func}()\n"
        code += "# Output is a dictionary of computed metrics\n"
        return code

    return None


# NO-OP: Trigger CI rebuild for unterminated string fix
