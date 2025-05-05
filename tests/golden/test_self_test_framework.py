"""Tests for the synthetic self-test framework.

This module contains basic tests to ensure the synthetic self-test framework
is functioning correctly.
"""

from tests.golden.synthetic_self_test import (
    SyntheticDataGenerator,
    TestCase,
    SyntheticSelfTestLoop,
)
import os
import sys
import tempfile
import unittest
from pathlib import Path
import sqlite3

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestSyntheticSelfTestFramework(unittest.TestCase):
    """Test cases for the synthetic self-test framework."""

    def setUp(self):
        """Set up a temporary test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")

    def tearDown(self):
        """Clean up the temporary test environment."""
        self.temp_dir.cleanup()

    def test_synthetic_data_generator(self):
        """Test that the synthetic data generator creates valid data."""
        generator = SyntheticDataGenerator(self.db_path)
        generator.create_database()
        generator.generate_synthetic_data()

        # Verify database was created and contains expected tables
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ["patients", "vitals", "scores", "lab_results", "test_runs"]
        for table in expected_tables:
            self.assertIn(table, tables)

        # Check data was inserted
        cursor.execute("SELECT COUNT(*) FROM patients")
        patient_count = cursor.fetchone()[0]
        self.assertEqual(patient_count, 20)

        cursor.execute("SELECT COUNT(*) FROM vitals")
        vitals_count = cursor.fetchone()[0]
        self.assertGreater(vitals_count, 0)

        cursor.execute("SELECT COUNT(*) FROM scores")
        scores_count = cursor.fetchone()[0]
        self.assertGreater(scores_count, 0)

        conn.close()

    def test_test_case_class(self):
        """Test that the TestCase class works correctly."""
        # Create a test case
        test_case = TestCase(
            name="test", query="How many patients?", expected_result=42, tolerance=0.1
        )

        # Verify attributes
        self.assertEqual(test_case.name, "test")
        self.assertEqual(test_case.query, "How many patients?")
        self.assertEqual(test_case.expected_result, 42)
        self.assertEqual(test_case.tolerance, 0.1)
        self.assertIsNone(test_case.actual_result)
        self.assertFalse(test_case.passed)
        self.assertIsNone(test_case.error)

    def test_self_test_loop_initialization(self):
        """Test that the SyntheticSelfTestLoop initializes correctly."""
        test_loop = SyntheticSelfTestLoop(self.temp_dir.name)

        # Verify attributes
        self.assertEqual(test_loop.output_dir, Path(self.temp_dir.name))
        self.assertIsNotNone(test_loop.timestamp)
        self.assertEqual(
            test_loop.db_path,
            Path(self.temp_dir.name) / f"synthetic_test_{test_loop.timestamp}.db",
        )
        self.assertEqual(
            test_loop.report_path,
            Path(self.temp_dir.name) / f"test_report_{test_loop.timestamp}.json",
        )
        self.assertEqual(len(test_loop.test_cases), 0)


if __name__ == "__main__":
    unittest.main()
