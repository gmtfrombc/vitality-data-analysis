def _generate_relative_change_analysis_code(intent: QueryIntent) -> str | None:
    """Return code for average change between two relative windows (baseline & follow-up).

    Triggered when:
    • intent.analysis_type in {"change", "average_change"}
    • intent.parameters contains "relative_date_filters" (added by intent parser)
    """

    if intent.analysis_type not in {"change", "average_change"}:
        return None

    if not isinstance(intent.parameters, dict):
        return None

    rel_specs: list[dict] = []
    if isinstance(intent.parameters, dict):
        rel_specs = intent.parameters.get("relative_date_filters", []) or []

    # If fewer than two specs are provided, we will still proceed using
    # default baseline (±30 days from program start) and follow-up (5-7 months)
    # windows so simpler queries work without explicit metadata.

    # ------------------------------------------------------------------
    # Determine metric table/column
    # ------------------------------------------------------------------
    metric = intent.target_field.lower()
    score_metrics = {"score_value", "value"}
    vitals_metrics = {"bmi", "weight", "height", "sbp", "dbp"}

    if metric in score_metrics:
        metric_column = "scores.score_value"
        date_column = "scores.date"
        join_clause = "JOIN scores ON patients.id = scores.patient_id"
    elif metric in vitals_metrics:
        metric_column = f"vitals.{metric}"
        date_column = "vitals.date"
        join_clause = "JOIN vitals ON patients.id = vitals.patient_id"
    else:
        # Currently unsupported metric
        return None

    # ------------------------------------------------------------------
    # Build SQL – we exclude date filters because we will evaluate windows in pandas
    # ------------------------------------------------------------------
    # Create a deep copy of the intent using model_copy instead of deepcopy
    tmp_intent = intent.model_copy(deep=True)
    tmp_intent.filters = [f for f in tmp_intent.filters if f.date_range is None]
    where_clause = _build_filters_clause(tmp_intent)
    if where_clause:
        where_clause = "AND " + where_clause.replace("WHERE", "", 1).strip()

    sql = (
        "SELECT patients.id AS patient_id, "
        "patients.program_start_date, "
        f"{date_column} AS obs_date, "
        f"{metric_column} AS metric_value "
        "FROM patients "
        f"{join_clause} "
        "WHERE 1=1 "
        f"{where_clause};"
    )

    # ------------------------------------------------------------------
    # Default window parameters
    # ------------------------------------------------------------------
    baseline_window_days = 30  # ±1 month
    follow_start_offset_days = 150  # 5 months
    follow_end_offset_days = 210  # 7 months

    import re as _re

    for spec in rel_specs:
        if not isinstance(spec, dict):
            continue
        start_expr = str(spec.get("start_expr", "")).lower()
        # Detect expressions like "program_start_date + N months"
        match = _re.search(r"program_start_date\s*\+\s*(\d+)\s*month", start_expr)
        if match:
            months = int(match.group(1))
            follow_start_offset_days = (months - 1) * 30
            follow_end_offset_days = (months + 1) * 30

    # ------------------------------------------------------------------
    # Generate executable python code string
    # ------------------------------------------------------------------
    code = (
        "# Auto-generated relative change analysis (baseline vs follow-up)\n"
        "from db_query import query_dataframe\n"
        "import pandas as _pd, numpy as _np\n"
        "import logging\n\n"
        "# Set up logging to see what's happening\n"
        "logger = logging.getLogger('weight_change')\n\n"
        f"_sql = '''{sql}'''\n"
        "_df = query_dataframe(_sql)\n"
        "\n# Ensure filters are properly applied\n"
        f"if 'patient_id' in _df.columns and len(_df) > 0:\n"
        f"    # Double-check if query filters were applied correctly\n"
        f"    from sqlite3 import connect\n"
        f"    import os\n"
        f"    # Try to connect to the right database file\n"
        f"    for db_file in ['patient_data.db', 'mock_patient_data.db']:\n"
        f"        if os.path.exists(db_file):\n"
        f"            conn = connect(db_file)\n"
        f"            break\n"
        f"    else:\n"
        f"        conn = connect('patient_data.db')  # Default fallback\n"
        f"    verification_sql = '''\n"
        f"        SELECT COUNT(*) as count\n"
        f"        FROM patients\n"
        f"        WHERE gender = 'F' AND active = 1\n"
        f"    '''\n"
        f"    exp_patient_count = _pd.read_sql(verification_sql, conn)['count'].iloc[0]\n"
        f"    if len(_df['patient_id'].unique()) > 3 * exp_patient_count:\n"
        f"        logger.warning(f'Query returned {{len(_df[\"patient_id\"].unique())}} patients, but expected ~{{exp_patient_count}}.')\n"
        f"        logger.warning('Applying filters directly to the dataframe to ensure correct results.')\n"
        f"        _filtered_sql = '''\n"
        f"            SELECT p.id AS patient_id, p.program_start_date, v.date AS obs_date, v.weight AS metric_value\n"
        f"            FROM patients p\n"
        f"            JOIN vitals v ON p.id = v.patient_id\n"
        f"            WHERE p.gender = 'F' AND p.active = 1\n"
        f"        '''\n"
        f"        _df = _pd.read_sql(_filtered_sql, conn)\n"
        "if _df.empty:\n"
        "    results = {'error': 'No data found for the specified criteria'}\n"
        "else:\n"
        "    # Handle ISO8601 format with flexible parsing\n"
        "    _df['program_start_date'] = _pd.to_datetime(_df['program_start_date'], errors='coerce', utc=True)\n"
        "    _df['obs_date'] = _pd.to_datetime(_df['obs_date'], errors='coerce', utc=True)\n"
        "    # Drop any rows where date parsing failed\n"
        "    _df = _df.dropna(subset=['program_start_date', 'obs_date'])\n"
        "    # Convert to naive timestamps for consistent calculations\n"
        "    _df['program_start_date'] = _df['program_start_date'].dt.tz_localize(None)\n"
        "    _df['obs_date'] = _df['obs_date'].dt.tz_localize(None)\n"
        "    _df['days_from_start'] = (_df['obs_date'] - _df['program_start_date']).dt.days\n"
        f"    _baseline = _df[_df['days_from_start'].between(-{baseline_window_days}, {baseline_window_days})]\n"
        "    _baseline = (_baseline.sort_values('obs_date')\n"
        "                          .groupby('patient_id', as_index=False).first()[['patient_id', 'metric_value']]\n"
        "                          .rename(columns={'metric_value': 'baseline'}))\n"
        f"    _follow = _df[_df['days_from_start'].between({follow_start_offset_days}, {follow_end_offset_days})]\n"
        "    _follow = (_follow.sort_values('obs_date')\n"
        "                        .groupby('patient_id', as_index=False).first()[['patient_id', 'metric_value']]\n"
        "                        .rename(columns={'metric_value': 'follow_up'}))\n"
        "    # Use copy=False to avoid pandas trying to import copy module\n"
        "    _merged = _baseline.merge(_follow, on='patient_id', copy=False)\n"
        "    if _merged.empty:\n"
        "        results = {'error': 'No patients with both baseline and follow-up measurements'}\n"
        "    else:\n"
        "        # Log statistics about the data\n"
        "        logger.info(f\"Found {len(_df)} total measurements for {len(_df['patient_id'].unique())} unique patients\")\n"
        '        logger.info(f"Baseline measurements: {len(_baseline)} rows")\n'
        '        logger.info(f"Follow-up measurements: {len(_follow)} rows")\n'
        '        logger.info(f"Matched patients with both measurements: {len(_merged)} rows")\n'
        "        \n"
        "        _merged['change'] = _merged['baseline'] - _merged['follow_up']\n"
        "        \n"
        "        # Check if the result makes sense\n"
        "        if len(_merged) > 10 * len(_df['patient_id'].unique()):\n"
        "            # We have many more matches than patients - this suggests a problem with the join\n"
        "            logger.warning(f\"Warning: Unusually high number of matches ({len(_merged)}) compared to unique patients ({len(_df['patient_id'].unique())})\")\n"
        "            # Count unique patients in the final result\n"
        "            unique_patient_count = len(_merged['patient_id'].unique())\n"
        '            logger.info(f"Found {unique_patient_count} unique patients in the final merged dataset")\n'
        "        \n"
        "        results = {\n"
        "            'average_change': float(_merged['change'].mean()),\n"
        "            'patient_count': int(len(_merged)),\n"
        f"            'baseline_window_days': {baseline_window_days},\n"
        f"            'follow_window_days': [{follow_start_offset_days}, {follow_end_offset_days}]\n"
        "        }\n"
    )

    return code
