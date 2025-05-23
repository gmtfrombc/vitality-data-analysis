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
| WS-2 | Hybrid AI Engine | Multi-metric correlation ✔ · slot-based Smart Clarifier ✔ · auto-viz template coverage ✔ |
| WS-3 | Data & Storage | Saved questions in SQLite ✔ · migrations ✔ · JSON→SQLite ETL ✔ |
| WS-4 | UX & Viz | Auto-visualization mapper ✔ · Smart Clarifier UX ✔ · fix plots.py test issues ✔ · responsive layout |
| WS-5 | Cloud Deployment | Docker · CI/CD · AWS/GCP hosting |
| WS-6 | Continuous Feedback | Feedback widget ✔ · query/response logging ✔ · Assistant Evaluation Framework ✔ · enhanced Self-Test Loop 🔄 |

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
app/                # All core application code (UI, logic, helpers)
  ├── pages/        # Panel pages (dashboard, patient view, etc.)
  ├── utils/        # AI, codegen, validation, helpers
  ├── components/   # UI components
  ├── assets/       # Static assets (if any)
  └── ...           # Other app modules (engine.py, ui.py, etc.)
data/               # Local assets, reference data, and saved_questions.json
archive/            # Legacy, abandoned, or experimental files (for audit/history)
docs/               # Technical documentation, design, and summaries
  └── README_SELF_TEST.md  # Self-test system documentation
logs/               # Test and run logs (auto-rotated)
migrations/         # DB migration scripts (if any)
tests/              # All test code (mirrors app/ structure)
requirements.txt    # Main dependencies
run.py              # Main entry point (Panel server)
pyproject.toml      # Project metadata/config
.venv/              # Virtual environment (not versioned)
.env                # Environment variables (not versioned)
.gitignore          # Git ignore rules
```

> **Note:** All legacy, abandoned, or experimental files are now in the `archive/` folder at the project root. See that folder for historical scripts, prototypes, and compatibility shims.

### Commit & Branching
* **main** = deployable head. Feature work: `feat/<topic>`; experiments: `exp/<topic>`.
* Conventional commit messages: `feat:`, `fix:`, `chore:` …
* Open a PR → CI runs lint + tests → review → squash-merge.

### LLM Usage
* All prompts & responses routed through `app/ai_helper.py`.
* Deterministic templates now cover **median** aggregates, **distribution histograms**, and **date range filtering**.
* Intelligent **slot-based Smart Clarifier** identifies specific missing information in queries and asks targeted questions.
* Hardened execution sandbox blocks unsafe imports & network access.
* Persist user queries (minus PII) for audit.
* Post-process model output with rule-based checks before execution.

## AI Assistant Module Structure

The AI Assistant is now fully modularized for clarity and maintainability. Key modules:

- **UI Construction:** `app/pages/ai_assistant_ui.py` – All Panel layout, widgets, and user interaction logic.
- **State Management & Persistence:** `app/utils/query_state.py` – Handles loading, saving, and updating saved queries (file-based, extensible).
- **Prompt Engineering:** `app/utils/prompt_engineering.py` – Centralizes prompt construction, schema formatting, and example query logic for LLMs.
- **Main Logic:** `app/pages/ai_assistant.py` – Orchestrates the assistant, connects UI, state, and prompt modules, and manages LLM client.

### Where to Add/Change Logic
- **UI changes:** Edit or extend `ai_assistant_ui.py`.
- **Prompt templates/examples:** Update `prompt_engineering.py`.
- **Saved query logic:** Update `query_state.py`.
- **Business logic or LLM integration:** Update `ai_assistant.py`.

### Example Usage
To add a new prompt example or schema rule, edit `prompt_engineering.py` and use the helper functions in `ai_assistant.py`.

To persist a new type of query state, extend the interface in `query_state.py`.

All modules are documented with Google-style docstrings for onboarding and maintenance.

---
## ⏱️ Quick Start (Local)
```bash
# Install deps
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Set your OpenAI key
cp .env.example .env  # or echo "OPENAI_API_KEY=sk-..." >> .env

# (Optional) ingest patient export
#   1. Place your *patients.json* export (or run `python deidentify_patients.py patients.json` → `deidentified_patients.json`)
#   2. Run ETL: `python -m etl.json_ingest deidentified_patients.json`

# Run the app
python run.py  # automatically applies any pending database migrations
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
* **Known Issue (2025-07-15):** Tests for plot utilities (`tests/utils/test_plots.py`) are failing due to mock implementation issues. Coverage remains strong at 73.38% (above the required 60%), and a fix is in progress. See `docs/summary_2025-07-15.md` for details.

---
*Last updated: 2025-05-06 – WS-6 Assistant Evaluation Framework implemented*

## Getting Started

1. Clone this repository
2. Run `pip install -r requirements.txt` to install dependencies
3. Start the application with `python run.py`

## Features

