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
                              │  app/ai_helper.py      │         │
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
## 2. Module Map
| Path | Role | Key Classes / Functions |
|------|------|-------------------------|
| `run.py` | Entry-point; sets up Panel server. | `panel.serve(...)` |
| `app/pages/data_assistant.py` | Multi-step assistant UI & logic. | `DataAnalysisAssistant` |
| `app/pages/patient_view.py` | Patient-centric dashboard. | `PatientView` |
| `app/ai_helper.py` | Thin wrapper over OpenAI API (GPT-4). | `AIHelper`, `client.chat.completions` |
| `db_query.py` | SQLite helpers for vitals, labs, demographics. | `get_all_patients()`, etc. |
| `data/` | Static assets & `saved_questions.json`. | N/A |
| `tests/` | Pytest suite. | `test_*` files |

---
## 3. Execution Flow (Happy Path)
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
## 4. Data Layer
* **SQLite (`patient_data.db`)** – Single-file relational store for demographics, vitals, labs. Accessed read-only by default.
* **JSON (`data/saved_questions.json`)** – Persists user-saved queries; file-based now, slated for DB migration (see Roadmap WS-3).
* **In-Memory** – Pandas DataFrames used for transformations & joins.

---
## 5. External Services
| Service | Purpose | Notes |
|---------|---------|-------|
| OpenAI GPT-4 | NLP understanding, code & text generation | Key in `.env`; minimal prompt context passed (privacy). |
| (Future) CI | Lint, type-check, tests | GitHub Actions planned. |

---
## 6. Extension Points
* **New Analysis Types** – Add intent patterns & code-gen templates in `ai_helper.py`.
* **Additional Pages** – Place Panel pages in `app/pages/`; auto-served by Router.
* **Database Migrations** – Use Alembic scripts in `migrations/` (planned).
* **Theming/Branding** – Override Panel CSS/HTML templates under `app/theme/`.
* **Deterministic Code Templates** – Fast-path templates now cover:
  * Scalar aggregates: count, average, sum, min, max, **median**
  * Distributions: 10-bin histogram for numeric columns
  * **Trend** (new): average metric per calendar month
* **Sandbox Guard-Rails** – Import whitelist & network blockade; coverage gate ≥ 60 % enforced in CI.

---
## 7. Glossary
* **Intent** – Structured representation of a user's question (metric, filters, grouping).
* **Clarifying Question** – Follow-up asked when intent ambiguity detected.
* **Sandbox** – Ephemeral `exec` environment isolated from global scope.

---
_Last updated: <!-- AI/maintainer: timestamp on save -->_ 