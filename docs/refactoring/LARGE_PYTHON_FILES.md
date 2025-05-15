# Large Python Files Analysis

This document lists Python files with more than 300 lines of code in the codebase, sorted by line count in descending order. This analysis helps identify potential candidates for refactoring to improve maintainability.

## Files Over 300 Lines

| File Path | Line Count | Summary |
|-----------|------------|---------|
| ./app/pages/data_assistant.py | 4049 | Core UI component for the data analysis assistant. Provides natural language query functionality, visualization, and results display. Contains methods for processing queries, generating analysis code, executing it in a sandbox, and displaying results. Many methods handle different stages of the analysis workflow. |
| ./app/ai_helper.py | 3522 | LLM integration layer that handles prompting and response processing. Contains methods for query intent classification, code generation, result interpretation, and fallback strategies. Includes specialized code generators for different analysis types (correlation, trend, distribution, etc.). |
| ./app/pages/data_validation.py | 1930 | UI component for validating and correcting patient data. Provides interfaces to identify and fix data quality issues, implement validation rules, and track corrections. Includes visualization of patient timelines and quality metrics. |
| ./app/pages/ai_assistant.py | 1715 | SQL generation assistant that converts natural language to database queries. Includes schema validation, query execution, SQL debugging, and results display. Has healthcare-specific term mapping. |
| ./tests/golden/synthetic_self_test.py | 1590 | Testing framework that generates synthetic data and runs a suite of predefined queries to verify assistant functionality. Creates controlled test cases with known ground truth answers and compares assistant output against expected results. |
| ./db_query.py | 1094 | Core database interaction module. Provides functions to query the SQLite database, retrieve patient information, and execute various data operations. Includes utilities for schema validation and path resolution. |
| ./app/pages/patient_view.py | 1041 | Patient detail view UI component. Displays comprehensive patient information including demographics, vitals, lab results, and metrics. Includes visualization of patient data trends. |
| ./app/utils/validation_engine.py | 843 | Engine for data validation rules. Implements logic to detect data quality issues based on configurable rules and metrics. Handles detection, reporting, and tracking of data issues. |
| ./app/utils/sandbox.py | 801 | Security sandbox for executing user-generated or AI-generated code safely. Implements resource limits, restricted imports, and safety checks to prevent harmful code execution. |
| ./app/utils/plots.py | 725 | Visualization library for creating various charts and plots. Implements histogram, line chart, bar chart, and other visualization types optimized for healthcare data. |
| ./app/utils/evaluation_framework.py | 706 | Framework for evaluating the performance of the AI assistant. Implements metrics tracking, result verification, and error analysis utilities. |
| ./app/components/evaluation_dashboard.py | 469 | Dashboard component for visualizing evaluation metrics of the AI assistant. Displays performance trends, error rates, and quality metrics. |
| ./app/utils/query_intent.py | 437 | Parser and classifier for natural language query intents. Converts user queries into structured representations of analysis intent (filters, metrics, groupings, etc.). |
| ./model_retraining.py | 418 | Script for retraining or fine-tuning models used in the application. Includes data preparation, training, and evaluation logic. |
| ./app/utils/advanced_correlation.py | 389 | Specialized correlation analysis utilities. Implements various correlation techniques beyond basic Pearson correlation, such as conditional correlations, time-series correlations, and multivariate analysis. |
| ./app/utils/metrics.py | 358 | Registry and computation logic for health metrics. Defines standardized metrics for patient health assessment and analysis. |
| ./tests/golden/test_enhanced_correlation.py | 326 | Test suite for advanced correlation analysis functionality. Verifies correlation computations across different data scenarios. |
| ./tests/golden/test_golden_queries.py | 320 | Test suite for the query engine against a set of golden standard queries. Ensures accuracy and consistency of results for predefined queries. |
| ./tests/conftest.py | 320 | pytest configuration and fixture definitions. Sets up test environments, mock data, and utilities used across multiple test files. |

## Refactoring Recommendations

Based on the analysis, the following files are primary candidates for refactoring:

1. **app/pages/data_assistant.py** (4049 lines): This file is excessively large and should be split into multiple modules:
   - UI component logic
   - Analysis workflow handling
   - Results formatting and visualization
   - Query processing

2. **app/ai_helper.py** (3522 lines): Should be decomposed into:
   - LLM interaction core
   - Intent processing
   - Code generation (separate modules for different analysis types)
   - Result interpretation

3. **app/pages/data_validation.py** (1930 lines): Could be split into:
   - UI component
   - Validation workflow
   - Correction handling
   - Reporting

4. **app/pages/ai_assistant.py** (1715 lines): Should separate:
   - UI component
   - SQL generation
   - Schema validation
   - Query execution and results

These refactorings will improve code maintainability, make testing easier, and allow for better separation of concerns. 