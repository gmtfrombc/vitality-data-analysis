You are a python expert finalizing the modular AI Data Assistant app.

**Background:**
    • The robust Data Analysis Assistant (`app/data_assistant.py`) is now live for all user workflows.
    • The clarification workflow currently uses a keyword-based trigger; you need to upgrade to intent/confidence-based logic.

Your Task: Implement Real Ambiguity Detection for Clarification

Goals:
    • Replace the keyword-based clarification trigger with logic that uses real intent parsing and confidence scoring.
    • The system should ask for clarification if the user's query is ambiguous or intent confidence is low.
    • Integrate this into the modular workflow and UI.

Instructions:
    • Review ambiguity/clarification logic in `recovery/data_assistant_legacy.py`, focusing on intent/confidence/missing slot handling.
    • Adapt/port the logic into `app/data_assistant.py` and supporting helpers.
    • Trigger clarification when intent is ambiguous or confidence is below threshold (e.g., <0.75).
    • Add clear print/logs to verify when clarification is triggered by real ambiguity.
    • Test with queries of varying clarity.
    • Do NOT trigger clarification for confident, unambiguous queries.

Definition of Done:
    • Real intent/confidence logic controls clarification workflow.
    • Ambiguity triggers clarification only when appropriate.
    • System tested and verified in UI.