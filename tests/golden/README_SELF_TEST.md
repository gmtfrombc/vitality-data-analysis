# Synthetic Golden-Dataset Self-Test Loop

## Overview

The Synthetic Golden-Dataset Self-Test Loop is a quality assurance framework for the Data Analysis Assistant. It provides an automated way to test the "ask anything" capability against a controlled dataset with known ground truth answers.

This system helps detect:
- Regressions in the AI's ability to understand natural language queries
- Errors in code generation or execution
- Discrepancies in statistical analysis results
- Missing visualizations or incorrect interpretation

By running these tests daily, the development team can quickly identify issues before they impact users.

## How It Works

The self-test system follows these steps:

1. **Create Synthetic Database**: Generates a tiny SQLite database with controlled patient data that has known statistical properties
2. **Define Test Cases**: Creates a set of natural language queries with predetermined expected results
3. **Run the Pipeline**: Processes each query through the full Data Analysis Assistant pipeline:
   - Parse query intent
   - Generate analysis code
   - Execute code
   - Compare results with expected ground truth
4. **Generate Report**: Creates a detailed report of test results, highlighting any discrepancies
5. **Track Performance**: Stores results in the database to monitor changes over time

## Key Features

- **Controlled Environment**: Tests run in isolation with synthetic data, eliminating external dependencies
- **Reproducible Results**: Deterministic data generation with fixed random seed ensures consistent test conditions
- **Tolerance Settings**: Numerical comparisons use relative tolerance to handle floating-point differences
- **Comprehensive Validation**: Tests various query types and analysis patterns
- **Automated Scheduling**: Can be run daily via cron job or systemd timer
- **Notification System**: Optional email alerts when tests fail

## Running the Tests

### Manual Execution

```bash
# Run with default settings
python -m tests.golden.synthetic_self_test

# Specify output directory
python -m tests.golden.synthetic_self_test --output-dir=/path/to/results
```

### Scheduled Daily Run

```bash
# Set up as a daily job
python -m tests.golden.run_daily_self_test --notify --recipients=team@example.com
```

### Setting Up Environment Variables for Notifications

If using email notifications, set the following environment variables:

```bash
export SMTP_SERVER=smtp.example.com
export SMTP_PORT=587
export SMTP_USER=username
export SMTP_PASSWORD=password
export NOTIFICATION_SENDER=selftest@example.com
```

## Test Cases

The self-test includes the following query types:

1. **Basic Aggregations**: Count, average, sum, etc.
2. **Filters and Conditions**: Gender, age, activity status
3. **Group By Analysis**: Breakdowns by demographics
4. **Time Series**: Monthly trends and changes
5. **Correlations**: Relationships between metrics
6. **Visualizations**: Chart and graph generation

Each test has a pre-calculated expected result based on the synthetic data properties.

## Adding New Test Cases

To add a new test case, update the `generate_test_cases` method in `SyntheticSelfTestLoop`:

```python
TestCase(
    name="new_test_name",
    query="Your natural language query here",
    expected_result=123.45,  # or a dictionary for more complex results
    tolerance=0.05  # 5% tolerance for numerical comparisons
)
```

## Understanding Test Reports

The test report JSON includes:

- **timestamp**: When the test was run
- **total_tests**: Number of test cases
- **passed_tests**: Number of tests that passed
- **success_rate**: Percentage of tests that passed
- **tests**: Detailed information about each test:
  - **name**: Test identifier
  - **query**: Natural language question
  - **expected_result**: Ground truth answer
  - **actual_result**: What the assistant returned
  - **passed**: Boolean success indicator
  - **error**: Description of failure (if any)

## Integrating with CI/CD

This self-test can be integrated into CI/CD pipelines to ensure that changes don't break existing functionality:

```yaml
# Example GitHub Action
name: Daily Self-Test
on:
  schedule:
    - cron: '0 0 * * *'  # Run at midnight daily
jobs:
  self-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run self-test
        run: python -m tests.golden.run_daily_self_test
      - name: Archive test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test_results/
```

## Troubleshooting

Common issues and solutions:

- **Database connection errors**: Check that SQLite is available and properly configured
- **OpenAI API errors**: Ensure the OPENAI_API_KEY environment variable is set
- **Unexpected result types**: Ensure the expected_result in the test case matches the actual result type
- **Notification failures**: Verify SMTP settings and recipient email addresses

## Future Enhancements

Planned improvements to the self-test framework:

1. **Dynamic Test Generation**: Automatically generate test cases based on query patterns
2. **More Comprehensive Coverage**: Expand test cases to cover all analysis types and edge cases
3. **Performance Metrics**: Track execution time and resource usage alongside result accuracy
4. **Web Dashboard**: Visual interface to view test history and trends 