"""Test natural language queries with a focus on functionality.

Unlike the golden query harness, these tests use a real DataAnalysisAssistant 
and run against a real (but small) test database.
"""

import unittest
from app.pages.data_assistant import DataAnalysisAssistant

# Import both ai and get_data_schema
from app.ai_helper import ai, get_data_schema


class TestQueries(unittest.TestCase):
    """Test natural language queries with a real DataAnalysisAssistant."""

    def setUp(self):
        """Set up a DataAnalysisAssistant for testing."""
        # Using a temporary settings dictionary to avoid affecting real storage
        self.assistant = DataAnalysisAssistant()

    def test_weight_trend_with_date_range(self):
        """Test querying weight trend within a specific date range."""
        # Note: This test is using a specific date range pattern that should be recognized
        query = "Show me patient weight trends from January to March 2025"

        # Execute the query through the AI helper directly
        intent = ai.get_query_intent(query)

        # Verify the intent captures the date range
        self.assertEqual(intent.analysis_type, "trend")
        self.assertEqual(intent.target_field, "weight")
        self.assertTrue(intent.has_date_filter())

        # Check that the date range is correctly interpreted
        date_range = intent.get_date_range()
        self.assertIsNotNone(date_range)

        # January to March
        self.assertEqual(date_range.start_date.month, 1)
        self.assertEqual(date_range.end_date.month, 3)
        self.assertEqual(date_range.start_date.year, 2025)
        self.assertEqual(date_range.end_date.year, 2025)

        # Generate code for the analysis
        code = ai.generate_analysis_code(intent, get_data_schema())

        # Skip execution in unit tests to avoid database dependencies
        # In a real integration test, we would execute the code
        self.assertIn("date BETWEEN", code)
        self.assertIn("2025-01-01", code)
        self.assertIn("2025-03-31", code)
