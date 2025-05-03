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
| WS-2 | **Hybrid AI Engine** | Natural-language analytics powered by GPT | ✔ OpenAI integration <br> ✔ Intent classification API <br> ✔ Richer code templates (var/std, pct-change, top-N, GROUP BY, Multi-Metric) <br> ☐ Dynamic code generation sandbox | Q2–Q3 2024 |
| WS-3 | **Data & Storage** | Scalable, durable persistence | ☐ Move saved questions to SQLite <br> ☐ Add migrations <br> ☐ Multiple-user support | Q3 2024 |
| WS-4 | **UX & Visualization** | Intuitive interface & dashboards | 🔄 Auto-visualisation mapper <br> ☐ Responsive layout overhaul <br> ☐ Drag-and-drop chart builder <br> ☐ Help & onboarding tour <br> ☐ Refine follow-ups | Q3 2024 |
| WS-5 | **Cloud Deployment** | CI/CD & managed hosting | ☐ Dockerize app <br> ☐ GitHub Actions pipeline <br> ☐ Deploy to AWS/GCP <br> ☐ Observability (logging, metrics) | Q4 2024 |

Legend: ✔ = done ☐ = pending 🔄 = in progress

---
## 4. Backlog (Next-Up Tasks)
- [ ] **Tests:** Scale golden-query harness to ≥25 canonical questions (#testing)
- [✔] **AI:** Multi-metric & boolean filter parsing (#ai) - *Backend & parsing tests complete; needs live LLM validation.*
- [ ] **UX:** Auto-visualisation mapper (#design)
- [ ] **Persistence:** SQLite migration for `saved_questions` table (#db)
- [ ] **Refactor:** Extract plotting utilities into `plots.py` (#code-health)
- [ ] **Deployment:** Draft minimal Dockerfile & GH Action (#devops)
- [ ] **UX:** Add tooltip hints to saved-question buttons (#design)

> _The backlog is intentionally short; move items to Work Streams when scheduled._

---
## 5. Risks & Mitigations
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM hallucinations | Incorrect clinical insights | Medium | Keep deterministic post-processing; display code used |
| Data privacy breach | Legal & reputational | Low | Run models locally / mask PII; audit logging |
| Scope creep | Delays | Medium | Roadmap gatekeeper & time-boxed spikes |

---
## 6. Meta
- **Document owner:** @gmtfr  
- **Last updated:** 2025-05-06 # Reflecting backlog completion
- **Edit instructions for AI assistants:**  
  • Maintain markdown table formatting.  
  • Use ✔/☐/🔄 symbols for status.  
  • Preserve section headers.  
  • Keep backlog ≤ 10 items; archive completed ones. 