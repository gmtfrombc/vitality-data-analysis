# AI Helper Refactor – Progress Snapshot (2025-05-15)

## Context
We are midway through Step 4 of the refactor plan: wiring the new helper
modules back into the original `app/ai_helper.py` while keeping the full
test-suite green.

Work completed so far:
1. **Clarifying questions** now delegated to `app.utils.ai.clarifier`.
2. **Narrative / result interpretation** delegated to
   `app.utils.ai.narrative_builder`.
3. **LLM call wrapper** (`_ask_llm`) delegates to
   `app.utils.ai.llm_interface.ask_llm`.
4. **Intent parsing** is handed off via a *thin wrapper* that calls
   `app.utils.ai.intent_parser.get_query_intent` while preserving the unit-test
   convention of monkey-patching `AIHelper._ask_llm`.
5. `QueryIntent` model extended with an optional `raw_query` field
   (excluded from JSON dumps, so existing golden files are unchanged).

## Current Failing Tests
* `pytest` yields **7 failures** and then appears to hang.
* The hang is caused by our thin wrapper temporarily forcing
  `intent_parser.is_offline_mode()` to `True`; the parser therefore returns a
  *fallback* intent lacking many expected fields, which trips dozens of
  assertions and causes some parametrised tests to retry indefinitely.

## What Was Tried
* Introduced a response-cache in the patched `ask_llm` to satisfy retry logic
  inside the parser (works fine).
* Added and later removed a monkey-patch of `is_offline_mode`.
  – When it was forced **False** the tests made real API calls and hung.  
  – When it was forced **True** (current state) the parser exits too early and
    produces minimal intents, failing 7 tests.
  A clean run should *not* patch this flag at all; unit tests already stub
  `_ask_llm`, so no external network is invoked.

## Recommended Next Steps
1. **Delete the monkey-patch on `is_offline_mode`** inside
   `AIHelper.get_query_intent` (both the assignment and restore lines).
   After that, run `pytest -q`; expected result is **all green** or a small
   number of legitimate failures that can be tackled individually.
2. Once tests are green, continue Step 4 by
   • exporting public helpers in each new module (`__all__`).  
   • removing legacy code that is now dead in `ai_helper.py`.
3. Proceed to Step 5 of the checklist (add a smoke test for one moved module).

---
_Snapshot created automatically by previous assistant to pass context to the
next session._ 