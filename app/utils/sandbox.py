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
import threading as _threading
import multiprocessing
import time

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

# Max DataFrame size to prevent memory issues
MAX_DATAFRAME_SIZE = 1_000_000  # 1 million cells

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


def _execute_code_in_process(code: str, queue: multiprocessing.Queue):
    """Execute code in a separate process and put the result in a queue."""
    try:
        # Create a safe locals dictionary
        safe_locals: Dict[str, Any] = {}

        # Import handling
        import builtins as _builtins  # local alias to avoid shadowing

        # Save original import so we can restore later
        _orig_import = _builtins.__import__

        # Minimal whitelist – expand as legitimate needs grow
        _IMPORT_WHITELIST = {
            # Required packages
            "pandas",
            "pd",
            "numpy",
            "np",
            "db_query",
            "app",
            "__future__",
            "holoviews",
            "operation",  # Required for holoviews operation.element
            "data",  # Required for holoviews data module
            "dimension",  # Required for holoviews dimension module
            # Standard-lib utilities commonly used by snippets *and* Panel callbacks
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
            "asyncio",  # param/Panel internals may import while watcher fires
            "time",
            "typing",
            "sqlite3",  # allow db_query.query_dataframe
            "email",
            "tornado",  # Panel server runtime
            "config",  # panel.config import path during error handling
            # Allow lightweight visual helpers
            "hvplot",
            # Needed by traceback formatting when logging errors
            "unicodedata",
            # Needed by hvplot
            "textwrap",
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

        # Execute the code
        exec(code, _EXEC_GLOBALS, safe_locals)

        # Check for results
        if "results" not in safe_locals:
            queue.put(
                SandboxResult(
                    type="error", value="Snippet did not define a `results` variable"
                )
            )
            return

        raw = safe_locals["results"]

        # Size validation for DataFrames and Series to prevent memory issues
        try:
            import pandas as _pd

            if isinstance(raw, _pd.DataFrame):
                size = raw.shape[0] * raw.shape[1]
                if size > MAX_DATAFRAME_SIZE:
                    queue.put(
                        SandboxResult(
                            type="error",
                            value=f"DataFrame too large: {size} cells (max: {MAX_DATAFRAME_SIZE})",
                        )
                    )
                    return
            elif isinstance(raw, _pd.Series) and len(raw) > MAX_DATAFRAME_SIZE:
                queue.put(
                    SandboxResult(
                        type="error",
                        value=f"Series too large: {len(raw)} elements (max: {MAX_DATAFRAME_SIZE})",
                    )
                )
                return
        except Exception:
            pass  # If pandas isn't available, skip this check

        # Detect result type
        result_type = "object"
        meta: Dict[str, Any] = {}

        try:
            import pandas as _pd
            import holoviews as _hv
            from bokeh.document import Document  # noqa: F401 – just for isinstance test

            if raw is None:
                result_type = "object"
                raw = {}
            elif isinstance(raw, (int, float, complex)):
                result_type = "scalar"
            elif isinstance(raw, _pd.Series):
                result_type = "series"
                meta = {"length": len(raw)}
            elif isinstance(raw, _pd.DataFrame):
                result_type = "dataframe"
                meta = {"shape": raw.shape, "columns": list(raw.columns)}
            elif isinstance(raw, dict):
                result_type = "dict"
                meta = {"keys": list(raw.keys())}
            elif isinstance(raw, _hv.core.generators.Generator):
                result_type = "figure"
            else:
                result_type = "object"

        except Exception:
            # If imports fail, use basic type detection
            if raw is None:
                result_type = "object"
                raw = {}
            elif isinstance(raw, (int, float, complex)):
                result_type = "scalar"
            elif isinstance(raw, dict):
                result_type = "dict"
                meta = {"keys": list(raw.keys())}
            else:
                result_type = "object"

        # Put the result in the queue
        queue.put(SandboxResult(type=result_type, value=raw, meta=meta))

    except Exception as exc:
        # Send the error back through the queue
        queue.put(SandboxResult(type="error", value=str(exc)))
    finally:
        # Always restore the original import
        _builtins.__import__ = _orig_import


def run_user_code(code: str) -> SandboxResult:
    """Execute *code* safely and return a :class:`SandboxResult` envelope.

    This is the forward-looking API replacing :func:`run_snippet`.  The caller
    receives a consistent data structure independent of what the snippet
    produced, making UI rendering much simpler.
    """
    logger.info("Starting sandbox execution")

    # First try with thread-based timeout approach for compatibility
    if (
        _threading.current_thread() is _threading.main_thread()
        and hasattr(signal, "alarm")
        and os.name != "nt"
    ):
        return _run_with_signal_timeout(code)

    # Otherwise, use a more robust process-based approach
    return _run_with_process_timeout(code)


def _run_with_signal_timeout(code: str) -> SandboxResult:
    """Execute code with signal-based timeout (original implementation)."""
    safe_locals: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Import & network guard-rails
    # ------------------------------------------------------------------
    import builtins as _builtins  # local alias to avoid shadowing

    # Save original import so we can restore later
    _orig_import = _builtins.__import__

    # Minimal whitelist – expand as legitimate needs grow
    _IMPORT_WHITELIST = {
        # Required packages
        "pandas",
        "pd",
        "numpy",
        "np",
        "db_query",
        "app",
        "__future__",
        "holoviews",
        "operation",  # Required for holoviews operation.element
        "data",  # Required for holoviews data module
        "dimension",  # Required for holoviews dimension module
        # Standard-lib utilities commonly used by snippets *and* Panel callbacks
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
        "asyncio",  # param/Panel internals may import while watcher fires
        "time",
        "typing",
        "sqlite3",  # allow db_query.query_dataframe
        "email",
        "tornado",  # Panel server runtime
        "config",  # panel.config import path during error handling
        # Allow lightweight visual helpers
        "hvplot",
        # Needed by traceback formatting when logging errors
        "unicodedata",
        # Needed by hvplot
        "textwrap",
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
    _HAS_ALARM = (
        hasattr(signal, "alarm")
        and os.name != "nt"
        and _threading.current_thread() is _threading.main_thread()
    )

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

    # Check DataFrame size
    try:
        import pandas as _pd

        if isinstance(raw, _pd.DataFrame):
            size = raw.shape[0] * raw.shape[1]
            if size > MAX_DATAFRAME_SIZE:
                return SandboxResult(
                    type="error",
                    value=f"DataFrame too large: {size} cells (max: {MAX_DATAFRAME_SIZE})",
                )
        elif isinstance(raw, _pd.Series) and len(raw) > MAX_DATAFRAME_SIZE:
            return SandboxResult(
                type="error",
                value=f"Series too large: {len(raw)} elements (max: {MAX_DATAFRAME_SIZE})",
            )
    except Exception:
        pass  # If pandas isn't available, skip this check

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


def _run_with_process_timeout(code: str, timeout=5) -> SandboxResult:
    """Execute code in a separate process with timeout."""
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()

    # Create and start the process
    process = ctx.Process(target=_execute_code_in_process, args=(code, queue))

    try:
        # Start the process with a timeout
        process.start()

        # Wait for result with timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not queue.empty():
                # Get the result and return it
                result = queue.get(block=False)
                return result

            # Check if process has terminated
            if not process.is_alive():
                if not queue.empty():
                    return queue.get(block=False)
                return SandboxResult(
                    type="error", value="Process terminated without returning a result"
                )

            # Sleep a bit to avoid tight loop
            time.sleep(0.1)

        # If we're here, we hit the timeout
        logger.warning("Sandbox execution timed out after %s seconds", timeout)
        return SandboxResult(
            type="error", value=f"Execution timed out after {timeout} seconds"
        )

    except Exception as e:
        logger.error("Error in process-based execution: %s", e, exc_info=True)
        return SandboxResult(type="error", value=str(e))

    finally:
        # Make sure we clean up the process
        if process.is_alive():
            process.terminate()
            process.join(timeout=1.0)
            # Force kill if it didn't terminate
            if process.is_alive():
                os.kill(process.pid, 9)  # SIGKILL


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
