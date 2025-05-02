Changelog
One-liner bullets so AI agents (and humans) can quickly diff what changed since their last session.
Use reverse-chronological order (latest on top).

[Unreleased] – ongoing
🐛 Scalar result support – DataAnalysisAssistant now accepts NumPy scalars; float64 crash fixed.
✨ Architecture docs – Added docs/ARCHITECTURE.md with module map & data flow.
📜 Cursor rules – Introduced .cursorrules for naming, tests, LLM usage.
🗺️ Roadmap canvas – Added ROADMAP_CANVAS.md and updated README.md link.
🤖 Hybrid AI integration – app/ai_helper.py and GPT-4 hooks in Data Assistant.
💾 Persistent saved questions – JSON file storage with load/save helpers.
🖼️ Pie chart fixes – Switched to hvplot(kind='pie').
🔧 UI tweaks – Save / reset buttons & delete-question flow.
🧩 Clarifying intent workflow – Assistant now detects vague queries, asks follow-up questions with a text input, and only proceeds when clarified; added heuristic, UI elements, and updated tests; fixed pandas truth-value errors.
Last updated: 2025-05-01

- [ ] Tech debt: silence Tornado loop warn in tests
- [ ] Upgrade to Pydantic v2 APIs