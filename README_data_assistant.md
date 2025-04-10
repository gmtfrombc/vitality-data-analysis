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

## Recent Updates

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

## Key Features

- **Natural Language Interface**: Ask questions about patient data in normal English
- **Interactive Visualizations**: Get charts and graphs that answer your specific questions
- **Data Insights**: Receive explanations and key statistics alongside visualizations
- **Example Queries**: Browse example questions to get started quickly

## How It Works

The Data Assistant uses:
1. Pandas for data processing and analysis
2. Panel for the interactive user interface
3. HoloViews/hvPlot for interactive visualizations
4. Pattern matching to interpret questions (can be replaced with an LLM)

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

### Weight Analysis
- "How many patients lost weight during the program?"
- "What percentage of active patients lost at least 10% body weight?"
- "Show weight change trends by age group"

### Health Metrics
- "What's the average A1C change for patients in the program?"
- "Show blood pressure trends over time"
- "Compare engagement scores to health outcomes"

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

## Future Enhancements

The current implementation uses pattern matching for demonstration purposes. For production use, consider these enhancements:

1. **LLM Integration**: Replace pattern matching with an LLM for more flexible understanding
2. **Memory**: Add conversation memory to allow follow-up questions
3. **Custom Functions**: Allow creating and saving custom analyses
4. **Export Features**: Add ability to export results to PDF or Excel
5. **Data Refresh**: Add controls to refresh cached data 