"""
Database Connector Utility

This module provides a connection to the db_query functions.
"""

import db_query
import sys
import logging
from pathlib import Path

# Add the parent directory to path so we can import db_query
sys.path.append(str(Path(__file__).parent.parent.parent))


logger = logging.getLogger(__name__)


class DBConnector:
    """Wrapper class for database operations"""

    @staticmethod
    def get_patients():
        """Get all patients"""
        return db_query.get_all_patients()

    @staticmethod
    def get_patient(patient_id):
        """Get a specific patient"""
        return db_query.get_patient_by_id(patient_id)

    @staticmethod
    def get_patient_vitals(patient_id, start_date=None, end_date=None):
        """Get vitals for a specific patient"""
        return db_query.get_patient_vitals(patient_id, start_date, end_date)

    @staticmethod
    def get_patient_mental_health(
        patient_id, assessment_type=None, start_date=None, end_date=None
    ):
        """Get mental health data for a specific patient"""
        return db_query.get_patient_mental_health(
            patient_id, assessment_type, start_date, end_date
        )

    @staticmethod
    def get_patient_labs(patient_id, test_name=None):
        """Get lab results for a specific patient"""
        return db_query.get_patient_labs(patient_id, test_name)

    @staticmethod
    def update_patient(patient_id, updates):
        """Update a patient record"""
        return db_query.update_patient(patient_id, updates)

    @staticmethod
    def search_patients(criteria):
        """Search for patients matching criteria"""
        return db_query.search_patients(criteria)

    @staticmethod
    def execute_query(query, params=None):
        """Execute a custom SQL query"""
        return db_query.query_dataframe(query, params)
