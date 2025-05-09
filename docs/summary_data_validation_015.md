# Sprint 0.15 – Data-Validation Hardening & Mock-DB Parity

_Date:_ 2025-05-11

## What we set out to do
* Close the schema gap between the synthetic **mock_patient_data.db** and production **patient_data.db** so tests mirror reality.
* Eliminate lingering environment-variable inconsistencies that caused pages to open the wrong database.
* Stabilise the Data-Validation UI for human-in-the-loop (HITL) testing.

## Key accomplishments
| Area | Outcome |
|------|---------|
| Mock DB | • Added **mental_health**, **pmh**, **patient_visit_metrics** and eight system tables.<br>• All column names, `NOT NULL` constraints and unique indexes now match production.<br>• Regenerated 20-patient cohort with realistic vitals, scores, labs, visit metrics and validation_rules (41). |
| Env override | Single helper `db_query.get_db_path()` now respected app-wide. `export MH_DB_PATH=...` switches datasets for all pages & tests. |
| Dashboard | Fixed total-patient count and stats when mock DB in use. |
| Data-Validation UI | • Handles alphanumeric IDs (`SP001`).<br>• Patient-row highlight bug resolved.<br>• Quality-metrics reporting complete (field & date trend plots). |
| Tests | • `test_db_path_override.py` verifies env-var override.<br>• Synthetic self-test extended (height, unit, mental_health, pmh). 100 % pass. |
| Docs & tooling | • Updated CHANGELOG & ROADMAP.<br>• `create_mock_db.py` auto-adds repo root to `sys.path`; `--overwrite` flag regenerates DB. |

## Metrics
* Unit-test coverage: _unchanged_ 71 % (threshold 60 %).
* Synthetic self-test: 10/10 tests passing.
* Mock DB creation time: **< 0.5 s** (20 patients, 500+ rows).

## Outstanding risks / next steps
1. _Performance optimisation for patient list refresh_ (WS-7 🔄) – hit 600 ms with 20 patients; will address caching & pagination for real dataset (~700 patients).
2. Docker packaging (WS-5) remains open; will be picked up in infra sprint.
3. Plan A/B framework for clarification approaches (WS-6 backlog).

---
_Compiled automatically by the AI assistant after Sprint 0.15 hand-off._ 