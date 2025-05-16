# Data Assistant HTML Visualization Testing Guide

## Overview

This document provides instructions for testing the new HTML-based visualization capabilities in the Data Analysis Assistant. These visualizations are designed to work within the sandbox security restrictions, providing users with visual representations of their data analysis results.

## Testing Steps

### 1. Histogram Visualization Test

1. Launch the Data Analysis Assistant
2. Enter the query: `Show me a distribution of BMI values for all patients`
3. Click "Run Query"
4. Verify in the Results tab that you see a numerical summary of BMI statistics
5. Click on the "Visualization" tab
6. Verify that a histogram appears showing the distribution of BMI values
7. Confirm the histogram has labeled bins and a title

### 2. Bar Chart Visualization Test

1. Launch the Data Analysis Assistant
2. Enter the query: `Count patients by gender`
3. Click "Run Query"
4. Verify in the Results tab that you see counts for each gender
5. Click on the "Visualization" tab
6. Verify that a bar chart appears showing patient counts by gender
7. Confirm the bars are correctly labeled and proportional to the counts

### 3. Line Chart Visualization Test

1. Launch the Data Analysis Assistant
2. Enter the query: `Show me the trend of average weight over 6-month periods from 2022 to 2024`
3. Click "Run Query"
4. Verify in the Results tab that you see weight averages for different time periods
5. Click on the "Visualization" tab
6. Verify that a line chart appears showing the weight trend over time
7. Confirm the chart has labeled data points and axes

## What to Look For

When testing these visualizations, look for:

- **Appearance**: Charts should be clean and well-formatted with appropriate labels
- **Data Accuracy**: Visual representation should match the numerical results
- **Responsiveness**: Charts should load and display quickly
- **Error Handling**: If data is sparse or missing, you should see appropriate fallback messages rather than errors

## Troubleshooting

If visualizations don't appear properly:

1. Check the browser console for any JavaScript errors
2. Verify that the query returned valid data in the Results tab
3. Try a different query that might produce a simpler dataset
4. Refresh the page and try again

## Next Steps

After verifying these basic visualization types, feel free to explore more complex queries that might generate more intricate visualizations, such as:

- Correlations between different metrics
- Multi-series comparisons
- Time-based trend analysis with different time granularities

Please report any issues or suggestions for improvement to the development team. 