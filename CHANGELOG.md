Changelog
One-liner bullets so AI agents (and humans) can quickly diff what changed since their last session.
Use reverse-chronological order (latest on top).

[Unreleased] – ongoing
⚡️ Enhancement: Added Health Scores table to display Vitality Score and Heart Fit Score data alongside visit information
🐛 Fix: Normalized date formatting in Health Scores table to prevent duplicate entries due to inconsistent date formats
🐛 Fix: Fixed issue with NaN dates appearing in Health Scores table by implementing regex-based date extraction
✨ Feature: Patient Data-Quality Dashboard implemented with record quality badge, status tiles, timeline ribbon, issue table, and vitals/labs cards
🐛 Fix: Fixed missing `db_query` import in data_validation.py to enable patient detail view functionality
⚡️ Enhancement: Added timestamp tracking for data refresh to provide user feedback on data currency
⚡️ Enhancement: Simplified visualization handling for labs with tabular fallback for robustness
✨ Feature: Validation engine now supports `not_null_check` and `allowed_values_check` (categorical) with central dispatch
⚡️ Enhancement: `seed_validation_rules.py` converts frequency rows with `0`/`not_null` to presence rules (`not_null_check`)
⚡️ Enhancement: Data-Validation UI adds `categorical_check` filter option
⚡️ Enhancement: Snackbar notifications show when validation starts/completes; error toast on failure
⚡️ Enhancement: Patient list buttons now display `patient_id` prefix for quick identification
🛑 Change: Insurance & provider spring fields temporarily skipped via `SKIPPED_FIELDS` until UI support
🐛 Fix: Replaced invalid `sizing_mode='fixed-width'` with `fixed` in Data-Validation UI
🐛 Fix: Removed unsupported `.on_click` on `pn.Row`; patient list now uses interactive buttons
🐛 Fix: AttributeError in filter callback resolved by assigning parameters directly
🐛 Fix: Runtime plots now use real hvplot; safeguarded `.opts` call – resolves `_OptsProxy` errors
⚡️ Enhancement: Data-Validation dashboard loads correctly; patient filtering UI operational (needs refinement)
🐛 Fix: Resolved timezone-aware datetime comparison issues in validation system
🐛 Fix: Improved NaT handling and date parsing in data validation system
🐛 Fix: Fixed Panel widget parameter naming conflicts in data validation UI
✨ Feature: Created robust date handling utility in app/utils/date_helpers.py
⚡️ Enhancement: Added graceful error handling and fallbacks in run.py
⚡️ Enhancement: Improved visualization error handling with fallback views
🔄 Changing documentation summary naming convention from dates to sequential numbering
✨ Feature: Data Quality & Validation System (#WS-7, #data-quality)
✅ Implemented data validation system with rule-based validation engine
✅ Created database migration for validation tables (008_data_validation_tables.sql)
✅ Added patient-centric validation UI with timeline visualization
✅ Implemented initial set of validation rules for vital measurements
✅ Integrated database migrations into application startup for seamless updates
🧩 Updating roadmap to include data validation capabilities
🧩 Planning validation rule schema for patient data
🧩 Designing patient-centric validation interface
✨ Feature: Assistant Evaluation Framework (#WS-6, #feedback)
✅ Created comprehensive evaluation framework with multi-dimensional metrics tracking
✅ Implemented satisfaction, response quality, intent accuracy, and visualization metrics
✅ Built interactive dashboard for visualizing assistant performance metrics
✅ Added automated metrics calculation script with scheduling capability
✅ Created database migration for assistant_metrics table
✅ Added unit tests with >90% coverage for evaluation framework
✨ Feature: Enhanced Continuous Feedback & Evaluation System (#WS-6, #feedback)
✅ Added lightweight UI feedback widget for real-time user feedback collection
🧩 Planning Assistant Evaluation Framework with multi-faceted metrics tracking
🧩 Designing enhanced Self-Test Loop with AI-driven test case generation
🧩 Creating performance metrics dashboard for objective assistant evaluation
🧩 Implementing A/B testing capability for comparing clarification approaches
✨ Feature: Extended Statistical Templates (#WS-2, #AI) - Five new analysis templates for complex data scenarios
🧩 Added Percentile Analysis template - Divides data into percentiles for metric analysis with visualization
🧩 Added Outlier Analysis template - Identifies statistical outliers with demographic breakdown
🧩 Added Frequency Analysis template - Analyzes categorical variable distributions with weighting options
🧩 Added Seasonality Analysis template - Detects patterns by month/day/hour in time-series data
🧩 Added Change Point Analysis template - Identifies significant trend changes over time 
✅ Enhanced _generate_dynamic_code_for_complex_intent function to utilize all templates
🧪 Verified all templates maintain 71.67% test coverage with 214 passing tests
✨ Feature: Synthetic "Golden-Dataset" Self-Test Loop (#QA) - Automated regression testing for the assistant
🧩 Created framework for testing against synthetic dataset with known statistical properties
🧩 Implemented daily runner with notification system for continuous monitoring
🧩 Added 10 test cases covering key query types and analysis patterns
🧪 Developed unit tests for the self-test framework components
📚 Added comprehensive documentation in README_SELF_TEST.md
🛠️ Fixed test suite issues – Added textwrap to sandbox whitelist, fixed KeyError in test_tricky_pipeline.py
✅ Tests now pass with 71.67% coverage (above 60% requirement)
✅ Added automated notification system with AppleScript alerts
🔧 Created `handoff.sh` script to automate documentation updates and assistant transitions
🔧 Added nightly cron job setup with desktop notification system
⚙️ Updated README with documentation on self-test framework and developer workflow

✨ Feature: Auto-Visualization Template Coverage Completed (#WS-2) - Added support for top-N chart visualization
🧩 Enhanced auto_viz_mapper.py to create bar chart visualizations for top-N analysis results
🧩 Updated AI helper to generate code with visualization hooks for top-N templates
🧩 Modified data_assistant.py to display top-N charts with formatted markdown tables
🧪 Added comprehensive tests including unit tests and golden test for top-N visualization
🔧 Fixed test failures in correlation analysis by implementing proper HoloViews mocking in test modules
🔧 Fixed string case issues for chart titles
🛠️ Fixed string formatting issues in _generate_correlation_code function in app/ai_helper.py
✨ Feature: Enhanced Correlation Analysis Capabilities (#WS-2, #WS-4) - Advanced correlation tools for deeper insights
🧩 Added conditional correlation analysis by demographic variables in `app/utils/advanced_correlation.py`
🧩 Added time-series correlation analysis to track relationship changes over time
🧩 Implemented specialized visualizations for conditional and time-series correlations
🧪 Added comprehensive tests for advanced correlation functionality in `tests/utils/test_advanced_correlation.py`
🧪 Added integration tests to verify AI-assisted correlation analysis in `tests/golden/test_enhanced_correlation.py`
✨ Feature: Slot-based Smart Clarifier for intent engine hardening (#WS-2, #WS-4) - Identifies specific missing information in queries 
🧩 Added MissingSlot and SlotType for focused, structured clarification requests in `app/utils/intent_clarification.py`
🛠️ Implemented generic fallback template for low-confidence queries with data schema inspection and relevant visualizations
🧪 Added tests for slot-based clarifier functionality in `tests/utils/test_intent_clarification.py`
✨ Feature: Correlation matrix heat-map template (#WS-4) – Supports 2+ metrics with visualized p-values
🧩 Added `compute_correlation()`
🐛 Fix: Excessive logging during validation reduced (DEBUG level)
✨ Feature: Patient list now refreshes dynamically via `_refresh_patient_list` container; filter changes reflected instantly with concise INFO log
🧪 Chore: groundwork laid for unit-tests around patient list refresh performance
✨ Feature: Ring 1 Data-Validation MVP – Validation Inbox, YAML Rule Catalogue, Nightly validator job
🛠️ Chore: Updated ROADMAP_CANVAS with new WS-7 milestones (Validation Inbox & YAML rule loader)
✨ Feature: Validation Inbox now interactive – patient detail panel loads on selection with timeline & correction form
⚡️ Enhancement: Loading spinner added to patient list refresh; optional import guard for older Panel versions
🐛 Fix: AttributeError when opening correction form (param .value misuse) resolved
🐛 Fix: Mental-health plot creation variable scope bug fixed (individual_plot)
🛠️ Chore: `seed_validation_rules.py` script created; converts CSV → YAML and loads rules into DB
✨ Feature: Reload Rules admin button in Data-Validation dashboard – one-click seeding from CSV → YAML → DB
⚡️ Enhancement: Patient list counts now use DISTINCT rule IDs (shows real issue count)
⚡️ Enhancement: Selected patient row highlights; detail pane auto-scrolls to header
🐛 Fix: Height rule duplication removed; old cm-based rule deactivated
🐛 Fix: Weight range & frequency issues suppressed when BMI already flagged; weight-only rules set inactive
⚡️ Enhancement: Validation action clears previous results before re-run, preventing stale issues