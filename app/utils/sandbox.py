"""Utility to execute dynamically-generated analysis code in a controlled namespace.

The sandbox exposes a limited set of globals (pandas, numpy, db_query, metric registry)
and captures a variable named `results` created by the snippet.

Errors are caught and returned as a dict: {'error': '...'} so the calling code
can surface them gracefully in the UI.
"""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any, Dict, Literal
from dataclasses import dataclass, field
import os
import signal

import numpy as np
import pandas as pd

import db_query
from app.utils.metrics import get_metric, METRIC_REGISTRY

logger = logging.getLogger("sandbox")

# Immutable globals mapping to prevent snippet from mutating them
_READ_ONLY_GLOBALS = MappingProxyType(
    {
        "pd": pd,
        "np": np,
        "db_query": db_query,
        "get_metric": get_metric,
        "METRIC_REGISTRY": METRIC_REGISTRY,
        # Convenience aliases expected by some generated snippets
        "get_all_scores": db_query.get_all_scores,
        "get_all_vitals": db_query.get_all_vitals,
        "get_all_mental_health": db_query.get_all_mental_health,
        "get_all_patients": db_query.get_all_patients,
    }
)

# dict version for exec (exec requires mutable mapping)
_EXEC_GLOBALS = dict(_READ_ONLY_GLOBALS)

if not logger.handlers:
    import logging.handlers

    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "sandbox.log"), maxBytes=500_000, backupCount=2
    )
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)


@dataclass
class SandboxResult:
    """Unified envelope returned by sandbox execution.

    Attributes
    ----------
    type : str
        High-level category of *value* – e.g. ``scalar``, ``series``, ``dataframe``,
        ``dict``, ``figure``, ``error``.
    value : Any
        The actual object produced by the snippet or the error message.
    meta : dict, optional
        Auxiliary metadata (shape, dtype info, traceback, etc.).
    """

    type: Literal[
        "scalar",
        "series",
        "dataframe",
        "dict",
        "figure",
        "error",
        "object",
    ]
    value: Any
    meta: Dict[str, Any] = field(default_factory=dict)


def run_user_code(code: str) -> SandboxResult:
    """Execute *code* safely and return a :class:`SandboxResult` envelope.

    This is the forward-looking API replacing :func:`run_snippet`.  The caller
    receives a consistent data structure independent of what the snippet
    produced, making UI rendering much simpler.
    """
    safe_locals: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Import & network guard-rails
    # ------------------------------------------------------------------
    import builtins as _builtins  # local alias to avoid shadowing

    # Save original import so we can restore later
    _orig_import = _builtins.__import__

    # Minimal whitelist – expand as legitimate needs grow
    _IMPORT_WHITELIST = {
        "pandas",
        "numpy",
        "np",
        "pd",
        "db_query",
        "math",
        "json",
        "datetime",
        "os",
        "sys",
        "signal",
        "logging",
        "tokenize",
        "linecache",
        "inspect",
        "warnings",
        "_io",
        "re",
    }

    def _safe_import(
        name, globals=None, locals=None, fromlist=(), level=0
    ):  # noqa: ANN001, D401 – guard
        root_name = name.split(".")[0]
        if root_name not in _IMPORT_WHITELIST:
            raise ImportError(
                f"Import of '{name}' is blocked in sandbox (only {sorted(_IMPORT_WHITELIST)})"
            )
        return _orig_import(name, globals, locals, fromlist, level)

    # Patch builtins.__import__
    _builtins.__import__ = _safe_import  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Execution timeout (POSIX only)
    # ------------------------------------------------------------------
    _HAS_ALARM = hasattr(signal, "alarm") and os.name != "nt"

    if _HAS_ALARM:

        def _timeout_handler(_signum, _frame):  # noqa: ANN001 – inner handler
            raise TimeoutError("sandbox execution timed out")

        _old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(3)  # three-second cap

    try:
        exec(code, _EXEC_GLOBALS, safe_locals)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Sandbox execution failed: %s", exc, exc_info=True)
        return SandboxResult(type="error", value=str(exc))
    finally:
        # Always restore the original import to avoid polluting global state
        _builtins.__import__ = _orig_import
        if _HAS_ALARM:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, _old_handler)

    if "results" not in safe_locals:
        logger.warning(
            "Snippet did not set a `results` variable – returning error envelope"
        )
        return SandboxResult(
            type="error", value="Snippet did not define a `results` variable"
        )

    raw = safe_locals["results"]

    # Detect result type ---------------------------------------------------
    result_type: str
    meta: Dict[str, Any] = {}
    try:
        import pandas as _pd
        import holoviews as _hv
        from bokeh.document import Document  # noqa: F401 – just for isinstance test
    except Exception:  # pragma: no cover – optional deps may be missing during tests
        _pd = None  # type: ignore
        _hv = None  # type: ignore

    if raw is None:
        result_type = "object"
        raw = {}
    elif isinstance(raw, (int, float, complex)):
        result_type = "scalar"
    elif _pd is not None and isinstance(raw, _pd.Series):
        result_type = "series"
        meta = {"length": len(raw)}
    elif _pd is not None and isinstance(raw, _pd.DataFrame):
        result_type = "dataframe"
        meta = {"shape": raw.shape, "columns": list(raw.columns)}
    elif isinstance(raw, dict):
        result_type = "dict"
        meta = {"keys": list(raw.keys())}
    # type: ignore[attr-defined]
    elif _hv is not None and isinstance(raw, _hv.core.generators.Generator):
        result_type = "figure"
    else:
        result_type = "object"

    logger.info("Sandbox execution completed → %s", result_type)
    return SandboxResult(type=result_type, value=raw, meta=meta)


def run_snippet(code: str) -> Dict[str, Any]:
    """Backward-compat wrapper – will be removed in a future clean-up.

    Executes *code* via :func:`run_user_code` and returns only the raw
    ``value`` portion when the result type is not ``error``.
    """
    res = run_user_code(code)
    if res.type == "error":
        return {"error": res.value}
    # Keep legacy contract of dict or scalar; wrap non-dicts in themselves.
    return res.value  # type: ignore[return-value]
