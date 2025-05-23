# SPRINT 5: Saved Query CRUD Enhancements

**Prompt:**
```
You are a python expert upgrading the modular AI Data Assistant app.

**Background:**
- The app is now modular, with staged workflow, clarification, feedback, import, and mock DB reset features implemented and tested.
- You have access to the legacy assistant (`recovery/data_assistant_legacy.py`), which provides a full-featured reference implementation for saved query CRUD (Create, Read, Update, Delete) operations. Use this as a design pattern and feature parity reference only—do not copy code verbatim.

**What has been done so far:**
    • Modular workflow, clarification, feedback, and import/mock DB reset are all implemented and tested.

---

**Your Task:** Enhance Saved Query CRUD

**Goals:**
    • Ensure users can save, load, update, and delete named queries from the UI.
    • UI should reflect the current state (enable/disable buttons as appropriate, show loading/error/success status).
    • Saved queries should persist and update in real time (live reload after CRUD actions).

**Instructions:**
    • Review saved query handling in `recovery/data_assistant_legacy.py` to capture any advanced CRUD logic, edge case handling, or UI state management patterns.
    • Port or rebuild the following into the modular code:
        - Robust save, load, update, and delete logic
        - UI state management for button states (only enable load/delete when a query is selected, etc.)
        - Error handling and status messaging
    • Pause and test frequently:
        - Saving a new query and confirming it persists
        - Loading a query into the editor/input field
        - Updating a saved query (name/query)
        - Deleting a query and confirming the list/UI updates
        - Checking button enable/disable state matches app state
    • Ensure all changes pass pytests and ruff checks, and app launches with a fully functioning saved queries UI.
    • Use clear log/print statements for each CRUD action.

**Definition of Done:**
    • Saved query panel supports all CRUD operations as in the legacy version.
    • UI/UX is robust, error-tolerant, and gives clear user feedback.
    • All actions are persisted (to file or DB as appropriate), and reflected in the UI in real time.
```