"""
Intent Parser Module

This module handles parsing, validating, and normalizing query intents
from LLM responses. It ensures consistent field names and handles
various post-processing steps to ensure clean intents.
"""

import re
import logging
from datetime import datetime
import calendar

from app.utils.query_intent import (
    parse_intent_json,
    QueryIntent,
    Filter,
    DateRange,
    normalise_intent_fields,
    inject_condition_filters_from_query,
    get_canonical_condition,
)
from app.utils.ai.llm_interface import ask_llm, is_offline_mode
from app.utils.ai.prompt_templates import (
    INTENT_CLASSIFICATION_PROMPT,
    INTENT_STRICTER_SUFFIX,
)
from app.utils.intent_clarification import clarifier as _clarifier

# Configure logging
logger = logging.getLogger("intent_parser")

__all__ = ["get_query_intent", "QueryIntent", "Filter", "DateRange"]


def get_query_intent(query: str) -> QueryIntent:
    """
    Analyze the query to determine the user's intent and required analysis.
    Returns a structured response with analysis type and parameters.

    Args:
        query: The user query string to analyze

    Returns:
        A validated QueryIntent object with the parsed intent
    """
    logger.info(f"Getting intent for query: {query}")

    # Offline fast-path -------------------------------------------------
    if is_offline_mode():
        logger.info("Offline mode – returning fallback intent")
        return _clarifier.create_fallback_intent(query)

    max_attempts = 2
    last_err = None

    for attempt in range(max_attempts):
        try:
            prompt = (
                INTENT_CLASSIFICATION_PROMPT
                if attempt == 0
                else INTENT_CLASSIFICATION_PROMPT + INTENT_STRICTER_SUFFIX
            )
            raw_reply = ask_llm(prompt, query)

            # Remove any accidental markdown fences
            if "```" in raw_reply:
                raw_reply = raw_reply.split("```", maxsplit=2)[1].strip()

            # Validate & convert
            intent = parse_intent_json(raw_reply)

            # Canonicalise field names & synonyms
            normalise_intent_fields(intent)

            # Add the raw query for reference
            intent.raw_query = (
                query  # This is important for contextual operations later
            )

            # Apply post-processing heuristics
            apply_post_processing_heuristics(intent, query)

            # ------------------------------------------------------------------
            #  NEW: Inject condition filters directly from raw user text
            # ------------------------------------------------------------------
            inject_condition_filters_from_query(intent, query)
            # ------------------------------------------------------------------

            # Remove redundant non-clinical filters that duplicate condition terms (e.g., score_type = "anxiety")
            cleaned_filters = []
            for _f in intent.filters:
                if _f.field.lower() in {
                    "score_type",
                    "assessment_type",
                } and isinstance(_f.value, str):
                    canon_cond = get_canonical_condition(_f.value)
                    # Remove the filter only when the *value* itself is an exact canonical match
                    # (e.g., "anxiety", "obesity"), NOT when it merely appears as a substring
                    if canon_cond and canon_cond in {
                        _f.value.lower(),
                        _f.value.lower().replace(" ", "_"),
                    }:
                        # Skip – this non-clinical field is duplicating a condition term
                        continue
                cleaned_filters.append(_f)

            intent.filters = cleaned_filters

            return intent
        except Exception as exc:
            last_err = exc
            logger.warning("Intent parse failure on attempt %s – %s", attempt + 1, exc)

    # All attempts failed – return fallback structure with error message
    logger.error("All intent parse attempts failed: %s", last_err)
    return QueryIntent(
        analysis_type="unknown",
        target_field="unknown",
        filters=[],
        conditions=[],
        parameters={"error": str(last_err) if last_err else "unknown"},
        additional_fields=[],
        group_by=[],
        time_range=None,
    )


def apply_post_processing_heuristics(intent: QueryIntent, query: str) -> None:
    """
    Apply various heuristics to refine and correct the intent.

    Args:
        intent: The intent to refine
        query: The original query string
    """
    q_lower = query.lower()

    # Heuristic 1: Add implicit active filter
    mentions_active_patients = (
        "active patient" in q_lower or "active patients" in q_lower
    )
    has_active_filter = any(
        f.field.lower() in {"active", "status", "activity_status"}
        for f in intent.filters
    )
    if (
        intent.analysis_type == "count"
        and mentions_active_patients
        and not has_active_filter
    ):
        logger.debug("Injecting missing active=1 filter based on query text heuristic")
        intent.filters.append(Filter(field="active", value="active"))

    # Heuristic 2: Map "total" phrasing to count
    if "total" in q_lower and intent.analysis_type not in {"count", "sum"}:
        logger.debug("Overriding analysis_type to 'count' based on 'total' keyword")
        intent.analysis_type = "count"

    # Heuristic 3: Map weight-loss phrasing to change analysis
    if any(
        kw in q_lower
        for kw in [
            "weight loss",
            "lost weight",
            "weight change",
            "gain weight",
            "gained weight",
        ]
    ) and intent.analysis_type in {"average", "unknown", "count"}:
        logger.debug(
            "Overriding analysis_type to 'change' based on weight-loss wording"
        )
        intent.analysis_type = "change"

    # Heuristic 4: Add date range based on month mentions
    if not intent.has_date_filter():
        # Simple date heuristic for "in [month]" or "during [month]"
        month_pattern = r"(?:in|during)\s+(january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+(\d{4}))?\.?"
        month_match = re.search(month_pattern, q_lower)

        if month_match:
            month_name = month_match.group(1)
            year = (
                int(month_match.group(2))
                if month_match.group(2)
                else datetime.now().year
            )

            month_map = {
                "january": 1,
                "february": 2,
                "march": 3,
                "april": 4,
                "may": 5,
                "june": 6,
                "july": 7,
                "august": 8,
                "september": 9,
                "october": 10,
                "november": 11,
                "december": 12,
            }

            month_num = month_map.get(month_name.lower())
            if month_num:
                # Create a date range for the full month
                _, last_day = calendar.monthrange(year, month_num)

                start_date = f"{year}-{month_num:02d}-01"
                end_date = f"{year}-{month_num:02d}-{last_day:02d}"

                intent.time_range = DateRange(start_date=start_date, end_date=end_date)
                logger.debug(
                    f"Added implicit date range for month: {start_date} to {end_date}"
                )
