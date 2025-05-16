# Refactor Plan: `ai_helper.py`

This checklist guides a safe, modular refactor of the `ai_helper.py` file, breaking it into testable components without affecting app functionality.

---

## ✅ Step 0 – Pre-check

* [x] Create a new branch (`git checkout -b refactor-ai-helper`)
* [x] Run full test suite and confirm green baseline (`pytest -q`)
* [x] Snapshot in Cursor (optional)

---

## 🔍 Step 1 – Identify Functional Sections

Mark or comment the major logic groups:

* [x] OpenAI/gpt call & retry logic
* [x] Prompt formatting (system & user templates)
* [x] Intent parsing and validation
* [x] Code generation and template rendering
* [x] Clarifying questions / missing slot detection
* [x] Narrative and result formatting

---

## 🧠 Step 2 – Create Target Modules

Place these inside `app/utils/ai/` or `app/ai_core/`:

* [x] `llm_interface.py` → GPT call, retry, token counting
* [x] `prompt_templates.py` → prompt scaffolds and prompt builders
* [x] `intent_parser.py` → parse\_intent\_json, validation, fallback
* [x] `code_generator.py` → render\_code\_template, sandbox prep
* [x] `clarifier.py` → get\_missing\_fields, build\_clarifying\_questions
* [x] `narrative_builder.py` → summarize\_results, format\_answer

---

## ✅ Step 3 – Move Code in Stages

* [x] Move prompt builders to `prompt_templates.py`
* [x] Move retry/wrapper logic to `llm_interface.py`
* [x] Move intent parsing to `intent_parser.py`
* [x] Move clarification slot logic to `clarifier.py`
* [x] Move result narrative functions to `narrative_builder.py`
* [x] Move template rendering to `code_generator.py`

---

## ✅ Step 4 – Wire Back to `ai_helper.py`

* [x] Replace inline code with imports from new modules
* [x] Ensure all reused functions are exported (`__all__ = [...]`)
* [x] Avoid changing behavior — just relocate

---

## ✅ Step 5 – Run Tests

* [x] Re-run existing unit and smoke tests
* [x] Add one new test per moved module (e.g., test render\_code\_template still works)
* [x] Manually verify at least one end-to-end GPT query

---

## ✅ Step 6 – Final Cleanup

* [x] Remove now-unused functions from `ai_helper.py`
* [x] Add module docstrings in each new file
* [x] Update changelog or ROADMAP\_CANVAS.md if tracked

---

## 🛡 Optional

* [ ] Document module roles in `docs/ai_architecture.md`
* [x] Push branch and open PR for review

---

## Outcome

`ai_helper.py` is slimmed down to a high-level coordinator. Each AI component lives in a clear, testable, focused module. Cursor performance improves and future devs understand the layout.

---

> *"Clean separation of function breeds stable iteration."*
