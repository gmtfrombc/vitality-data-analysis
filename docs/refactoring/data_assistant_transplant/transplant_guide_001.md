# 🧬 AI Task: Transplant Post-Split Features from Legacy Assistant to Modular Codebase

## ✅ Context
- You've already analyzed the legacy `data_assistant_legacy.py` and identified ~12 high-value features added after modularization.
- These features were never migrated into the new modular layout in `app/data_assistant.py` and related utils.
- The modular version is working well and has 100% test pass rate — we must **preserve that stability**.

## 🔄 Task
For each of the features you identified in the previous step:
1. Isolate the legacy code implementing it (with line numbers if possible).
2. Identify where this logic *should* go in the modular structure (which file, which function).
3. Create **one transplant at a time**.
4. After each transplant:
   - Re-run the test suite
   - Report whether any tests fail
   - Pause and wait for confirmation before continuing

## 🚧 Caution
- Do NOT overwrite existing modular logic.
- Do NOT re-introduce legacy architectural patterns (e.g., giant helper methods).
- Keep code modular, testable, and in line with how other helpers are structured.

## 🧪 Transplant Order (suggested)
1. Threshold Query Analysis
2. Active/Inactive Logic
3. BMI Unit Handling
4. Reference Ranges
5. Query Refinement
6. Correlation Analysis
7. Ambiguous Query Detection
8. Sandbox Safety
9. AI Indicator UI
10. Assumptions Section
11. Feedback Enhancements
12. Record Export Logic
