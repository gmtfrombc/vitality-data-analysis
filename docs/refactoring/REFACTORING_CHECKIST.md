# Refactor Plan: `data_assistant.py`

This checklist guides the safe refactor of a large assistant module into focused, testable components without breaking app functionality.

---

## ✅ Step 0 – Safety First

* [ ] Create a new branch (`git checkout -b refactor-data-assistant`)
* [ ] Run full test suite and confirm green baseline
* [ ] Snapshot in Cursor (optional)

---

## 🔍 Step 1 – Identify Logical Sections

* [ ] Mark sections in `data_assistant.py` by purpose:

  * [ ] UI widgets and layout (Panel components)
  * [ ] Query handling: parsing, codegen, execution
  * [ ] Plotting and result formatting
  * [ ] Feedback / logging
  * [ ] Stage management and state transitions

---

## 🧠 Step 2 – Create Target Modules

* [ ] `app/ui.py` → layout & controls (widgets, buttons, user input)
* [ ] `app/engine.py` → intent → code → result pipeline
* [ ] `app/analysis_helpers.py` → pandas, hvplot transforms
* [ ] `app/state.py` → current stage, transition logic
* [ ] `app/data_assistant.py` → refactored coordinator using above

---

## ✂️ Step 3 – Move Code Gradually

* [ ] Move helper functions to `analysis_helpers.py`
* [ ] Move sandbox logic and query dispatch to `engine.py`
* [ ] Move display/plot formatting to `analysis_helpers.py`
* [ ] Move all Panel widgets and UI layout to `ui.py`
* [ ] Move stage logic (`STAGE_INPUT`, `STAGE_CLARIFY`, etc.) to `state.py`

---

## 🔗 Step 4 – Wire & Test

* [ ] Import new modules into `data_assistant.py`
* [ ] Replace moved logic with calls to new modules
* [ ] Run existing tests (fix imports if needed)
* [ ] Add 1–2 new smoke tests for end-to-end workflow

---

## 🧪 Step 5 – Sanity Check

* [ ] App runs with expected behavior
* [ ] Clarifications, feedback, charts all work
* [ ] Run `pytest -q` and check for regressions

---

## 🧹 Step 6 – Clean Up

* [ ] Delete unused functions from `data_assistant.py`
* [ ] Update `README_data_assistant.md` if it exists
* [ ] Commit all changes (`git commit -am "Refactor data_assistant.py into 5 modules"`)

---

## 🚀 Optional

* [ ] Document module responsibilities in `docs/`
* [ ] Add inline docstrings for each new module
* [ ] Push to GitHub and open PR for code review

---

## Outcome

`data_assistant.py` shrinks to <300 lines and becomes an orchestrator.
Each concern is isolated into testable, reusable modules.
Cursor and model cost improves due to smaller context diffs.

---

> *“Big refactors should feel like lots of small, obvious moves.”*
