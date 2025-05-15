# DASHBOARD Canvas – Data-Quality Gap Report

_Last updated: 2025-05-19_

---
## Purpose
Provide a one-click/manual tool for clinicians or data stewards to list patients who meet clinical criteria (e.g. BMI > 30) **but lack** the corresponding diagnosis in PMH.  Output is a simple table / downloadable CSV – no charts.

---
## 1. Feature Overview
| ID | Feature | User Story | Status |
|----|---------|-----------|--------|
| DQ-GAP-01 | Condition Gap Report | *As a clinician*, I want to run a report that shows patients whose measurements imply a condition (obesity, pre-diabetes, T2DM, hypertension…) but who do **not** have that diagnosis coded, so that I can correct the record. | ☐ |

---
## 2. Scope (Phase 1 – Manual Run)
1. Command-line / Assistant invocation only (no scheduler)
2. Accepts a condition keyword ("obesity", "prediabetes", etc.) and thresholds (optional)
3. Returns a dataframe printed as a text table **and** writes `tmp/gap_report_<condition>.csv`
4. No charting libraries – text/CSV only

---
## 3. Implementation Notes
• Re-use existing SQLite connection via `db_query`
• Gap logic:
  - Look up ICD-10 codes for the condition via `condition_mapper`
  - Determine measurement rule, e.g. BMI > 30, A1C ≥ 5.7, BP ≥ 130/80
  - `LEFT JOIN` vitals/labs with PMH; filter `pmh.patient_id IS NULL`
• Wrap in helper: `get_condition_gap_report(condition: str, **kwargs) -> pd.DataFrame`
• CLI entry-point: `python -m scripts.generate_gap_report --condition obesity`
• Unit-tests: happy path + "unknown condition" error

---
## 4. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Large joins slow | Use indexes on `vitals.patient_id, vitals.date` |
| Evolving clinical thresholds | Thresholds passed as args / config YAML |

---
## 5. Next Steps
1. Build helper + CLI (est. 0.5 day)
2. Integrate into Assistant prompt templates (0.25 day)
3. Write unit tests (0.25 day)

---
*Owner: @gmtfr – created via assistant session 2025-05-19* 