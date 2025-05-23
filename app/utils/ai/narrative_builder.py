"""
Narrative Builder Module

This module handles the generation of natural language interpretations
and narratives from analysis results. It includes functionality for:

- Converting raw analysis results into human-readable text
- Highlighting key insights and patterns in the data
- Providing contextual medical interpretations of metrics
- Formatting different types of results for consistent presentation
- Handling fallbacks for offline operation
"""

import json
import logging
from typing import Any, List, Optional

import pandas as pd

from .llm_interface import ask_llm, is_offline_mode

logger = logging.getLogger(__name__)

__all__ = ["interpret_results"]


def simplify_for_json(obj: Any):
    """Convert complex objects to a JSON-serialisable structure.

    The helper gracefully degrades when encountering non-serialisable objects
    by returning their string representation.  This logic mirrors the original
    implementation in ``ai_helper.py`` to ensure backwards compatibility.
    """

    import numpy as np

    if isinstance(obj, dict):
        return {k: simplify_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [simplify_for_json(item) for item in obj]
    if isinstance(obj, (pd.DataFrame, pd.Series)):
        try:
            if isinstance(obj, pd.DataFrame):
                return {
                    "type": "DataFrame",
                    "data": obj.head(5).to_dict(orient="records"),
                    "shape": obj.shape,
                }
            return {
                "type": "Series",
                "data": obj.head(5).to_dict(),
                "length": len(obj),
            }
        except Exception:
            return str(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist() if obj.size < 100 else f"Array of shape {obj.shape}"
    if isinstance(obj, (np.integer, np.floating)):
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    if hasattr(obj, "to_dict"):
        try:
            return obj.to_dict()
        except Exception:
            return str(obj)
    if hasattr(obj, "__dict__"):
        try:
            return {
                k: simplify_for_json(v)
                for k, v in obj.__dict__.items()
                if not k.startswith("_")
            }
        except Exception:
            return str(obj)
    try:
        json.dumps(obj)
        return obj  # Already serialisable
    except Exception:
        return str(obj)


def interpret_results(
    query: str,
    results: Any,
    visualisations: Optional[List[str]] = None,
    model: str = "gpt-4",
) -> str:
    """Return a concise, clinician-friendly narrative for *results*.

    Mirrors the original behaviour from ``AIHelper.interpret_results`` while
    being library-agnostic.  The function is safe to call in offline mode – it
    will provide a deterministic fallback instead of raising.
    """

    logger.info("Interpreting analysis results for query: %s", query)

    # ---------------------------
    # Offline fast-path
    # ---------------------------
    if is_offline_mode():
        logger.info("Offline mode – returning simplified interpretation")
        return "Here is a concise summary of the analysis results based on the provided data."

    system_prompt = """
You are an expert healthcare data analyst and medical professional. Based on the patient data analysis results, provide a clear, insightful interpretation that:

1. Directly answers the user's original question
2. Highlights key findings and patterns in the data
3. Provides relevant clinical context or healthcare implications
4. Suggests potential follow-up analyses if appropriate

Respond in 3-5 sentences, focusing on the most important insights.
"""

    # Prepare visualisation notes
    viz_notes = ""
    if visualisations:
        viz_notes += "\n\nVisualisations include:\n"
        viz_notes += "\n".join(f"{idx+1}. {v}" for idx, v in enumerate(visualisations))

    try:
        payload = (
            f"Original question: {query}\n\n"
            f"Analysis results: {json.dumps(simplify_for_json(results))}{viz_notes}"
        )

        response = ask_llm(
            system_prompt, payload, model=model, temperature=0.4, max_tokens=500
        )
        interpretation = response.strip()
        logger.info("Successfully generated result interpretation")
        return interpretation

    except Exception as exc:
        logger.error("Error interpreting results: %s", exc, exc_info=True)
        return f"Analysis shows the requested data for your query: '{query}'. The results include relevant metrics based on the available patient data."
