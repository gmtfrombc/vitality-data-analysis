"""
comparison.py

Code generation for group comparison analysis types.
"""


def generate_comparison_code(intent, parameters=None):
    """Generate code for group comparison analysis."""
    parameters = parameters or getattr(intent, "parameters", {}) or {}
    target_field = getattr(intent, "target_field", None)
    group_by = getattr(intent, "group_by", []) or []

    # Enhanced logic to handle A1C comparison queries that weren't properly parsed
    raw_query = (
        getattr(intent, "raw_query", "").lower() if hasattr(intent, "raw_query") else ""
    )

    # If we're missing target_field or group_by, try to infer from the query
    if not (group_by and target_field):
        # Check if this is an A1C comparison query
        if "a1c" in raw_query and any(
            bp_term in raw_query
            for bp_term in ["blood pressure", "bp", "systolic", "diastolic"]
        ):
            # This is likely "Compare blood pressure values for patients with high or normal A1C"
            if "systolic" in raw_query or "sbp" in raw_query:
                target_field = "sbp"
            elif "diastolic" in raw_query or "dbp" in raw_query:
                target_field = "dbp"
            else:
                # Default to systolic blood pressure
                target_field = "sbp"

            # Create A1C categories for grouping
            group_by = ["a1c_category"]

            # Generate code with A1C categorization using clinical reference ranges
            code = (
                "# Auto-generated comparison analysis with A1C categorization\n"
                "from db_query import query_dataframe\n"
                "from app.utils.metric_reference import get_range\n"
                "import pandas as pd\n\n"
                "# Get clinical reference ranges for A1C\n"
                "a1c_high_threshold = get_range('a1c', 'high')['min']  # Should be 6.5\n"
                "a1c_normal_threshold = get_range('a1c', 'normal')['max']  # Should be 5.6\n\n"
                "# SQL to get blood pressure and A1C data with categorization\n"
                'sql = f"""\n'
                "SELECT \n"
                "    v.patient_id,\n"
                f"    v.{target_field} as bp_value,\n"
                "    l.value as a1c_value,\n"
                "    CASE \n"
                "        WHEN l.value >= {{a1c_high_threshold}} THEN 'high_a1c'\n"
                "        WHEN l.value <= {{a1c_normal_threshold}} THEN 'normal_a1c'\n"
                "        ELSE 'pre_diabetes_a1c'\n"
                "    END as a1c_category\n"
                "FROM vitals v\n"
                "JOIN patients p ON p.id = v.patient_id\n"
                "JOIN lab_results l ON l.patient_id = v.patient_id AND (l.test_name = 'HbA1c' OR l.test_name = 'a1c')\n"
                "WHERE v.{} IS NOT NULL AND l.value IS NOT NULL\n".format(target_field)
                + '"""\n\n'
                "df = query_dataframe(sql)\n"
                "print('DEBUG: df.columns =', df.columns.tolist())\n"
                "if df.empty:\n"
                "    results = {'error': 'No data available for A1C comparison analysis'}\n"
                "else:\n"
                "    # Group by A1C category and compute statistics\n"
                "    comparison = df.groupby('a1c_category')['bp_value'].agg([\n"
                "        ('mean', 'mean'),\n"
                "        ('std', 'std'),\n"
                "        ('count', 'count')\n"
                "    ]).round(2)\n"
                "    \n"
                "    results = {\n"
                "        'comparison': comparison.to_dict(),\n"
                "        'summary': {\n"
                "            'high_a1c': {\n"
                f"                'avg_{target_field}': comparison.loc['high_a1c', 'mean'] if 'high_a1c' in comparison.index else None,\n"
                "                'count': comparison.loc['high_a1c', 'count'] if 'high_a1c' in comparison.index else 0\n"
                "            },\n"
                "            'normal_a1c': {\n"
                f"                'avg_{target_field}': comparison.loc['normal_a1c', 'mean'] if 'normal_a1c' in comparison.index else None,\n"
                "                'count': comparison.loc['normal_a1c', 'count'] if 'normal_a1c' in comparison.index else 0\n"
                "            }\n"
                "        }\n"
                "    }\n"
            )
            return code

    # Original logic for cases where target_field and group_by are properly set
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
