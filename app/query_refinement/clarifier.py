from ..utils.ai.llm_interface import ask_llm, is_offline_mode
from typing import List
from app.utils.intent_clarification import clarifier
from app.utils.query_intent import QueryIntent, compute_intent_confidence
import logging
import json


def is_truly_ambiguous_query(intent):
    """
    Return True only when the query is genuinely ambiguous and requires clarification.
    """
    import logging

    logger = logging.getLogger(__name__)

    from app.config import OFFLINE_MODE

    if OFFLINE_MODE:
        return False

    # Treat clear parsing failures as ambiguous; mocks/unknown objects as NOT ambiguous
    # Treat clear parsing failures as ambiguous
    if intent is None:
        logger.warning("is_truly_ambiguous_query: None intent → True (ambiguous)")
        return True

    if isinstance(intent, dict):
        return True

    # ------------------------------------------------------------------
    # Low‑confidence detection – only for real QueryIntent objects
    # ------------------------------------------------------------------
    from app.utils.query_intent import QueryIntent

    if isinstance(intent, QueryIntent):
        # helper defined later in this file
        if _is_low_confidence_intent(intent):
            return True
    else:
        # Generic object (e.g., MagicMock) – robust pseudo-intent check
        if hasattr(intent, "analysis_type") and hasattr(intent, "target_field"):
            # Treat like a pseudo‑QueryIntent
            analysis_type = str(getattr(intent, "analysis_type", "unknown")).lower()
            target_field = str(getattr(intent, "target_field", "unknown")).lower()

            # If either key part is unknown ⇒ ambiguous
            if analysis_type == "unknown" or target_field == "unknown":
                return True

            # Otherwise treat as a well‑formed intent ⇒ NOT ambiguous
            return False
        else:
            # Object lacks intent‑like attributes ⇒ we cannot be confident → ambiguous
            logger.debug(
                "is_truly_ambiguous_query: Object (%s) lacks intent fields → True (ambiguous)",
                type(intent).__name__,
            )
            return True
    # Check if the query is entirely unclear about what metric or analysis is wanted
    if (
        getattr(intent, "analysis_type", "unknown") == "unknown"
        and getattr(intent, "target_field", "unknown") == "unknown"
    ):
        return True

    # Check if multiple interpretations are equally valid (critical ambiguity)
    raw_query = getattr(intent, "raw_query", "")
    if not raw_query:
        return False

    raw_query = raw_query.lower()

    ambiguous_patterns = [
        "compare",
        "between",
        "versus",
        "vs",
        "which",
        "better",
        "best",
        "correlation",
        "relationship between",
    ]
    has_ambiguous_pattern = any(pattern in raw_query for pattern in ambiguous_patterns)
    has_unclear_targets = (
        not getattr(intent, "additional_fields", None)
        and getattr(intent, "target_field", "unknown") == "unknown"
    )
    if has_ambiguous_pattern and has_unclear_targets:
        return True

    # Default to not asking questions
    return False


"""
Clarifier Module

This module handles the generation of clarifying questions when user queries
are ambiguous or missing critical details. It includes functionality for:

- Detecting missing information in user queries or parsed intents
- Generating specific clarifying questions based on query context
- Providing fallback questions when online generation is unavailable
- Identifying ambiguous slots that need clarification from users
"""


logger = logging.getLogger(__name__)


def _is_low_confidence_intent(intent):
    """Return True when *intent* should trigger clarification (low confidence)."""

    from app.config import OFFLINE_MODE

    # In offline/test mode we skip clarification to keep smoke tests fast.
    if OFFLINE_MODE:
        return False

    # If parsing failed → low confidence
    if isinstance(intent, dict):
        return True

    assert isinstance(intent, QueryIntent)

    # Prepare raw_query_str robustly (ensuring string, not None)
    raw_query_str = getattr(intent, "raw_query", "") or ""

    # Use the slot-based clarifier to determine if we need clarification
    needs_clarification, _ = clarifier.get_specific_clarification(intent, raw_query_str)

    if needs_clarification:
        logger.debug("Slot-based clarifier identified missing information")
        return True

    # Fallback to the confidence score for cases not caught by the slot-based clarifier
    confidence = compute_intent_confidence(intent, raw_query_str)

    # Threshold grey zone: below 0.75 ask clarification
    if confidence < 0.75:
        logger.debug(
            "Low confidence %.2f for intent – requesting clarification", confidence
        )
        return True

    return False


