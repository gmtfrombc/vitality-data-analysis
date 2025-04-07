# Metabolic Health Patient Data Analysis Application

A comprehensive web-based application for analyzing, visualizing, and querying patient metabolic health data. This application uses Panel for interactive dashboards, SQLite for data storage, and OpenAI for AI-assisted SQL query generation.

## Features

- **Dashboard**: Overview of program statistics and key metrics
- **Patient View**: Detailed patient information with tabs for:
  - Vital signs (weight, blood pressure)
  - Mental health assessments
  - Laboratory results
  - Metabolic health scores
- **AI SQL Assistant**: Generate SQL queries from natural language using OpenAI

## Setup

### Prerequisites

- Python 3.8+
- SQLite
- OpenAI API key (for AI SQL Assistant)

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Setting up OpenAI API Key

For the AI SQL Assistant to work, you need to set up an OpenAI API key as an environment variable. You can use our setup script to help with this:

```
python setup_env.py
```

Or manually set the environment variable:

- **macOS/Linux**:
  ```
  export OPENAI_API_KEY="your_api_key_here"
  ```

- **Windows**:
  ```
  set OPENAI_API_KEY=your_api_key_here
  ```

## Running the Application

To start the application:

```
python run.py
```

The application will be available at http://localhost:5006 (or a similar port if 5006 is in use).

## Application Structure

```
├── app/                  # Main application code
│   ├── components/       # Reusable UI components
│   ├── pages/            # Application pages
│   ├── utils/            # Utility functions
│   └── main.py           # Application entry point
├── run.py                # Script to run the application
├── setup_env.py          # Environment setup script
├── patient_data.db       # SQLite database
├── db_query.py           # Database query functions
└── README.md             # This file
```

## Usage

### Dashboard

The dashboard provides an overview of patient statistics, program metrics, and trends.

### Patient View

1. Select a patient from the dropdown
2. View detailed patient information across various tabs
3. Analyze trends in health metrics through interactive visualizations

### AI SQL Assistant

1. Enter a natural language question about the patient data
2. The AI will generate a SQL query to answer your question
3. Review the generated SQL query
4. Execute the query to see results

## Example Queries for AI Assistant

- "Show me all female patients with an engagement score above 80"
- "What is the average BMI for patients over 50 years old?"
- "List patients who have abnormal blood pressure readings (systolic > 140 or diastolic > 90)"
- "Show me lab results for HbA1c values greater than 6.5"
- "Find patients who have improved their mental health scores over time" 