- **Data Assistant**: Natural language interface for querying patient data
- **Visualizations**: Automatic visualization generation based on query type
- **Self-Test System**: Regression testing to ensure assistant reliability
- **Evaluation Framework**: Metrics dashboard for measuring assistant performance
- **Developer Tools**: Scripts for maintaining project quality

## Documentation

Key project documents:
- [ROADMAP_CANVAS.md](ROADMAP_CANVAS.md) - Project roadmap and milestones
- [CHANGELOG.md](CHANGELOG.md) - History of changes and feature additions
- [docs/](docs/) - Technical documentation and development summaries
- [docs/README_SELF_TEST.md](docs/README_SELF_TEST.md) - Self-test system documentation

## Developer Workflow

### Self-Test Framework

The project includes a synthetic "Golden-Dataset" self-test loop that validates the Data Analysis Assistant's functionality:

```bash
# Run the self-test manually
./run_self_test.sh

# Set up as a daily cron job
crontab -e
# Add: 0 1 * * * cd /path/to/project && ./run_self_test.sh
```

The self-test:
- Creates a synthetic database with controlled data
- Runs predetermined queries with known correct answers
- Compares results to expected values
- Reports any discrepancies

Test results are stored in `logs/self_test_*` directories with detailed reports.

### Assistant Evaluation Framework

The Assistant Evaluation Framework provides quantitative metrics for measuring, tracking, and improving the assistant's performance:

```bash
# Calculate metrics manually
python calculate_metrics.py --days=30

# Schedule daily metrics calculation (with notification)
crontab -e
# Add: 0 0 * * * cd /path/to/project && python calculate_metrics.py --notify
```

#### Using the Evaluation Dashboard

1. Start the application with `python run.py`
2. Navigate to the "Evaluation Dashboard" tab
3. Use the time period controls to view different timeframes (7/30/90 days)
4. Click "Refresh Data" to update metrics in real-time

#### Key Metrics

The framework tracks metrics across multiple dimensions:
- **Satisfaction**: User feedback ratings and comments
- **Response Quality**: Response times and code complexity
- **Intent Classification**: Accuracy of query intent detection
- **Query Patterns**: Common query types and complexity
- **Visualization**: Effectiveness of auto-generated visualizations

Metrics are stored historically in the database, allowing trend analysis over time. Reports are also saved to `logs/metrics_report_*.json` for offline analysis.

### Assistant Handoff Process

When switching between AI assistants or ending a development session, use the handoff script:

```bash
./handoff.sh
```

This script:
1. Runs the self-test to validate current functionality
2. Creates a summary template for the current date if needed
3. Generates a checklist of documentation to update
4. Provides a standardized handoff message for the assistant

The assistant will then update documentation, address any test failures, and prepare the project for the next session.

## License

[License information here] 

## Project Maintainer Profile

This section documents the technical background and communication preferences of the primary maintainer to help collaborators and AI assistants provide appropriate support.

### Background and Expertise

- **Professional Role**: Physician and designer of the Metabolic Health Program
- **Programming Experience**:
  - Flutter: Intermediate level
  - Python: Beginner level (limited experience)
  - SQL: Basic understanding of queries
- **Data Science Knowledge**: College-level understanding of statistics and data concepts
- **Domain Expertise**: Strong medical/clinical knowledge, especially in metabolic health

### Communication Preferences

- **Technical Explanations**: Prefer concepts explained without assuming deep technical background
- **Code Examples**: Include comments explaining logic and purpose
- **Terminology**: Define technical terms and acronyms when introducing new concepts
- **Visual Aids**: Diagrams and flowcharts are helpful for complex processes

When providing support or suggesting implementation approaches, please:
1. Avoid overly technical jargon without explanation
2. Break down complex tasks into smaller, manageable steps
3. Explain the "why" behind technical decisions
4. Provide concrete examples where possible

## Post-Refactor Highlights

- **Modular Architecture:** All core logic is now split into clear modules (see `app/utils/ai/`, `app/engine.py`, `app/ui.py`).
- **Dependency Injection:** LLM, DB, and config are injected via constructors/parameters for testability and flexibility.
- **Centralized Error Handling:** All errors are raised and handled via shared exception types in `app/errors.py`.
- **Test Isolation:** All tests use fixtures/mocks; no monkeypatching of private helpers. LLM and DB calls are stubbed or injected for offline/CI runs.
- **Legacy Code Quarantined:** All legacy/compatibility code is moved to `archive/`.

## Architecture & API

See [docs/design/ARCHITECTURE.md](docs/design/ARCHITECTURE.md) for a full architecture diagram, module map, and dependency flow.

**Main Public APIs:**
- `AIHelper` (`app/utils/ai_helper.py`): LLM orchestration, codegen, narrative.
- `AnalysisEngine` (`app/engine.py`): Query → intent → code → results pipeline.
- `UIComponents` (`app/ui.py`): All Panel widgets and UI state. 

## Configuration & Environment Variables

All configuration is centralized in `app/config.py` and can be set via environment variables or a `.env` file (loaded automatically).

**Key Environment Variables:**

