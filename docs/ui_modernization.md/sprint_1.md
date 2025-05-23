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