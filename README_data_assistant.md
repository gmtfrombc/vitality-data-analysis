# Data Analysis Assistant

## Overview

The Data Analysis Assistant is a natural language interface for analyzing patient data. It allows users to ask questions in plain English and get visualized responses with insights about the data.

## Features

### Modern AI-Powered Data Analysis Workflow

The Data Analysis Assistant follows a modern AI-powered workflow:

1. **Initial Setup**: Data is loaded into Python once at the beginning of your session
2. **Query Process**:
   - You ask a natural language question
   - AI asks clarifying questions and shows data samples
   - AI generates Python code with explanations
   - AI executes the code and shows results
3. **Validation is integrated throughout**:
   - AI shows intermediate results at each step
   - Code is visible and auditable
   - Visualizations help spot outliers or errors
   - Calculations are transparent with explanations

### User Interface

The Data Analysis Assistant interface includes:

- A text area for entering natural language queries
- Example queries that can be clicked to run immediately
- Tabs showing:
  - Results: The main findings from your query
  - Code: The Python code used to analyze the data
  - Visualization: Interactive charts and graphs of the results

## Using the Data Analysis Assistant

1. Navigate to the main application
2. Click on the "Data Analysis Assistant" tab
3. Enter your question in the text box or click one of the example queries
4. Review the results, code, and visualizations in the tabs below

## Example Questions

You can ask questions like:

- "How many active patients are in the program?"
- "What is the average weight of patients?"
- "Show me the distribution of BMI across all patients"
- "Compare blood pressure values for patients with high vs. normal A1C"
- "What percentage of patients showed improvement in their vital signs?"
- "Which patients have not had a visit in the last 3 months?"
- "Show me the top 5 ethnicities in our program"
- "Is there a correlation between weight and blood pressure over time?"
- "Compare the correlation between BMI and A1C across different age groups"

## Recent Updates

- **May 2025**: Implemented Synthetic "Golden-Dataset" Self-Test Loop for automated regression testing
- **May 2025**: Added top-N chart visualizations for categorical and numeric analyses
- **July 2025**: Enhanced correlation analysis with conditional and time-series capabilities
- **July 2025**: Implemented slot-based Smart Clarifier to ask specific, targeted questions when query intent is ambiguous
- **July 2025**: Added correlation matrix heat-map visualization with statistical significance testing
- **April 2025**: Implemented the new Data Analysis Assistant with natural language query capabilities
- **April 2025**: Removed the AI SQL Assistant module, replacing its functionality with the more comprehensive Data Analysis Assistant
- **April 2025**: Added visualization capabilities to the Data Analysis Assistant

## Technical Details

The Data Analysis Assistant uses a multi-step process:
1. Parse natural language to understand the question
2. Retrieve the relevant data from the database
3. Generate and run Python code to analyze the data
4. Create visualizations to present the results
5. Format and display the findings

All code is available for review in the "Code" tab to ensure transparency and auditability

### Architecture

The Data Analysis Assistant has been refactored into a modular architecture with clear separation of concerns:

1. **data_assistant.py**: Main coordinator module that orchestrates the end-to-end workflow
2. **ui.py**: Handles all UI components, widgets, and display functions
3. **engine.py**: Contains the core query processing logic, code generation, and execution
4. **analysis_helpers.py**: Provides data transformation, formatting, and visualization functions
5. **state.py**: Manages workflow state transitions and application state

This modular design improves maintainability, testability, and makes it easier to extend the assistant with new features.

## Key Features

- **Natural Language Interface**: Ask questions about patient data in normal English
- **Smart Clarification**: System identifies specific missing information and asks targeted questions
- **Intelligent Fallbacks**: Even ambiguous queries produce useful results through fallback templates
- **Interactive Visualizations**: Get charts and graphs that answer your specific questions
- **Data Insights**: Receive explanations and key statistics alongside visualizations
- **Example Queries**: Browse example questions to get started quickly
- **Advanced Correlation Analysis**: Supports conditional correlations by demographics and time-series correlations
- **Top-N Analysis**: Automatically generate bar charts for top/bottom ranking queries
- **Automated Quality Assurance**: Self-test system validates functionality against known datasets

## How It Works

The Data Assistant uses:
1. Pandas for data processing and analysis
2. Panel for the interactive user interface
3. HoloViews/hvPlot for interactive visualizations
4. GPT-4 for natural language understanding and query intent classification
5. Slot-based clarification system for handling ambiguous queries

## Advantages Over SQL-Based Approach

The Data Assistant has several advantages over the previous SQL-based approach:

1. **More Intuitive**: No need to generate or understand SQL queries
2. **Step-by-Step Analysis**: Shows the reasoning process, not just final results
3. **Visual Validation**: Charts help validate that the analysis is correct
4. **Interactive**: Results include both summaries and detailed data
5. **Expandable**: Easily add new analysis types without complex query generation

## Usage Examples

Here are some examples of questions you can ask:

### Demographics
- "How many active patients do we have?"
- "What is the gender distribution of our patients?"
- "Show me the age distribution of our patients"
- "What are the top 5 ethnicities in our program?"

### Weight Analysis
- "How many patients lost weight during the program?"
- "What percentage of active patients lost at least 10% body weight?"
- "Show weight change trends by age group"
- "Who are the top 10 patients with the most weight loss?"

### Health Metrics
- "What's the average A1C change for patients in the program?"
- "Show blood pressure trends over time"
- "Compare engagement scores to health outcomes"
- "Is there a correlation between BMI and blood pressure?"
- "How does the correlation between weight and A1C vary by gender?"

## Getting Started

1. Run the application with `python run.py`
2. Click on the "Data Analysis Assistant" tab
3. Type your question or select an example
4. Click "Analyze" to get results

## Extending the Assistant

You can extend the Data Assistant by:

1. Adding new analysis functions in the `_analyze_*` methods
2. Creating new pattern matching rules in the `analyze_query` method
3. Adding new example questions to the `data_examples.json` file
4. Adding new test cases to the self-test system

## Self-Test System

The Data Analysis Assistant includes a robust self-test system that:

1. Creates a synthetic database with controlled statistical properties
2. Runs predetermined queries with known correct answers
3. Compares results against expected values
4. Reports any discrepancies through desktop notifications
5. Maintains test history for regression analysis

To run the self-test manually:
```bash
./run_self_test.sh
```

Test results are stored in the `logs/self_test_*` directories with detailed reports.

## Future Enhancements

For future enhancements, consider:

1. **Memory**: Add conversation memory to allow follow-up questions
2. **Custom Functions**: Allow creating and saving custom analyses
3. **Export Features**: Add ability to export results to PDF or Excel
4. **Data Refresh**: Add controls to refresh cached data
5. **Help & Onboarding Tour**: Add interactive guidance for new users

## Importing New Patient JSON

A lightweight **Import Patient JSON** panel lives in the left sidebar.

1. Click *Choose File* and pick a de-identified patients JSON export (max 10 MB).
2. Press **Import JSON** – the button greys out and a tiny spinner shows while the ETL runs.
3. Once complete you'll see a toast like `Import complete – patients: 3, vitals: 5, …`.
4. Ask your question again – the data is immediately available.

Every import is logged to the `ingest_audit` table so we can track who/what file modified the DB. You can inspect it with:

```bash
sqlite3 patient_data.db 'SELECT * FROM ingest_audit ORDER BY imported_at DESC LIMIT 5;' | column -t
``` 