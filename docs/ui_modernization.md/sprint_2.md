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