def generate_clarifying_questions(query: str, model: str = "gpt-4") -> List[str]:
    """Return up to four clarifying questions for a user *query*.

    The function utilises the LLM in online mode and falls back to a static set
    of generic questions when running offline (no ``OPENAI_API_KEY``).

    Parameters
    ----------
    query:
        The original natural-language question from the user.
    model:
        Model to forward to :pyfunc:`app.utils.ai.llm_interface.ask_llm`.

    Returns
    -------
    list[str]
        A list with a maximum of four focused clarifying questions.
    """

    logger.info("Generating clarifying questions for query: %s", query)

    # Check if we should include a question about active/inactive patients
    query_lower = query.lower()
    should_ask_active = True

    # If the query explicitly mentions active or inactive, we don't need to ask
    if (
        "active" in query_lower
        or "inactive" in query_lower
        or "all patient" in query_lower
    ):
        should_ask_active = False

    # ---------------------------
    # Offline fast-path
    # ---------------------------
    if is_offline_mode():
        logger.info("Offline mode – returning default clarifying questions")
        default_questions = [
            "Could you clarify the time period of interest?",
            "Which patient subgroup (e.g., gender, age) should we focus on?",
            "Are you interested in averages, counts, or trends?",
        ]

        # Conditionally add active/inactive question
        if should_ask_active:
            default_questions.insert(
                0, "Should we include inactive patients, or only use active patients?"
            )

        return default_questions[:4]  # Return at most 4 questions

    # ---------------------------
    # Build system prompt
    # ---------------------------
    system_prompt = """
You are an expert healthcare data analyst. Based on the user's query about patient data, generate 4 relevant clarifying questions that would help provide a more precise analysis.

The questions should address potential ambiguities about:
- Time period or date ranges
- Specific patient demographics or subgroups
- Inclusion/exclusion criteria
- Preferred metrics or visualisation types
"""

    # Conditionally add active/inactive prompt
    if should_ask_active:
        system_prompt += """
IMPORTANT: Always include a question about whether to include inactive patients or just active patients, unless the query explicitly specifies this.
"""

    system_prompt += """
Return the questions as a *JSON array* of strings – no markdown fencing.
"""

    try:
        raw_response = ask_llm(
            system_prompt, query, model=model, temperature=0.7, max_tokens=500
        )

        # Some models wrap the JSON in markdown fences – strip if necessary.
        if "```json" in raw_response:
            raw_response = raw_response.split("```json")[1].split("```", 1)[0].strip()
        elif "```" in raw_response:
            raw_response = raw_response.split("```", 1)[1].split("```", 1)[0].strip()

        # Attempt strict JSON parse first.
        try:
            questions = json.loads(raw_response)
            # The model might wrap it in an object: {"questions": [...] }
            if isinstance(questions, dict) and "questions" in questions:
                questions = questions["questions"]
        except Exception as exc:
            logger.warning(
                "Failed to parse clarifier JSON – falling back to heuristic parse: %s",
                exc,
            )
            questions = []
            for line in raw_response.splitlines():
                stripped = line.strip()
                if stripped.startswith(('"', "'")):
                    questions.append(stripped.strip("'\", "))
                elif stripped.startswith("-"):
                    questions.append(stripped.lstrip("- "))

        logger.info("Generated %d clarifying questions", len(questions))

        # Ensure we have a question about active/inactive patients if needed
        if should_ask_active and questions:
            has_active_question = False
            for q in questions:
                if "active" in q.lower() and "patient" in q.lower():
                    has_active_question = True
                    break

            if not has_active_question:
                # Insert active question as the second question (after most important one)
                active_question = (
                    "Should we include inactive patients, or only use active patients?"
                )
                if len(questions) > 1:
                    questions.insert(1, active_question)
                else:
                    questions.append(active_question)

        return questions[:4] if questions else []

    except Exception as exc:
        # Defensive – never raise; just provide sensible defaults.
        logger.error(
            "Error during clarifying-question generation: %s", exc, exc_info=True
        )
        default_questions = [
            "Would you like to filter the results by any specific criteria?",
            "Are you looking for a time-based analysis or current data?",
            "Would you like to compare different patient groups?",
        ]

        # Conditionally add active/inactive question
        if should_ask_active:
            default_questions.insert(
                0, "Should we include inactive patients, or only use active patients?"
            )

        return default_questions[:4]  # Return at most 4 questions
