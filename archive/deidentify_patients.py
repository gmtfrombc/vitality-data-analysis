import json
import sys


def deidentify_patient_data(
    input_filename="all_patients.json", output_filename="deidentified_patients.json"
):
    """
    Reads patient data from a JSON file, de-identifies it, and writes to a new file.

    Args:
        input_filename (str): The name of the input JSON file containing an array of patient objects.
        output_filename (str): The name of the output JSON file to store de-identified data.
    """
    fields_to_remove = [
        "email",
        "phone",
        "address",
        "city",
        "state",
        "zip_code",
        "insurance_group_id",
        "insurance_member_id",
        "auth0Id",  # Often contains identifying info or email
        "user_id",  # Often contains identifying info or email
    ]

    try:
        with open(input_filename, "r") as infile:
            patients = json.load(infile)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.", file=sys.stderr)
        return
    except json.JSONDecodeError:
        print(
            f"Error: Could not decode JSON from '{input_filename}'. Ensure it's a valid JSON array.",
            file=sys.stderr,
        )
        return
    except Exception as e:
        print(
            f"An unexpected error occurred while reading the file: {e}", file=sys.stderr
        )
        return

    if not isinstance(patients, list):
        print(
            f"Error: Expected a JSON array in '{input_filename}', but found {type(patients)}.",
            file=sys.stderr,
        )
        return

    deidentified_patients = []
    for patient in patients:
        if not isinstance(patient, dict):
            print(
                f"Warning: Skipping item in list as it's not a dictionary: {patient}",
                file=sys.stderr,
            )
            continue

        # Convert names to initials
        if (
            "first_name" in patient
            and isinstance(patient["first_name"], str)
            and patient["first_name"]
        ):
            patient["first_name"] = patient["first_name"][0].upper() + "."
        else:
            # Handle cases where name might be missing or not a string
            # Or None, or skip, depending on desired handling
            patient["first_name"] = "?"

        if (
            "last_name" in patient
            and isinstance(patient["last_name"], str)
            and patient["last_name"]
        ):
            patient["last_name"] = patient["last_name"][0].upper() + "."
        else:
            # Handle cases where name might be missing or not a string
            patient["last_name"] = "?"  # Or None, or skip

        # Remove sensitive fields
        for field in fields_to_remove:
            # Use pop with default None to avoid KeyError if field missing
            patient.pop(field, None)

        deidentified_patients.append(patient)

    try:
        with open(output_filename, "w") as outfile:
            # Use indent for readability
            json.dump(deidentified_patients, outfile, indent=4)
        print(f"Successfully de-identified {len(deidentified_patients)} records.")
        print(f"Output written to '{output_filename}'.")
    except Exception as e:
        print(f"An error occurred while writing the output file: {e}", file=sys.stderr)


if __name__ == "__main__":
    # You can change the input filename here if your actual file has a different name
    # Example: deidentify_patient_data(input_filename="all_patients.json")
    deidentify_patient_data()
