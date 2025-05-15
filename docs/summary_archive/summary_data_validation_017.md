# Sprint 0.17 – Continuous Feedback Polish (2025-05-18)

**Theme:** Usability & Feedback Loop

## Key Outcomes

| Area | Item |
|------|------|
| UI | Embedded feedback widget inside **Results** tab (`result_container` replaces markdown pane). |
| UI | Comment box visible by default (rows=3) to capture qualitative feedback. |
| UX | Improved button spacing and responsive layout in feedback block. |
| Stability | Reset logic clears and hides feedback widget without page refresh. |
| Docs | CHANGELOG, ROADMAP_CANVAS updated; this summary added. |
| Tests | Manual smoke test confirms buttons, comment box, and submit flow render. |
| Dev | CLI triage tools (`feedback_triage.py`, `test_generator.py`) enable manual feedback triage & regression-test scaffolding. |

## Next Up
1. Wire the thumbs/comment data into `assistant_feedback` DB table (backend already exists).
2. Start **Query Test & Feedback** sessions (Feedback-Friday loop) to seed real evaluations.
3. Expose simple metrics dashboard (count of 👍 vs 👎, common pain-points from comments).

---
_Prepared automatically after closing Sprint 0.17._ 