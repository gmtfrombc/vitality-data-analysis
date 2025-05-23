# ------------------------------------------------------------------
# Code Generator Orchestrator (modular, no cross-imports)
# ------------------------------------------------------------------
import logging
from app.utils.ai.codegen import (
    generate_basic_code,
    generate_trend,
    generate_top_n,
    generate_histogram,
    generate_comparison_code,
    generate_relative_change_code,
    generate_correlation_code,
    generate_fallback_code,
)

logger = logging.getLogger(__name__)


def generate_code(intent, parameters=None):
    """Route to the correct codegen module based on intent.analysis_type.

    Raises:
        LLMError: If LLM/codegen fails
        AppError: For general application errors
    """
    analysis_type = getattr(intent, "analysis_type", None)
    if analysis_type in {
        "count",
        "sum",
        "average",
        "min",
        "max",
        "median",
        "variance",
        "std_dev",
    }:
        return generate_basic_code(intent, parameters)
    if analysis_type == "trend":
        return generate_trend(intent, parameters)
    if analysis_type == "top_n":
        return generate_top_n(intent, parameters)
    if analysis_type in ("histogram", "distribution"):
        return generate_histogram(intent, parameters)
    if analysis_type == "comparison":
        return generate_comparison_code(intent, parameters)
    if analysis_type in {"change", "percent_change", "relative_change"}:
        return generate_relative_change_code(intent, parameters)
    if analysis_type == "correlation":
        return generate_correlation_code(intent, parameters)
    return generate_fallback_code(getattr(intent, "raw_query", ""), intent)
