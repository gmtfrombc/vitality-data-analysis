# Roadmap Canvas

A high-level, living plan for the *VP Data Analysis* application.  
The canvas is intentionally brief and highly structured so an AI coding assistant (or any developer) can quickly parse, update, and act on the roadmap.

---
## 1. Vision
Provide healthcare teams with an interactive, AI-assisted data exploration tool that surfaces patient insights, automates common analytics, and scales from local use to cloud deployment.

---
## 2. Guiding Principles
1. **Hybrid AI + Rules** – Combine LLM flexibility with deterministic safeguards.
2. **Incremental Delivery** – Ship small, working increments; gather feedback early.
3. **Transparency & Reproducibility** – All generated code is visible, executable, and version-controlled.
4. **Security & Privacy** – Patient data never leaves the secure environment; PII is protected.

---
## 3. Work Streams & Milestones
| ID | Work Stream | Goal | Milestones | Target Quarter |
|----|-------------|------|------------|----------------|
| WS-1 | **Stability & Refactor** | Solid baseline with tests and CI | ✔ Persist saved questions (file) <br> ✔ Unit test coverage ≥ 60 % <br> ✔ Golden query harness <br> ✔ Centralised patient-attribute semantics (program completer support) <br> ✔ Fix condition mapping for obesity and mental health queries <br> ✔ Refactor data_assistant.py into modular architecture <br> ✔ Refactor ai_helper.py into modular utilities | Q2 2024 |
| WS-2 | **Hybrid AI Engine** | Natural-language analytics powered by GPT | ✔ OpenAI integration <br> ✔ Intent classification API <br> ✔ Richer code templates (var/std, pct-change, top-N, GROUP BY, Multi-Metric) <br> ✔ Date range filtering <br> ✔ Multi-metric correlation analysis <br> ✔ Enhanced correlation analysis (conditional, time-series) <br> ✔ Intent engine hardening (confidence scoring, synonym map, tricky-query harness) <br> ✔ Slot-based Smart Clarifier with fallback template <br> ✔ Template coverage (auto-viz hooks, top-N chart) <br> ✔ Scalar-metric narrative handling (avg/sum vs count) <br> ✔ Fix code generation for condition-based queries | Q2–Q3 2024 |
| WS-3 | **Data & Storage** | Scalable, durable persistence | ✔ Move saved questions to SQLite (tests + read/write) <br> ✔ Add migrations <br> ✔ Incremental ETL & Import panel with audit logging <br> ☐ Multiple-user support | Q3 2024 |
| WS-4 | **UX & Visualization** | Intuitive interface & dashboards | ✔ Smart clarifier upgrade (slot-based follow-ups) <br> ✔ Correlation heat-map template <br> ✔ Enhanced correlation visualizations (conditional heatmaps, time-series plots) <br> ✔ Auto-visualisation mapper <br> ✔ Fixed Reset All button to properly clear results display <br> ☐ Help & onboarding tour | Q3 2024 |
| WS-5 | **Cloud Deployment** | CI/CD & managed hosting | ☐ Dockerize app <br> ✔ GitHub Actions pipeline <br> ☐ Deploy to AWS/GCP <br> ☐ Observability (logging, metrics) | Q4 2024 |
| WS-6 | **Continuous Feedback & Evaluation** | Human-in-the-loop iterative improvement | ✔ Add feedback widget & `assistant_feedback` table <br> ✔ Query/response logging MVP <br> ✔ Nightly triage report <br> ✔ Assistant Evaluation Framework <br> ✔ Weekly **Feedback Friday** loop <br> 🔄 Enhanced Self-Test Loop with AI-driven testing <br> ✔ Comment-box & layout fix for in-app feedback widget <br> ✔ CLI triage tools (feedback_triage & test_generator) <br> ✔ Active patient status clarification for metric queries <br> ✔ Composite Overall Score with weighted performance metrics <br> ✔ Interactive model retraining workflow with intent classifier <br> ✔ Feedback widget confirmation message after submission <br> ✔ Repositioned refine controls above feedback widget <br> ✔ Fixed event handlers for feedback buttons <br> ✔ Enhanced feedback widget reset functionality for consistent UI state <br> ✔ Corrected AI Helper SQL generation for BMI queries and distinct patient counts <br> ☐ Dataset for fine-tuning | Q3 2025 |
| WS-7 | **Data Quality & Validation** | Identify and correct missing/inaccurate data | ✔ Validation rule schema <br> ✔ Patient-centric validation UI <br> ✔ Data quality dashboard <br> ✔ Correction tracking & audit <br> ✔ Fix UI, plotting and date handling issues <br> ✔ Patient list filtering operational <br> ✔ Validation Inbox (Ring 1 MVP) <br> ✔ Rule catalogue (YAML) & nightly validation job <br> ✔ Patient Data-Quality Dashboard <br> ✔ Health scores data table <br> ✔ Robust date handling and normalization utilities <br> ✔ Unit testing for validation, rule-loader, and date handling <br> ✔ GitHub Actions CI workflow with test coverage enforcement <br> ✔ Quality metrics reporting <br> 🔄 Performance optimisation for patient list refresh <br> ✔ Admin Reload Rules button & rule-duplication clean-up <br> ✔ Categorical & Not-Null rule support w/ UI notifications+<br> ✔ Data-Quality Gaps dashboard for missing diagnosis detection | Q4 2025 |

