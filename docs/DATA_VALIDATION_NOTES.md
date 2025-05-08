# Metabolic Program Data – Key Issues & Design Notes  
*(Last updated May 2025)*

---

## 1 Data Flow & Storage
| Layer | Details |
|-------|---------|
| **Source of Truth** | Cloud SQL warehouse that aggregates EHR, lab, and scheduling feeds. |
| **Working Copy** | JSON snapshot **manually pulled on‑demand** and loaded into the local SQLite file `patient_data.db`. |
| **Write‑back** | No direct writes from the app to the cloud; fixes are made upstream (EHR, LIMS, etc.). A fresh JSON pull brings corrected data downstream. |

---

## 2 Observed Data Problems
| Category | Typical examples | Impact |
|----------|------------------|--------|
| **Entry Errors** | Weight 20 lb vs 200 lb, date 2050 vs 2024 | Must block analysis; obvious outliers. |
| **Omissions** | Null provider/coach names, missing insurance_type | Breaks joins & reporting pipelines. |
| **Missing Encounters/Labs** | Late provider visit, overdue blood panel | Disrupts cadence‑based outcome metrics. |
| **Patient Drop‑outs** | Only a few visits then inactive | Must be flagged so they don’t dilute averages. |
| **Program Completion Variance** | 7 provider visits stretch > 6 months; < 16 coach visits | Requires custom “stage” logic. |
| **Derived Metric Gaps** | Vitality Score missing because inputs not all present within 14 days | Lowers KPI completeness; drives follow‑up. |

---

## 3 Validation vs Analysis Responsibilities
| Layer | Responsibilities |
|-------|------------------|
| **Validation Engine** | • Range/outlier checks • Presence (not‑null) rules • Timeliness/SLA checks • Cross‑field coherence (e.g., Vitality inputs within 14 days). |
| **Analysis SQL Views** | • Compute program stage & dropout flag • Filter cohorts (e.g., completed vs in‑progress) • Ignore Vitality Scores where inputs invalid. |

---

## 4 Rule‑Catalogue Enhancements
* Add columns `severity` (`blocking`, `warning`, `info`) and `category` (engagement, vitals, labs, admin, patient‑reported).
* Support new rule types:  
  * `frequency` (SLA/timeliness)  
  * `consistency` (multi‑field window for Vitality inputs)
* **Waivers** expire automatically when the corresponding rule is edited.

---

## 5 Edge‑Case Policies
| Edge case | Policy |
|-----------|--------|
| New patient with zero cancelled/no‑show rows | Allowed (info only) until first visit completed. |
| Height missing after baseline | **Blocking** – BMI can’t be computed. |
| Vitality inputs collected > 14 days apart | Vitality Score set to `NULL`; raise *blocking* issue. |

---

## 6 Patient Data‑Quality Dashboard (high‑level)
1. **Header badge** — record‑quality: % of blocking rules passed.  
2. **Status tiles** — provider‑visit progress, coach‑visit progress, days since last provider visit, current Vitality Score, program stage.  
3. **Timeline ribbon** — month‑by‑month icons: ✔ on‑time, ⚠ late, ✕ missing for provider visits & labs.  
4. **Validation issues table** — Severity • Metric • Current • Expected • Age (days) • Resolve/Waive.  
5. **Vitals & Labs cards** — sparkline + border color (red = blocking, amber = warning).  
6. **Sidebar** — links to EHR/lab portals; waiver note field.

---

## 7 Process Workflow
1. **Manual JSON import** overwrites local SQLite when you choose to refresh.  
2. Validation job runs immediately after import → populates `validation_issues`.  
3. Clinician triages issues via Validation Inbox & Patient Dashboard.  
4. Source systems are updated to fix data; next manual refresh clears resolved issues.  
5. Analysis queries only include patients whose **blocking** issues are resolved or waived.

---

> **Save this file as** `docs/DATA_VALIDATION_NOTES.md` in your project so any AI or human collaborator can quickly grasp the known data challenges and agreed validation conventions.