# Helper function to get data schema for code generation
def get_data_schema():
    """Return a description of the available data schema for code generation"""
    return {
        "patients": {
            "id": "string - Unique patient identifier",
            "first_name": "string - Patient's first name",
            "last_name": "string - Patient's last name",
            "birth_date": "datetime - Patient's date of birth",
            "gender": "string - 'F' for female, 'M' for male",
            "ethnicity": "string - Patient's ethnicity",
            "engagement_score": "integer - Score indicating patient engagement (0-100)",
            "program_start_date": "datetime - When patient enrolled in program",
            "program_end_date": "datetime - When patient completed program (null if still active)",
            "active": "integer - 1 if patient is active, 0 if inactive",
            "etoh": "integer - 1 if patient uses alcohol, 0 if not",
            "tobacco": "integer - 1 if patient uses tobacco, 0 if not",
            "glp1_full": "integer - 1 if patient is on GLP1 medication, 0 if not",
        },
        "vitals": {
            "vital_id": "integer - Unique vital record ID",
            "patient_id": "string - Patient ID (foreign key)",
            "date": "datetime - Date vital signs were recorded",
            "weight": "float - Weight in pounds",
            "height": "float - Height in inches",
            "bmi": "float - Body Mass Index",
            "sbp": "integer - Systolic blood pressure",
            "dbp": "integer - Diastolic blood pressure",
        },
        "labs": {
            "lab_id": "integer - Unique lab record ID",
            "patient_id": "string - Patient ID (foreign key)",
            "date": "datetime - Date lab was performed",
            "test_name": "string - Name of lab test",
            "value": "float - Result value",
            "unit": "string - Unit of measurement",
        },
        "scores": {
            "score_id": "integer - Unique score record ID",
            "patient_id": "string - Patient ID (foreign key)",
            "date": "datetime - Date score was recorded",
            "score_type": "string - Type of score (e.g., 'vitality_score')",
            "score_value": "integer - Score value",
        },
    }
