
# AI Assistant Migration Plan: Legacy to Modular Refactored Version

This plan describes a stepwise migration of "modern" features from the legacy Data Assistant code (data_assistant_legacy.py) into the new modular AI Assistant architecture (ai_assistant.py and ai_assistant_ui.py). The migration is broken into self-contained sprints, each designed to be completed in a single Cursor session. Each sprint includes a copy-paste prompt for the Cursor assistant to provide all necessary context.

---

# Migration Plan: Modernizing AI Data Assistant

This plan guides you (or Cursor/AI assistants) through modularizing and upgrading the AI Assistant app for SQL-based healthcare data analysis, moving all "modern" features from the current monolithic implementation into the new modular codebase.

---

## **Sprint Roadmap**

1. **Sprint 1:** Workflow and State Management  
2. **Sprint 2:** Clarification Workflow  
3. **Sprint 3:** Feedback Functionality  
4. **Sprint 4:** Import/Mock Data Handling  
5. **Sprint 5:** Saved Query CRUD Enhancements  
6. **Sprint 6:** Narrative/Tabular Results Toggle  
7. **Sprint 7:** Threading and UI Responsiveness  
8. **Sprint 8:** Final Polish and Regression

---

# SPRINT 1: Workflow and State Management

```
You are a python expert working on the modular refactor of a Panel-based AI Data Assistant app for SQL-based patient data analysis.

**Background:**
- The app has been modularized:
    • Core logic in `app/pages/ai_assistant.py` (AIAssistant class)
    • UI in `app/pages/ai_assistant_ui.py`
- You also have access to the previous, monolithic implementation (`recovery/data_assistant_legacy.py`). This legacy file contains the original (fully-featured) workflow logic.  
- **You should use the legacy file as a feature and workflow reference** only. Rebuild features in the new modular structure, adapting logic as needed for clarity, maintainability, and testability. Do not simply copy/paste old code—translate concepts, not lines.

**What has been done so far:**
- Modular core/UI classes scaffolded
- LLM integration and SQL generation stubs exist
- Saved queries, basic UI, and example queries are live

---

**Your Task:** Add Workflow State Management

**Goals:**
- Integrate a multi-stage workflow (input, clarification, codegen, execution, results) using `WorkflowState` and `WorkflowStages` (from `app/state.py`).
- Display workflow indicators in the UI, visually showing progress.
- Implement transitions and “Continue” handling for moving through workflow.

**Instructions:**
- Use `WorkflowState` as a property of `AIAssistant`.
- Update `AIAssistant` and UI so each stage (input, clarification, etc) is clear to the user.
- Add progress indicators to the UI using Panel widgets.
- Ensure all button presses and state changes are handled via events/watcher pattern.
- Use frequent `print` or logging statements at every workflow transition for debug visibility.
- **Pause frequently** to test: After every stage is implemented or modified, run the app, verify the UI, and confirm expected behavior before proceeding.
- Use the legacy file only to guide desired workflow and user experience—not for direct migration of code.

**Definition of Done:**
- UI displays workflow/progress for each stage.
- Workflow transitions correctly from stage to stage (manual advance via button is fine).
- Transitions/indicators are visible and tested in the UI.
- Pytests are green, ruff checks pass, and the app launches with the Data Assistant viewable.
```

---

# SPRINT 2: Clarification Workflow

