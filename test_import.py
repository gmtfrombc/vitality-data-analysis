#!/usr/bin/env python3
"""
Test importing the ai_helper module
"""

try:
    import app.ai_helper

    print("Successfully imported app.ai_helper")
    print(f"ai object: {app.ai_helper.ai}")
    print(f"get_data_schema function: {app.ai_helper.get_data_schema}")
except Exception as e:
    print(f"Error importing app.ai_helper: {str(e)}")
