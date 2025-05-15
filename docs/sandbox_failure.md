# Sandbox Failure – Deep Dive (2025-05-11)

This document captures the current state of unresolved sandbox failures so that a new assistant can resume debugging efficiently.

---
## 1. Symptoms

* `app/utils/sandbox.py` raises `NameError: results not defined` when fallback rule-engine attempts to access the variable after sandbox execution fails.
* Log excerpt:
  ```
  2025-05-10 19:23:01 WARNING Sandbox execution failed or returned empty/error; falling back to rule-engine
  2025-05-10 19:23:01 ERROR NameError: name 'results' is not defined
  ```
* Automated tests (`pytest`) currently pass, indicating the issue manifests only in full app run (`run.py`) with dynamic snippet execution.

## 2. Recent Changes

1. **Sandbox Import Hook**
   * Allowed relative imports (`root_name == ''`).
   * Added stub for `subprocess` imports used by hvplot/bokeh.
   * Added early exit for built-ins (`sys`, `types`, `inspect`) when creating stub (fixes recursion).

2. **UI Guard**
   * `_display_execution_results` now checks for `None` `intermediate_results` and exits gracefully.

3. **Snippet Guards**
   * Attempted to pre-declare `results = None` inside `try`/`except` wrapper added via `_add_sandbox_safety` but change did **not** propagate to runtime snippets (needs reinvestigation).

## 3. Hypothesis

* Dynamic code assembled in `ai_helper._generate_dynamic_code_for_complex_intent()` does **not** contain a global `results` declaration. When the `except` block executes after sandbox error, it references `results`, causing `NameError`.
* Tests pass because test snippets stub out imports or do not exercise fallback rule path.

## 4. Proposed Fix

1. When wrapping user-generated code for sandbox safety (function `_add_sandbox_safety` in `data_assistant.py`), declare:
   ```python
   results: dict | None = None
   ```
   before the `try:` so that both `except` and `finally` clauses have access.
2. Ensure rule-engine checks `if results is None or results.get('error'):` before computing fallback.
3. Add integration test: generate BP-vs-A1C query, force sandbox failure (e.g., inject banned import), assert rule-engine produces non-empty results.

## 5. Next Steps

* [ ] Update `_add_sandbox_safety` wrapper as described.
* [ ] Re-run `run.py`, confirm no `NameError`.
* [ ] Expand test coverage to include runtime safety wrapper.

---
**Contact:** @gmtfr 