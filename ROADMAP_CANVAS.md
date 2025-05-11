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
| WS-1 | **Stability & Refactor** | Solid baseline with tests and CI | ✔ Persist saved questions (file) <br> ✔ Unit test coverage ≥ 60 % <br> ✔ Golden query harness <br> ☐ Refactor duplicated code | Q2 2024 |
| WS-2 | **Hybrid AI Engine** | Natural-language analytics powered by GPT | ✔ OpenAI integration <br> ✔ Intent classification API <br> ✔ Richer code templates (var/std, pct-change, top-N, GROUP BY, Multi-Metric) <br> ✔ Date range filtering <br> ✔ Multi-metric correlation analysis <br> ✔ Enhanced correlation analysis (conditional, time-series) <br> ✔ Intent engine hardening (confidence scoring, synonym map, tricky-query harness) <br> ✔ Slot-based Smart Clarifier with fallback template <br> ✔ Template coverage (auto-viz hooks, top-N chart) <br> ✔ Scalar-metric narrative handling (avg/sum vs count) | Q2–Q3 2024 |
| WS-3 | **Data & Storage** | Scalable, durable persistence | ✔ Move saved questions to SQLite (tests + read/write) <br> ✔ Add migrations <br> ✔ Incremental ETL & Import panel with audit logging <br> ☐ Multiple-user support | Q3 2024 |
| WS-4 | **UX & Visualization** | Intuitive interface & dashboards | ✔ Smart clarifier upgrade (slot-based follow-ups) <br> ✔ Correlation heat-map template <br> ✔ Enhanced correlation visualizations (conditional heatmaps, time-series plots) <br> ✔ Auto-visualisation mapper <br> ✔ Fixed Reset All button to properly clear results display <br> ☐ Help & onboarding tour | Q3 2024 |
| WS-5 | **Cloud Deployment** | CI/CD & managed hosting | ☐ Dockerize app <br> ✔ GitHub Actions pipeline <br> ☐ Deploy to AWS/GCP <br> ☐ Observability (logging, metrics) | Q4 2024 |
| WS-6 | **Continuous Feedback & Evaluation** | Human-in-the-loop iterative improvement | ✔ Add feedback widget & `assistant_feedback` table <br> ✔ Query/response logging MVP <br> ✔ Nightly triage report <br> ✔ Assistant Evaluation Framework <br> ✔ Weekly **Feedback Friday** loop <br> 🔄 Enhanced Self-Test Loop with AI-driven testing <br> ✔ Comment-box & layout fix for in-app feedback widget <br> ✔ CLI triage tools (feedback_triage & test_generator) <br> ✔ Active patient status clarification for metric queries <br> ✔ Composite Overall Score with weighted performance metrics <br> ✔ Interactive model retraining workflow with intent classifier <br> ✔ Feedback widget confirmation message after submission <br> ✔ Repositioned refine controls above feedback widget <br> ✔ Fixed event handlers for feedback buttons <br> ✔ Enhanced feedback widget reset functionality for consistent UI state <br> ☐ Dataset for fine-tuning | Q3 2025 |
| WS-7 | **Data Quality & Validation** | Identify and correct missing/inaccurate data | ✔ Validation rule schema <br> ✔ Patient-centric validation UI <br> ✔ Data quality dashboard <br> ✔ Correction tracking & audit <br> ✔ Fix UI, plotting and date handling issues <br> ✔ Patient list filtering operational <br> ✔ Validation Inbox (Ring 1 MVP) <br> ✔ Rule catalogue (YAML) & nightly validation job <br> ✔ Patient Data-Quality Dashboard <br> ✔ Health scores data table <br> ✔ Robust date handling and normalization utilities <br> ✔ Unit testing for validation, rule-loader, and date handling <br> ✔ GitHub Actions CI workflow with test coverage enforcement <br> ✔ Quality metrics reporting <br> 🔄 Performance optimisation for patient list refresh <br> ✔ Admin Reload Rules button & rule-duplication clean-up <br> ✔ Categorical & Not-Null rule support w/ UI notifications | Q4 2025 |

Legend: ✔ = done ☐ = pending 🔄 = in progress

---
## 4. Backlog (Next-Up Tasks)
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
- [ ] **Enhancement:** Extend reference ranges to support all clinical metrics in the database (#clinicalData)

> _The backlog is intentionally short; move items to Work Streams when scheduled._

---
## 5. Risks & Mitigations
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM hallucinations | Incorrect clinical insights | Medium | Keep deterministic post-processing; display code used |
| Data privacy breach | Legal & reputational | Low | Run models locally / mask PII; audit logging |
| Scope creep | Delays | Medium | Roadmap gatekeeper & time-boxed spikes |
| Test instability | Development friction | Low | ✅ Implemented robust mock strategy for visualization components with lightweight stubs |

---
## 6. Meta
- **Document owner:** @gmtfr  
- **Last updated:** 2025-05-14 # Fixed visualization testing with HoloViews and Panel stubs; all 254 tests now pass
- **Edit instructions for AI assistants:**  
  • Maintain markdown table formatting.  
  • Use ✔/☐/🔄 symbols for status.  
  • Preserve section headers.  
  • Keep backlog ≤ 10 items; archive completed ones.

### 2025-05-11 – Sandbox stability patch
- Delivered holistic stubs for holoviews/hvplot inside sandbox (incl. Store registry) – 'Plotting libraries are disabled' ImportErrors resolved.
- Remaining blocker: AI-generated SQL for BP vs A1C uses `vitals.score_type` which doesn't exist. Recommend adding schema-aware validation or adjusting prompt templates/rule-engine fallback.  See docs/summary_testing_011.md. 