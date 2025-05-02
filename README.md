# VP Data Analysis – README

**Purpose:** A notebook-style web application that helps healthcare teams explore patient data with a hybrid AI + rules engine. Powered by Panel, HoloViews, SQLite, and OpenAI GPT-4.

---
## 🚀 Vision (Why?)
* Give non-technical stakeholders instant, trustworthy insights on patient outcomes.
* Blend deterministic logic (for safety & reproducibility) with Large Language Models (for flexibility & speed).
* Scale seamlessly from a local analyst's laptop to a cloud-hosted, multi-user environment.

---
## 🗺️ Roadmap (What & When?)
The full living roadmap is tracked in **[ROADMAP_CANVAS.md](./ROADMAP_CANVAS.md)**.  
Below is a snapshot of the current work streams:

| ID | Work Stream | Key Next Steps |
|----|-------------|----------------|
| WS-1 | Stability & Refactor | Unit tests ≥ 60 % · remove duplication |
| WS-2 | Hybrid AI Engine | Intent classification · dynamic code generation |
| WS-3 | Data & Storage | Persist saved questions in SQLite · migrations |
| WS-4 | UX & Viz | Responsive layout · drag-and-drop chart builder |
| WS-5 | Cloud Deployment | Docker · CI/CD · AWS/GCP hosting |
| WS-6 | Security & Quality | Hardened sandbox · ≥60 % coverage gate ✔ |

> ❖ Legend: ✔ complete · ☐ pending · 🔄 in-progress.  
> See the canvas for milestones, risks, and backlog.

---
## 🧭 Coding Conventions (How?)

### General
1. **Python 3.11**; keep external deps lean (see `requirements.txt`).
2. Follow **PEP 8** with `black` style (line length = 88).
3. Use **type hints** (`mypy --strict`) for all new functions.
4. Write **docstrings** (Google style) for public classes & methods.
5. Add/extend **unit tests** in `tests/` for new logic (pytest).

### Project Structure (TL;DR)
```
app/            # UI & pages (Panel)
  └── pages/
       ├── data_assistant.py  # main assistant
       └── patient_view.py    # patient view page
app/ai_helper.py             # GPT-4 integration helper
 data/                       # local assets & saved_questions.json
 tests/                      # pytest suite (WIP)
run.py                       # Panel server entry-point
```

### Commit & Branching
* **main** = deployable head. Feature work: `feat/<topic>`; experiments: `exp/<topic>`.
* Conventional commit messages: `feat:`, `fix:`, `chore:` …
* Open a PR → CI runs lint + tests → review → squash-merge.

### LLM Usage
* All prompts & responses routed through `app/ai_helper.py`.
* Deterministic templates now cover **median** aggregates and **distribution histograms** in addition to count/average.
* Hardened execution sandbox blocks unsafe imports & network access.
* Persist user queries (minus PII) for audit.
* Post-process model output with rule-based checks before execution.

---
## ⏱️ Quick Start (Local)
```bash
# Install deps
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Set your OpenAI key
cp .env.example .env  # or echo "OPENAI_API_KEY=sk-..." >> .env

# Run the app
python run.py
```
Open `http://localhost:5006` in your browser.

---
## 🧪 Testing & Continuous Integration

Our safety-net is a minimal but important **pytest** suite + GitHub Actions workflow.

```
# Fast smoke tests (< 5 s)
pytest -m smoke

# Full suite with coverage
pytest --cov --cov-branch
```

Notes:
* Pre-commit hooks (`black`, `ruff`) run automatically before each commit (`pre-commit install` one-time).
* CI fails if branch coverage drops below the level on `main`.
* Add or extend tests whenever you fix a bug or create new helpers—e.g., histogram helper raises `ValueError` when column missing.

---
*Last updated: <!-- AI/maintainer: timestamp on save -->* 