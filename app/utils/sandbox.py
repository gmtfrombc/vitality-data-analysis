"""Utility to execute dynamically-generated analysis code in a controlled namespace.

The sandbox exposes a limited set of globals (pandas, numpy, db_query, metric registry)
and captures a variable named `results` created by the snippet.

Errors are caught and returned as a dict: {'error': '...'} so the calling code
can surface them gracefully in the UI.
"""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any, Dict

import numpy as np
import pandas as pd

import db_query
from app.utils.metrics import get_metric, METRIC_REGISTRY

logger = logging.getLogger("sandbox")

# Immutable globals mapping to prevent snippet from mutating them
_READ_ONLY_GLOBALS = MappingProxyType({
    "pd": pd,
    "np": np,
    "db_query": db_query,
    "get_metric": get_metric,
    "METRIC_REGISTRY": METRIC_REGISTRY,
    # Convenience aliases expected by some generated snippets
    "get_all_scores": db_query.get_all_scores,
    "get_all_vitals": db_query.get_all_vitals,
    "get_all_mental_health": db_query.get_all_mental_health,
})

# dict version for exec (exec requires mutable mapping)
_EXEC_GLOBALS = dict(_READ_ONLY_GLOBALS)

if not logger.handlers:
    import os
    import logging.handlers
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(os.path.join(
        log_dir, 'sandbox.log'), maxBytes=500_000, backupCount=2)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'))
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)


def run_snippet(code: str) -> Dict[str, Any]:
    """Execute *code* and return a dictionary of captured `results`.

    The snippet is expected to set a variable called `results`. If it does not,
    an empty dict is returned.
    """
    # Each run gets its own local namespace
    safe_locals: Dict[str, Any] = {}

    try:
        exec(code, _EXEC_GLOBALS, safe_locals)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Sandbox execution failed: %s", exc, exc_info=True)
        return {"error": str(exc)}

    results = safe_locals.get("results", {})
    logger.info("Sandbox execution completed. Returned type: %s",
                type(results).__name__)
    return results
