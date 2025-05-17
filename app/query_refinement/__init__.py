"""
Query‑refinement helpers – migrated from legacy ai_helper.py.
"""

# ---------------------------------------------------------------------
# Metric‑name canonicalisation helpers  (moved from legacy ai_helper.py)
# ---------------------------------------------------------------------

import re
from app.utils.query_intent import QueryIntent

# Alias map is module‑level so other helpers can import it too
ALIASES: dict[str, str] = {
    "test_date": "date",
    "score": "score_value",
    "scorevalue": "score_value",
    "phq9_score": "score_value",
    "phq_score": "score_value",
    "sex": "gender",
    "patient": "patient_id",
    "assessment_type": "assessment_type",
    "score_type": "score_type",
    "activity_status": "active",
    "status": "active",
    "date": "program_start_date",
}


def canonicalize_metric_name(intent: QueryIntent) -> str:
    """
    Return a normalised / canonical metric name for the given intent.

    Handles:
      • alias mapping (ALIASES)
      • snake‑case conversion
      • special cases (phq9_change, active_patients)
    """
    raw_name = intent.target_field.lower()
    metric = re.sub(r"[^a-z0-9]+", "_", raw_name).strip("_")

    # phq9 change heuristic
    if metric.startswith("phq") and "change" in (
        metric + intent.analysis_type + str(intent.parameters).lower()
    ):
        metric = "phq9_change"

    # Count‑active heuristic
    if (
        intent.analysis_type == "count"
        and metric in {"patient", "patients", "patient_id"}
        and any(
            f.field.lower() in {"active", "status", "activity_status"}
            for f in intent.filters
        )
    ):
        metric = "active_patients"

    return ALIASES.get(metric, metric)
