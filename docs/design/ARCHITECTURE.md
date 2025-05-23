# VP Data Analysis – Architecture Reference

> **Audience:** Contributors, AI coding assistants, & architects  
> **Goal:** Provide a stable, high-level map of code modules, runtime data flow, and extension points.  
> **Status:** Living document – update when structural changes land.

---
## 1. Bird's-Eye View
```
┌────────────┐      HTTP/WebSocket      ┌──────────────────┐
│  Browser   │ ───────────────────────▶ │  Panel Server    │
└────────────┘                          │  (run.py)        │
                                         │    │            │
                                         │    ▼            │
                                         │  Pages &        │
                                         │  Components     │
                                         └────┬────────────┘
                                              │ param events
                                              ▼
                                     ┌──────────────────┐
                                     │ Data Assistant   │
                                     │ (data_assistant) │
                                     └────┬─────────────┘
                                              │
                         ┌────────queries/clarifications────────┐
                                              │                  │
                                              ▼                  │
                              ┌────────────────────────┐         │
                              │  AI Helper (GPT-4)     │         │
                              │  app/utils/ai_helper.py │         │
                              └──────────┬─────────────┘         │
                                         │ code / narrative       │
                                         ▼                       │
                              ┌────────────────────────┐         │
                              │   Exec Sandbox         │◀────────┘
                              │ (pandas, hvplot)       │
                              └──────────┬─────────────┘
                                         │ results / figs
                                         ▼
                          ┌──────────────────────────────┐
                          │   UI Render (HoloViews,      │
                          │   Panel widgets)             │
                          └──────────────────────────────┘
```

---
## 2. Core Modules & Responsibilities
| Path | Role | Key Classes / Functions |
|------|------|-------------------------|
| `run.py` | Entry-point; sets up Panel server. | `panel.serve(...)` |
| `app/data_assistant.py` | Multi-step assistant UI & logic. | `DataAnalysisAssistant` |
| `app/engine.py` | Core analysis pipeline (query → intent → code → results). | `AnalysisEngine` |
| `app/ui.py` | UI widgets, layout, and state. | `UIComponents` |
| `app/utils/ai_helper.py` | Orchestrates LLM, codegen, and narrative. | `AIHelper` |
| `app/utils/ai/llm_interface.py` | LLM API interface, error handling, config. | `ask_llm`, `is_offline_mode` |
| `app/utils/ai/codegen/` | Modular code generation logic. | `generate_basic_code`, ... |
| `app/utils/ai/intent_parser.py` | Intent parsing and normalization. | `get_query_intent` |
| `app/utils/sandbox.py` | Safe code execution environment. | `run_snippet` |
| `app/db_query.py` | SQLite helpers for vitals, labs, demographics. | `get_all_patients()`, ... |
| `app/config.py` | Centralized config/env var loading. | `OPENAI_API_KEY`, ... |
| `tests/` | Pytest suite, fixtures, mocks. | `test_*` files |
| `archive/` | Quarantined legacy/compatibility code. | `ai_helper_old.py`, ... |

---
## 3. Dependency Flow & Design Patterns

- **Dependency Injection (DI):**
  - All major modules (AIHelper, LLM interface, DB, config) are injected via constructors or parameters, not imported directly.
  - Enables test isolation, mocking, and flexible configuration.
- **Orchestrator Pattern:**
  - `AIHelper` and `AnalysisEngine` coordinate submodules (intent parsing, codegen, LLM, sandbox) via clear interfaces.
- **Centralized Error Handling:**
  - Shared exception types in `app/errors.py`.
  - All LLM/DB/config errors are raised and handled at module boundaries.
- **Test Isolation:**
  - All tests use fixtures/mocks; no monkeypatching of private helpers.
  - LLM and DB calls are stubbed or injected for offline/CI runs.

**Dependency Graph (Textual):**
```
UIComponents (app/ui.py)
   │
   ▼
DataAnalysisAssistant (app/data_assistant.py)
   │
   ▼
AnalysisEngine (app/engine.py)
   │         │         │
   │         │         ├──> AIHelper (app/utils/ai_helper.py)
   │         │         │         │
   │         │         │         ├──> LLM Interface (app/utils/ai/llm_interface.py)
   │         │         │         └──> Codegen (app/utils/ai/codegen/)
   │         │         │         └──> Sandbox (app/utils/sandbox.py)
   │         │         └──> DB Query (app/db_query.py)
   │         └──> Config (app/config.py)
   └──> Config (app/config.py)
```

---
## 4. Execution Flow (Happy Path)
1. **User Input** – User enters a natural-language question in Data Assistant.
2. **Clarification (optional)** – Assistant asks follow-up questions (AI-generated).
3. **Intent Classification** – `AIHelper.get_query_intent()` returns a structured intent JSON.
4. **Code Generation** – `AIHelper.generate_analysis_code()` produces Python snippets tailored to intent & data schema.
5. **Sandbox Execution** – Generated code is executed inside a controlled namespace (`exec`).
6. **Intermediate Results** – Numeric stats & pandas DataFrames stored on `assistant.intermediate_results`.
7. **Visualization** – hvplot/HoloViews objects rendered into Panel panes.
8. **Final Explanation** – AI interprets numeric results → natural-language summary.

> Error handling: exceptions propagate to UI with friendly markdown; logs stored via Python `logging`.

---
## 5. Data Layer
* **SQLite (`patient_data.db`)** – Single-file relational store for demographics, vitals, labs. Accessed read-only by default.
* **JSON (`data/saved_questions.json`)** – Persists user-saved queries; file-based now, slated for DB migration (see Roadmap WS-3).
* **In-Memory** – Pandas DataFrames used for transformations & joins.

---
## 6. External Services
| Service | Purpose | Notes |
|---------|---------|-------|
| OpenAI GPT-4 | NLP understanding, code & text generation | Key in `.env`; minimal prompt context passed (privacy). |
| (Future) CI | Lint, type-check, tests | GitHub Actions planned. |

---
## 7. Extension Points
* **New Analysis Types** – Add intent patterns & code-gen templates in `app/utils/ai/codegen/`.
* **Additional Pages** – Place Panel pages in `app/pages/`; auto-served by Router.
* **Database Migrations** – Use SQL scripts in `migrations/` (see also `app/utils/db_migrations.py`).
* **Theming/Branding** – Override Panel CSS/HTML templates under `app/theme/`.
* **Deterministic Code Templates** – Fast-path templates now cover:
  * Scalar aggregates: count, average, sum, min, max, **median**
  * Distributions: 10-bin histogram for numeric columns
  * **Trend** (new): average metric per calendar month
* **Sandbox Guard-Rails** – Import whitelist & network blockade; coverage gate ≥ 60 % enforced in CI.

---
## 8. Glossary
* **Intent** – Structured representation of a user's question (metric, filters, grouping).
* **Clarifying Question** – Follow-up asked when intent ambiguity detected.
* **Sandbox** – Ephemeral `exec` environment isolated from global scope.
* **Dependency Injection (DI)** – Passing dependencies (LLM, DB, config) as arguments, not globals.
* **Orchestrator** – Module/class that coordinates submodules via interfaces, not direct imports.

---
_Last updated: <!-- AI/maintainer: timestamp on save -->_ 