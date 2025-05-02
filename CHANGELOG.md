Changelog
One-liner bullets so AI agents (and humans) can quickly diff what changed since their last session.
Use reverse-chronological order (latest on top).

[Unreleased] – ongoing
🐛 Scalar result support – DataAnalysisAssistant now accepts NumPy scalars; float64 crash fixed.
✨ Happy-path integration smoke test for average weight scenario added; coverage climbs +2 %. Roadmap milestones updated.
✨ Architecture docs – Added docs/ARCHITECTURE.md with module map & data flow.
📜 Cursor rules – Introduced .cursorrules for naming, tests, LLM usage.
🗺️ Roadmap canvas – Added ROADMAP_CANVAS.md and updated README.md link.
🤖 Hybrid AI integration – app/ai_helper.py and GPT-4 hooks in Data Assistant.
💾 Persistent saved questions – JSON file storage with load/save helpers.
🖼️ Pie chart fixes – Switched to hvplot(kind='pie').
🔧 UI tweaks – Save / reset buttons & delete-question flow.
🧩 Clarifying intent workflow – Assistant now detects vague queries, asks follow-up questions with a text input, and only proceeds when clarified; added heuristic, UI elements, and updated tests; fixed pandas truth-value errors.
🐛 Safe raw_query assignment – Wrapped intent.raw_query set in DataAnalysisAssistant with try/except to prevent AttributeError and restore passing tests.
⏱️ Sandbox timeout (3 s) + import whitelist hardened; security test added.
📈 Deterministic templates expanded – median, distribution histogram, and monthly trend (AVG per YYYY-MM) with unit tests.
✅ Coverage gate 60 % enforced via .coveragerc omit list; current 72 %.
📚 Docs updated (README, ARCHITECTURE) for new templates & security lane.
✨ Roadmap Sprint plan committed – new milestones (golden query harness, richer templates, auto-viz) and backlog revamped (05-04).
✅ Golden-query harness completed – all 5 canonical cases pass; moved milestone to *done*.
🐛 Fixed `ModuleNotFoundError: app` by re-ordering sys.path injection before project imports in golden harness.
⬆️ Coverage surpasses 80 % (was 75 %); 34 tests green.
Last updated: 2025-05-05

- [ ] Tech debt: silence Tornado loop warn in tests
- [ ] Upgrade to Pydantic v2 APIs