**Prompt:**
```
You are a python expert continuing the modular refactor of the AI Data Assistant app.

**Background:**
- The app is modularized, with a multi-stage workflow and workflow indicators already in place.
- You have access to the legacy implementation (`recovery/data_assistant_legacy.py`), which contains the original clarification workflow and user experience logic.
- **Use the legacy file only to guide the design of the clarification feature.** You should rebuild/adapt, not copy/paste code, to fit the new modular and event-driven architecture.

**What has been done so far:**
    • Workflow state and progress indicators work across all major stages (input, clarification, codegen, etc)
    • Modular structure and event pattern established
    • Saved query and basic LLM SQL stubs live

---

**Your Task:** Implement Clarification Workflow

**Goals:**
    • Implement “clarification” logic: If a user query is ambiguous, present clarifying questions in the UI and collect responses before continuing.
    • Integrate clarification tightly with the workflow state—moving to the next stage only after clarification is complete.

**Instructions:**
    • Use the legacy code as a reference for when and how clarification is triggered, what kind of questions are asked, and how responses are handled.
    • Implement logic (adapted for the modular codebase) to detect ambiguity and trigger clarification—either by porting/adapting a ClarificationWorkflow helper, or by building a new one.
    • Present clarification questions using Panel widgets, collect user responses, and update state accordingly.
    • After clarification is answered, advance the workflow to the next stage.
    • Add detailed logging/print statements for when clarification is triggered, displayed, and completed.
    • **Pause frequently**: Test the ambiguous and non-ambiguous query flows in the UI after implementing each branch to ensure correctness.
    • Do not copy-paste from legacy—focus on clarity, modularity, and maintainability.

**Definition of Done:**
    • Clarifying questions are shown for ambiguous queries.
    • User can answer, and workflow advances to the next stage.
    • Flow is tested in the UI for both ambiguous and non-ambiguous queries.
    • Pytests and ruff checks pass, and the app launches with the updated clarification workflow visible in the Data Assistant UI.
```

---

# SPRINT 3: Feedback Functionality

**Prompt:**

```
You are a python expert continuing the modularization of the AI Data Assistant app.

**Background:**
- The app is now modular, with a workflow engine, clarification stage, and saved query logic in place.
- You have access to the legacy implementation (`recovery/data_assistant_legacy.py`), which includes the original feedback UI/logic.
- Use the legacy file only to inform the *user experience and data flow*—rebuild/modernize as needed for the modular design.

**What has been done so far:**
    • Modular workflow with stage transitions and indicators are in place
    • Clarification workflow is implemented and tested
    • Saved query CRUD and basic result rendering are working

---

**Your Task:** Add Feedback Functionality

**Goals:**
    • Implement thumbs up/down feedback controls after results are displayed.
    • Store feedback in SQLite using `insert_feedback` from `app/utils/feedback_db.py`.
    • Acknowledge feedback submission in the UI with a “Thank you” or similar message.

**Instructions:**
    • Refer to the legacy file for feedback UX patterns, but rebuild for modular architecture.
    • Add feedback buttons (👍👎) to the result panel—make them accessible and intuitive.
    • Wire feedback submission to `insert_feedback`, including relevant context (query, result, timestamp, etc).
    • Show a brief thank you or confirmation message after feedback is received.
    • Add print/logging for every feedback action (button click, DB write, UI update).
    • **Pause frequently**: Test both thumbs up and down, and confirm the feedback is persisted in the database.
    • Ensure modular code organization and event-driven logic throughout.
    • Do **not** copy-paste from legacy—translate to clean, modern modular code.

**Definition of Done:**
    • Feedback can be submitted and is persisted to SQLite.
    • UI shows a thank you/confirmation message after feedback.
    • Both up and down flows tested and confirmed in UI and database.
    • Pytests and ruff checks pass, and app launches with visible feedback UI.

---

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
```

---


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

---

# SPRINT 6: Narrative/Tabular Results Toggle

**Prompt:**

```
You are a python expert finalizing the modular AI Data Assistant app.

**Background:**
- The app is now modular, and you have implemented and tested the following: workflow, clarification, feedback, import/reset, and robust saved query CRUD.
- You also have access to the legacy file (`recovery/data_assistant_legacy.py`), which contains a working implementation of the results narrative/tabular toggle logic. Use this as a reference if needed for behavior and UI expectations. Do not copy the code verbatim

**What has been done so far:**
    • Modular workflow, clarification, feedback, import/reset, and saved query enhancements are all done and tested.

---

**Your Task:** Add Narrative/Tabular Results Toggle

**Goals:**
    • Allow users to toggle between narrative (explanation) and tabular (data) views of results in the Results panel.
    • UI should update instantly based on user toggle, and both views should be clearly accessible.

**Instructions:**
    • Review the toggle logic (e.g., checkbox, switch, show/hide logic) in the legacy assistant (`recovery/data_assistant_legacy.py`) to understand UX and technical approach.
    • Implement a toggle widget (such as a Panel Checkbox or Toggle) in the modular UI.
    • On toggle, dynamically switch between showing the narrative interpretation and the raw/tabular data.
    • Ensure the panel updates in real time for different result types (e.g., scalar, dataframe, string).
    • Test both paths (narrative and tabular) for all common analysis results.
    • Add logs or print statements to verify which view is currently active during development.

**Definition of Done:**
    • The Results panel contains a user-accessible toggle for narrative/tabular views.
    • Both views are accessible, update correctly, and render as expected.
    • UI/UX matches or exceeds the behavior in the legacy version.
```

