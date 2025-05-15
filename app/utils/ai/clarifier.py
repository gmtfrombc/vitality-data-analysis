"""
Clarifier Module

This module handles the generation of clarifying questions when user queries
are ambiguous or missing critical details. It includes functionality for:

- Detecting missing information in user queries or parsed intents
- Generating specific clarifying questions based on query context
- Providing fallback questions when online generation is unavailable
- Identifying ambiguous slots that need clarification from users
"""

import json
import logging
from typing import List

from .llm_interface import ask_llm, is_offline_mode

logger = logging.getLogger(__name__)


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

    # ---------------------------
    # Offline fast-path
    # ---------------------------
    if is_offline_mode():
        logger.info("Offline mode – returning default clarifying questions")
        return [
            "Could you clarify the time period of interest?",
            "Which patient subgroup (e.g., gender, age) should we focus on?",
            "Are you interested in averages, counts, or trends?",
            "Do you need any visualisations?",
        ]

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
        return questions[:4] if questions else []

    except Exception as exc:
        # Defensive – never raise; just provide sensible defaults.
        logger.error(
            "Error during clarifying-question generation: %s", exc, exc_info=True
        )
        return [
            "Would you like to filter the results by any specific criteria?",
            "Are you looking for a time-based analysis or current data?",
            "Would you like to compare different patient groups?",
            "Should the results include visualisations or just data?",
        ]
