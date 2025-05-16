#!/usr/bin/env python3
"""
Quick test script for program completer/dropout analysis

This script demonstrates the functionality of the is_program_completer and 
is_program_dropout functions with sample data.
"""

import pandas as pd
import sys
from app.utils.patient_attributes import (
    Active,
    is_program_completer,
    is_program_dropout,
    get_patient_status,
)


def test_with_sample_data():
    """Test the program status functions with sample data."""
    # Create sample data with different provider visit counts
    sample_data = [
        {
            "id": 1,
            "active": Active.ACTIVE.value,
            "provider_visits": 2,
            "expected_status": "Active (2 visits)",
        },
        {
            "id": 2,
            "active": Active.ACTIVE.value,
            "provider_visits": 10,
            "expected_status": "Active (10 visits)",
        },
        {
            "id": 3,
            "active": Active.INACTIVE.value,
            "provider_visits": 7,
            "expected_status": "Program Completer",
        },
        {
            "id": 4,
            "active": Active.INACTIVE.value,
            "provider_visits": 10,
            "expected_status": "Program Completer",
        },
        {
            "id": 5,
            "active": Active.INACTIVE.value,
            "provider_visits": 3,
            "expected_status": "Program Dropout",
        },
        {
            "id": 6,
            "active": Active.INACTIVE.value,
            "provider_visits": 0,
            "expected_status": "Program Dropout",
        },
        {
            "id": 7,
            "active": Active.INACTIVE.value,
            "provider_visits": None,
            "expected_status": "Program Dropout",
        },
    ]

    # Create DataFrame
    df = pd.DataFrame(sample_data)

    # Add calculated columns
    df["is_completer"] = df.apply(
        lambda row: is_program_completer(row["active"], row["provider_visits"]), axis=1
    )
    df["is_dropout"] = df.apply(
        lambda row: is_program_dropout(row["active"], row["provider_visits"]), axis=1
    )
    df["status"] = df.apply(
        lambda row: get_patient_status(row["active"], row["provider_visits"]), axis=1
    )

    # Print results
    print("\nSAMPLE PATIENT STATUS ANALYSIS")
    print("=============================")
    print(
        f"{'ID':<3} {'Active':<7} {'Visits':<7} {'Completer':<10} {'Dropout':<10} {'Status':<20} {'Expected':<20} {'Match':<5}"
    )
    print("-" * 80)

    all_match = True

    for _, row in df.iterrows():
        visits = (
            str(row["provider_visits"])
            if row["provider_visits"] is not None
            else "None"
        )
        match = "✓" if row["status"] == row["expected_status"] else "✗"
        if row["status"] != row["expected_status"]:
            all_match = False

        print(
            f"{row['id']:<3} {row['active']:<7} {visits:<7} {row['is_completer']!s:<10} {row['is_dropout']!s:<10} {row['status']:<20} {row['expected_status']:<20} {match:<5}"
        )

    if all_match:
        print("\nAll status values match expected values! ✓")
        return 0
    else:
        print("\nSome status values do not match expected values! ✗")
        return 1


def main():
    print("Testing program completer/dropout functions...")
    return test_with_sample_data()


if __name__ == "__main__":
    sys.exit(main())