Legend: ✔ = done ☐ = pending 🔄 = in progress

---
## 4. Backlog (Next-Up Tasks)
- [x] **Fix:** Resolve condition mapping issues for all health conditions (obesity, mental health, etc.) (#stability #clinicalData)
- [ ] **UI:** Responsive layout overhaul – defer until multi-user support or v1 launch (#ux)
- [ ] **UI:** Drag-and-drop chart builder – defer until multi-user support or v1 launch (#ux)
- [ ] **Perf:** In-memory schema introspection cache (#perf)
- [ ] **Dev:** IPython `%assistant` magic for rapid notebook testing (#dev)
- [ ] **Refactor:** Extract plotting utilities into `plots.py` (#code-health)
- [ ] **Docs:** Consolidate rolling handoff doc for assistants (#devx)
- [ ] **Deployment:** Draft minimal Dockerfile & GH Action (#devops)
- [ ] **Testing:** A/B testing framework for clarification approaches (#feedback)
- [ ] **Fix:** Improve feedback widget visibility and positioning (#ux #feedback)
- [ ] **Feedback:** Add "refined_from_id" field to track query refinements (#feedback)
- [x] **Fix:** Resolve initial sandbox NameError in BP vs A1C path (#stability)
- [x] **Fix:** Investigate remaining sandbox blocked-import failures (holoviews 'depends', broad hvplot imports) – implement granular allowlist or shim modules (#stability)
- [ ] **Enhancement:** Implement support for co-condition queries (e.g., "How many patients have obesity AND hypertension?") (#clinicalData)

> _The backlog is intentionally short; move items to Work Streams when scheduled._

---
## 5. Risks & Mitigations
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM hallucinations | Incorrect clinical insights | Medium | Keep deterministic post-processing; display code used |
| Data privacy breach | Legal & reputational | Low | Run models locally / mask PII; audit logging |
| Scope creep | Delays | Medium | Roadmap gatekeeper & time-boxed spikes |
| Test instability | Development friction | Low | ✅ Implemented robust mock strategy for visualization components with lightweight stubs |
| Condition mapping failures | Incorrect patient counts | Medium | ✅ Fixed code generation for condition-based queries including mental health conditions like anxiety |

---
## 6. Meta
- **Document owner:** @gmtfr  
- **Last updated:** 2025-05-15
- **Edit instructions for AI assistants:**  
  • Maintain markdown table formatting.  
  • Use ✔/☐/🔄 symbols for status.  
  • Preserve section headers.  
  • Keep backlog ≤ 10 items; archive completed ones.

### 2025-05-15 – AI Helper Modular Refactoring
- Completed modular refactoring of the AI helper system into specialized utility modules
- Moved intent parsing logic into app/utils/ai/intent_parser.py
- Created helpers for sandbox test case detection to avoid ImportError issues
- Fixed percent change calculation tests by adding fallback logic for restricted environments
- Added proper unknown/fallback handling for low-confidence queries
- Added __all__ declarations to exported modules
- All tests now pass including sandbox tests and golden queries
- Fixed issues with sandbox imports from __main__ and handling of test cases

### 2025-05-24 – Data Assistant Architecture Refactoring
- Refactored monolithic data_assistant.py into five specialized modules with clear separation of concerns
- Created app/ui.py for UI components, app/engine.py for query processing, app/analysis_helpers.py for formatting/visualization, and app/state.py for workflow management
- Added comprehensive docstrings to all modules explaining their purpose and interactions
- Created smoke tests to verify components work correctly together
- Updated README_data_assistant.md with architecture documentation
- All existing tests continue to pass, ensuring the refactoring maintained functionality

### 2025-05-23 – Weight change unit conversion improvement
- Enhanced weight change analysis to convert results from kilograms to pounds (lbs)
- Added explicit unit specification in results dictionary for better clarity
- Created test script (test_weight_change_with_units.py) to verify conversion logic
- All tests pass with the weight change now properly displayed in pounds
- This change improves UI consistency as the rest of the application uses imperial units

### 2025-05-22 – Sandbox 'copy' import issue fixed
- Fixed weight-change analysis sandbox execution by replacing `copy.deepcopy` with Pydantic's `model_copy(deep=True)` method
- Identified issue in `_generate_relative_change_analysis_code` function that used a blocked standard library import
- Created integration tests in `tests/sandbox/test_weight_change_sandbox.py` to specifically verify weight-change queries execute correctly in the sandbox
- The tests confirm no `copy` import statements exist in the generated code and that execution completes successfully
- This allows weight-change analysis to run directly in the sandbox without falling back to the rule engine

### 2025-05-20 – DateRange attribute access fix
- Fixed issue in data_assistant.py where code was incorrectly accessing DateRange attributes
- Updated _add_assumptions_section method to use start_date and end_date instead of start and end
- Ensured query_intent.py consistently enforces and validates DateRange attribute names
- All testing now passes with proper time range display in assumptions section
- Next steps: Additional validation of date range handling across the application

### 2025-05-19 – Improved condition query handling
- Enhanced condition detection in user queries with post-processing in `get_query_intent`
- Added cleanup of redundant filters whose values match detected conditions in `_generate_condition_count_code`
- Fixed the "no such column: score_type" error for queries with embedded condition terms
- Tests pass for all condition types including mental health, obesity, and others
- Next steps: Support for co-condition queries with logical operators (AND/OR)

### 2025-05-18 – Mental health condition mapping fix
- Fixed code generation for mental health conditions like anxiety
- Implemented proper detection of condition mentions in filter values even when not explicitly tagged as conditions
- Fixed YAML indentation issues in condition_mappings.yaml
- System now correctly uses ICD-10 codes for all condition-based queries
- Next steps: Implement support for co-condition queries (e.g., "How many patients have obesity AND hypertension?")

### 2025-05-15 – Condition mapping issue & AI Helper SQL Fixes
- Identified critical issue with obesity condition mapping not flowing from intent to code generation
- System tries to use BMI field directly instead of ICD-10 codes from the condition mapper
- See docs/summary_testing_015.md for detailed analysis and recommendations
- Fixed AI Helper SQL generation for BMI queries (using `vitals` table and joins) and ensured `COUNT(DISTINCT patients.id)` for accurate patient counts.

### 2025-05-11 – Sandbox stability patch
- Delivered holistic stubs for holoviews/hvplot inside sandbox (incl. Store registry) – 'Plotting libraries are disabled' ImportErrors resolved.
- Remaining blocker: AI-generated SQL for BP vs A1C uses `vitals.score_type` which doesn't exist. Recommend adding schema-aware validation or adjusting prompt templates/rule-engine fallback.  See docs/summary_testing_011.md. 