| Variable                | Default                        | Purpose                                  |
|-------------------------|--------------------------------|------------------------------------------|
| `OPENAI_API_KEY`        | (none)                         | OpenAI API key for LLM features          |
| `OPENAI_MODEL`          | `gpt-4`                        | LLM model name (override if needed)      |
| `OFFLINE_MODE`          | `0`                            | Set to `1` to disable LLM calls          |
| `LOG_LEVEL`             | `INFO`                         | Logging verbosity                        |
| `DATABASE_URL`          | `sqlite:///patient_data.db`    | Main DB URL (SQLAlchemy, future use)     |
| `MH_DB_PATH`            | `patient_data.db`              | SQLite DB path for legacy helpers        |
| `VP_DATA_DB`            | `../patient_data.db`           | Shared DB for saved questions/logs       |
| `SMTP_SERVER`           | (none)                         | Email/notification server (optional)     |
| `SMTP_PORT`             | `587`                          | Email server port                        |
| `SMTP_USER`             | (none)                         | Email username                           |
| `SMTP_PASSWORD`         | (none)                         | Email password                           |
| `NOTIFICATION_SENDER`   | `no-reply@example.com`         | Sender address for notifications         |
| `ONLINE_LLM_TESTS`      | `0`                            | Enable online LLM tests in CI            |
| `HAPPY_PATH_TEST`       | `false`                        | Enable happy-path test mode              |
| `WEIGHT_CHANGE_SANDBOX_TEST` | `false`                   | Enable weight change sandbox test        |
| `DEBUG`                 | `0`                            | Set to `1` or `true` for debug logging   |

**How to set environment variables:**
- Create a `.env` file in the project root (see `.env.example` for template)
- Or set variables in your shell before running the app:
  ```bash
  export OPENAI_API_KEY="sk-..."
  export OFFLINE_MODE=1
  ```

**Overriding in Production/Test:**
- All config can be overridden by setting environment variables at runtime (e.g., via Docker, CI, or cloud deployment).
- For test isolation, use `OFFLINE_MODE=1` to disable LLM calls and run with deterministic templates/mocks.

See `app/config.py` for the full list and logic. 

## Testing Strategy & Dependency Injection

All tests use **pytest** and are located in the `tests/` directory, mirroring the main module structure. Coverage is tracked and must remain ≥ 60% on `main`.

**Key Testing Practices:**
- **Fixtures & Mocks:** All external dependencies (LLM, DB) are injected or mocked using pytest fixtures (see `tests/conftest.py`).
- **No Monkeypatching of Private Helpers:** Only public interfaces are patched or injected; private helpers are not monkeypatched.
- **Offline/Online Modes:**
  - By default, tests run in **offline mode** (`OFFLINE_MODE=1`), stubbing all LLM calls and DB access for deterministic, fast tests.
  - To run integration tests with real LLM calls, set `ONLINE_LLM_TESTS=1` and provide a valid `OPENAI_API_KEY`.
- **Dependency Injection:**
  - All major classes (e.g., `AIHelper`, `AnalysisEngine`) accept dependencies (LLM, DB, config) via constructor or parameters, enabling easy test injection.
  - Example: `AIHelper(ask_llm_func=my_stub_llm)`
- **Test Coverage:**
  - Run `pytest --cov --cov-branch` to check coverage. CI will fail if coverage drops below the threshold.
- **Test Isolation:**
  - Each test is isolated and does not depend on global state. Temporary DBs and mock clients are used as needed.

**How to Run Tests:**
```bash
# Fast smoke tests (offline, < 5s)
pytest -m smoke

# Full suite with coverage (offline)
pytest --cov --cov-branch

# Run integration tests with real LLM (requires API key)
export ONLINE_LLM_TESTS=1
export OPENAI_API_KEY=sk-...
pytest -m integration
```

See `tests/conftest.py` for fixture details and `tests/` for example usage of dependency injection in tests. 

## Migration & Legacy Code

- All legacy and compatibility code has been moved to the `archive/` directory (see `archive/ai_helper_old.py`, etc.).
- No active code paths reference legacy modules; all imports and usage have been updated to canonical modules.
- Migration was performed in parallel with a feature branch and/or feature flags, with all tests passing before removal of legacy code.
- See `docs/refactoring/ai_helper_refactor/ai_helper_sprint_checklist.md` for the full migration checklist and audit trail.
- Project is now ready for handoff, onboarding, or further migration. 

## Final Status & Known Risks

- **All tests are green** (see `docs/refactoring/ai_helper_refactor/final_test_results.txt` for full results).
- **Test coverage:** 63% (above the 60% threshold).
- **No active legacy code**; all legacy/compatibility code is quarantined in `archive/`.
- **No known critical risks.**
- **TODOs:**
  - Some modules (e.g., advanced correlation, fallback codegen, narrative builder) have low coverage and could be further tested.
  - Continue to monitor for edge cases in LLM intent parsing and code generation.

**Project is ready for handoff, onboarding, or migration.** 