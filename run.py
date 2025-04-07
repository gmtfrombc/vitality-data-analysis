#!/usr/bin/env python3
"""
Run script for the Metabolic Health Data Analysis application.

This script launches the Panel web application.
"""

import os
import sys
from app.main import app

if __name__ == "__main__":
    print("Starting Metabolic Health Data Analysis app...")
    app.show()
