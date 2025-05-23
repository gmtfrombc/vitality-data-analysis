You are a python expert finalizing the modular AI Data Assistant app.

**Background:**
- The app now renders the robust, full-featured Data Analysis Assistant (`app/data_assistant.py`) as the main Data Assistant UI.
- Workflow, clarification, feedback, import/reset, and robust saved query CRUD are all tested and live.
- You also have access to the legacy implementation (`recovery/data_assistant_legacy.py`) for reference—do NOT copy code verbatim.

**Your Task:** Add Narrative/Tabular Results Toggle

**Goals:**
    • Allow users to toggle between narrative (explanation) and tabular (data) views in the Results panel.
    • UI should update instantly based on user toggle, and both views should be clearly accessible.

**Instructions:**
    • Review the toggle logic in the legacy assistant (`recovery/data_assistant_legacy.py`) for behavior and UI expectations.
    • Implement the toggle (checkbox/switch) in `app/data_assistant.py` and its UI helpers.
    • On toggle, update the panel in real time to show either narrative or tabular data.
    • Test both paths (narrative and tabular) for all result types.
    • Add logs or print statements to verify view switching during development.

**Definition of Done:**
    • Results panel has a working toggle for narrative/tabular views.
    • Both views render and update correctly.
    • UI/UX matches or exceeds the legacy experience.