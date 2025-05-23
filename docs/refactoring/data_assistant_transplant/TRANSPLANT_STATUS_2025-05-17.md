# Data Assistant Refactor & Transplant — Mid‑Project Status *(2025‑05‑17)*

## 1 · Purpose  
Transform the original **monolithic** `data_assistant.py` into a modular, testable, and maintainable assistant while keeping production green at every step.

## 2 · Strategy (“Lots of Small, Obvious Moves”)

| Pillar | Principle |
| ------ | --------- |
| **Incremental Transplants** | Move one logical block at a time, run `pytest && ruff` after each. |
| **Layered Modules** | UI ↔ State ↔ Engine ↔ Helpers ↔ Utils — no cross‑layer shortcuts. |
| **Legacy for Reference Only** | `recovery/data_assistant_legacy.py` stays read‑only until all sprints complete. |
| **Documentation & Checklist** | Update `/docs/refactoring/REFACTORING_CHECKLIST.md` after every transplant. |
| **Green Tests Gate** | Tests must stay green; failing tests block merges. |

## 3 · Current Module Structure  

```
app/
├── data_assistant.py               # Thin orchestrator (shrinking)
├── ui.py                           # Panel widgets & rendering
├── state.py                        # Workflow state machine
├── engine.py                       # NL→Intent→Code→Execution
├── analysis_helpers.py             # Formatting & visualization utils
├── query_refinement/
│   ├── __init__.py                 # canonicalize_field, fuzzy_match
│   ├── clarifier.py                # low‑confidence & ambiguity helpers
│   └── clarification_workflow.py   # ← to be created next sprint
└── utils/
    └── intent_clarification.py     # Slot‑based clarifier singleton
recovery/
└── data_assistant_legacy.py        # read‑only reference
```

## 4 · Sprint Roadmap & Status  

| Sprint | Scope | Status | Notes |
| ------ | ----- | ------ | ----- |
| **S‑0 Baseline** | Tag pre‑refactor, tests green | ✅ complete |
| **S‑1 Reference Ranges** | Centralize clinical thresholds | ✅ complete |
| **S‑2 Threshold Query** | Add threshold detection & tests | ✅ complete |
| **S‑3 Active/Inactive Filter** | Clarify patient filters | ✅ complete |
| **S‑4 BMI Unit Logic** | kg ↔ lbs handling | ✅ complete |
| **S‑5 Query Refinement** | Synonyms, ambiguity, clarification | 🟢 in‑progress – `_is_low_confidence_intent` & `_is_truly_ambiguous_query` migrated; tests green |
| **S‑6 Clarification Workflow** | Extract Q&A logic to new module | 🔜 next |
| **S‑7 UI/Engine Boundary Polish** | Remove last business logic from UI | 🕒 queued |
| **S‑8 Final Cleanup** | Delete wrapper, archive legacy, docs | 🕒 queued |

## 5 · Risks & Mitigations  

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| UI/business coupling reappears | Refactor stalls or breaks UI | Keep logic in `clarification_workflow.py`; UI pure render |
| Backup files edited by mistake | Divergent features, dead code | Move `ai_helper_backup.py` & `ai_helper_original.py` to `/legacy` |
| Stage logic duplication | Inconsistent flow | Route transitions through `WorkflowState` |
| Clarification regressions | Wrong query flow | Expand smoke tests for multi‑round clarification |
| Dev context overload | Merge conflicts | Continue micro‑commits + checklist updates |

## 6 · Next Immediate Actions  

1. **Create `app/query_refinement/clarification_workflow.py`.**  
2. **Move Q&A logic from `data_assistant.py`** (display & processing).  
3. **Use `WorkflowState.transition_to()` — no direct `current_stage` edits.**  
4. **Archive backup files to `/legacy/`.**  
5. **Add tests for multi‑round clarification.**  
6. **Update checklists & docs.**

## 7 · Overall Health

| Metric | Status |
| ------ | ------ |
| **Tests** | ✅ 349 / 349 passing |
| **Lint (ruff)** | ✅ no errors |
| **Monolith LOC** | 📉 steadily shrinking |
| **Team Confidence** | High — green pipeline at each commit |
