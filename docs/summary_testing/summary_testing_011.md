# Summary Testing Session 011 – 2025-05-11

## Goal
Eliminate sandbox execution failures that forced every analysis snippet to fall back to the deterministic rule-engine whenever plotting libraries were referenced.

## What was done
1. Implemented lightweight **in-sandbox stubs** for:
   - `holoviews` (`Div`, `VLine`, `Store`, `extension`, etc.)
   - `hvplot` and `hvplot.pandas` (with dummy `hvplot` accessor on DataFrame / Series).
2. Added identical stubs to both sandbox execution paths:
   - `_execute_code_in_process` (process-based timeout)
   - `_run_with_signal_timeout` (signal-based timeout)
3. Updated `app/utils/plots.py` & `app/pages/data_assistant.py` to guard optional holoviews imports.
4. All unit tests green, live app now executes sandbox for plotting queries (e.g. *BMI distribution*) without fallback.

## Remaining issue
### Data-schema mismatch in AI-generated SQL
- Query: **"Compare blood pressure values for patients with high vs. normal A1C"**
- Generated SQL selects `vitals.score_type` which does **not** exist.
- SQLite raises `no such column: vitals.score_type`, sandbox wraps the error, caller logs warning and reverts to rule-engine.

### Recommendations
1. **Schema-aware validation** before execution: parse generated SQL, check referenced columns against `PRAGMA table_info`, and rewrite or redirect to pandas pipeline when invalid.
2. **Prompt / template tweak** in `ai.generate_analysis_code` so BP vs A1C uses the correct tables/columns (`lab_results` or `scores`) instead of `vitals`.
3. Add regression test: ensure sandbox completes for this query once fixed.

---
Owner: @gmtfr  │  Status: 📌 open for next work-stream 