---

# SPRINT 7: Threading and UI Responsiveness

**Prompt:**
```
You are a python expert optimizing the modular AI Data Assistant app for user experience and performance.

**Background:**
- All core features—multi-stage workflow, clarification, feedback, full CRUD for saved queries, data import/reset, and result view toggling—are present and tested.
- You have access to the legacy implementation (`recovery/data_assistant_legacy.py`) for reference on background processing patterns and user messaging. This is for reference if needed, do not copy the code verbatim

**What has been done so far:**
    • All main features (workflow, clarification, feedback, CRUD, import, toggles) are present and tested.

---

**Your Task:** Ensure Threading/UI Responsiveness

**Goals:**
    • Refactor all long-running tasks (data import, mock reset, LLM queries, analysis execution) to run in background threads, NOT the main/UI thread.
    • The UI must remain responsive (never freezes or blocks) during these operations.
    • Progress indicators (“busy”, “thinking”, etc) and status messages must inform the user of ongoing work.

**Instructions:**
    • Use Python’s `threading.Thread` for any time-consuming operation (review legacy logic for proven threading approaches).
    • Make sure any UI update from a thread is done using Panel’s safe callback patterns.
    • Thoroughly test each task (LLM query, DB import, mock reset, analysis execution) under simulated slowness—UI must remain interactive.
    • Add or improve progress indicators/messages for every threaded operation.
    • Pause and test after integrating each threaded task to confirm correct behavior and user feedback.

**Definition of Done:**
    • All long-running operations execute off the main/UI thread.
    • UI never freezes during any operation.
    • Progress/status indicators are shown and clearly reflect ongoing work.
    • All paths tested for responsiveness and user experience.
```

---

# SPRINT 8: Final Polish and Regression

**Prompt:**
```

You are a python expert completing the modular refactor of the AI Data Assistant app.

**Background:**
- All features have been incrementally migrated and modularized, and have passed sprint-level testing.
- You have access to the previous monolithic implementation (`recovery/data_assistant_legacy.py`) for reference when comparing feature completeness and user experience.

**What has been done so far:**
    • All features are migrated, modularized, and tested sprint-by-sprint.

---

**Your Task:** Polish, Test, and Validate

**Goals:**
    • Ensure the modular version matches or exceeds the functionality and usability of the original legacy implementation.
    • Add or update regression tests as necessary for all migrated features.
    • Identify and fix any remaining bugs or rough edges.
    • Thoroughly document the migration results and any remaining caveats.

**Instructions:**
    • Compare the modular implementation to the legacy (`recovery/data_assistant_legacy.py`) for feature and UX completeness.
    • Test every feature in the modular app: workflow, clarification, CRUD, feedback, data import/reset, results toggling, threading/responsiveness, etc.
    • Write or update automated tests as needed for new or changed logic.
    • Document any discovered edge cases, limitations, or migration gaps.
    • Pause after each major validation/checkpoint to confirm correctness before moving on.

**Definition of Done:**
    • All migrated features are regression-tested and working in the modular app.
    • UI/UX meets or exceeds the original implementation.
    • Migration is fully documented and ready for handoff or ongoing maintenance.
```    
    
## GENERAL INSTRUCTIONS FOR EACH SPRINT

- Always pause and run the app after any significant change.
- Ensure frequent testing and visible progress before moving to the next sprint.
- Mark the sprint complete when the definition of done (above) is fully satisfied.

---
