
# SPRINT 4: Import/Mock Data Handling

**Prompt:**

```
You are a python expert working on a modular AI Data Assistant app.

**Background:**
- The app is now modular with a staged workflow, clarification, feedback, and saved queries all in place.
- You have access to the previous monolithic implementation (`recovery/data_assistant_legacy.py`), which includes working examples for data import and mock patient reset features.
- Use the legacy code *as a reference for workflow, UX, and helper usage only*—do not copy directly.

**What has been done so far:**
    • Modular workflow and clarification flows are working
    • Feedback functionality is present
    • Saved queries and result panels are working

---

**Your Task:** Add Data Import and Mock Reset

**Goals:**
    • Enable JSON data import using the ETL pipeline (`etl/json_ingest.py`).
    • Provide a UI option to reset/mock the DB for developer testing (removes mock/demo patients).

**Instructions:**
    • Study the relevant logic in the legacy file for UX patterns and data flow.
    • Add modular UI components (file input, buttons) for both import and mock reset.
    • Ensure that both operations (import, reset) run in background threads to prevent UI freezing.
    • Implement progress or status messages so the user always knows the operation status.
    • Add clear print/log statements for each stage (button click, thread start, result, error).
    • **Pause and test frequently:** 
        • Test importing new JSON data and confirm via UI and DB.
        • Test resetting mock DB and confirm in UI/data.
        • Test both for success and error paths (bad file, interrupted reset, etc.).
    • Code should be clean, modular, and event-driven (no copy-paste from legacy).

**Definition of Done:**
    • Data import and mock reset features are fully available and working in the UI.
    • Both run in background threads and UI never freezes during operation.
    • User receives clear status messages for every operation.
    • Pytests and ruff checks pass, and app launches with visible import/reset UI.