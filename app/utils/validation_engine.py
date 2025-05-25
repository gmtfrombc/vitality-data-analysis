"""
Validation Engine for Patient Data

This module provides a simple, extensible framework for validating patient data
against a set of rules and identifying potential data quality issues.
"""

import json
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import logging

# Import the updated date helpers
from app.utils.date_helpers import (
    safe_date_diff_days,
    format_date_for_display,
    convert_df_dates,
    get_now,
)

# Set up logging
logger = logging.getLogger(__name__)


class ValidationRule:
    """Simple class to represent a validation rule."""

    def __init__(self, rule_dict: Dict[str, Any]):
        """
        Initialize a validation rule from a dictionary.

        Args:
            rule_dict: Dictionary containing rule parameters
                - rule_id: Unique identifier for the rule
                - description: Human readable description
                - rule_type: Type of rule (missing_data, range_check, consistency_check)
                - validation_logic: Logic to apply (date_diff_check, range_check, etc.)
                - parameters: Dictionary of parameters specific to this rule
                - severity: How serious is a violation (info, warning, error)
        """
        self.rule_id = rule_dict.get("rule_id", "")
        self.description = rule_dict.get("description", "")
        self.rule_type = rule_dict.get("rule_type", "")
        self.validation_logic = rule_dict.get("validation_logic", "")
        self.parameters = rule_dict.get("parameters", {})
        self.severity = rule_dict.get("severity", "info")

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary for storage."""
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "rule_type": self.rule_type,
            "validation_logic": self.validation_logic,
            "parameters": self.parameters,
            "severity": self.severity,
        }

    def __str__(self) -> str:
        return f"{self.rule_id}: {self.description} ({self.severity})"


class ValidationResult:
    """Class to represent a validation issue found."""

    def __init__(
        self,
        rule_id: str,
        patient_id: str,
        issue_description: str,
        field_name: Optional[str] = None,
        status: str = "open",
    ):
        """
        Initialize a validation result.

        Args:
            rule_id: ID of the rule that generated this result
            patient_id: ID of the patient with the issue
            issue_description: Human readable description of the issue
            field_name: Name of the field with the issue (if applicable)
            status: Current status of the issue (open, reviewed, corrected, ignored)
        """
        self.rule_id = rule_id
        self.patient_id = patient_id
        self.field_name = field_name
        self.issue_description = issue_description
        self.status = status
        self.detected_at = get_now()  # Use new helper to get consistent datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for storage."""
        return {
            "rule_id": self.rule_id,
            "patient_id": self.patient_id,
            "field_name": self.field_name,
            "issue_description": self.issue_description,
            "status": self.status,
            "detected_at": self.detected_at.isoformat(),
        }


class ValidationEngine:
    """
    Engine for applying validation rules to patient data.
    """

    # Fields whose validation rules are temporarily disabled until UI supports edits
    SKIPPED_FIELDS = {
        "insurance_plan",
        "insurance_type",
        "insurance_phone",
        "provider_id",
        "health_coach_id",
    }

    def __init__(self, db_path: str):
        """
        Initialize the validation engine with a database connection.

        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self.rules = []
        # logger.info(f"Found {result_count} existing validation results. Skipping initial validation.")
        # logger.info("Validation engine initialized successfully")

    def load_rules_from_db(self) -> List[ValidationRule]:
        """
        Load validation rules from the database.

        Returns:
            List of ValidationRule objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT rule_id, description, rule_type, validation_logic, parameters, severity FROM validation_rules WHERE is_active = 1"
            )
            rows = cursor.fetchall()

            rules = []
            for row in rows:
                rule_dict = {
                    "rule_id": row[0],
                    "description": row[1],
                    "rule_type": row[2],
                    "validation_logic": row[3],
                    "parameters": json.loads(row[4]),
                    "severity": row[5],
                }
                rules.append(ValidationRule(rule_dict))

            self.rules = rules
            conn.close()
            return rules

        except Exception as e:
            logger.error(f"Error loading rules from database: {e}")
            return []

    def save_rule_to_db(self, rule: ValidationRule) -> bool:
        """
        Save a validation rule to the database.

        Args:
            rule: ValidationRule object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if rule already exists
            cursor.execute(
                "SELECT 1 FROM validation_rules WHERE rule_id = ?", (rule.rule_id,)
            )
            exists = cursor.fetchone() is not None

            if exists:
                # Update existing rule
                cursor.execute(
                    "UPDATE validation_rules SET description = ?, rule_type = ?, validation_logic = ?, parameters = ?, severity = ?, updated_at = CURRENT_TIMESTAMP WHERE rule_id = ?",
                    (
                        rule.description,
                        rule.rule_type,
                        rule.validation_logic,
                        json.dumps(rule.parameters),
                        rule.severity,
                        rule.rule_id,
                    ),
                )
            else:
                # Insert new rule
                cursor.execute(
                    "INSERT INTO validation_rules (rule_id, description, rule_type, validation_logic, parameters, severity) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        rule.rule_id,
                        rule.description,
                        rule.rule_type,
                        rule.validation_logic,
                        json.dumps(rule.parameters),
                        rule.severity,
                    ),
                )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error saving rule to database: {e}")
            return False

    def save_validation_result(self, result: ValidationResult) -> bool:
        """
        Save a validation result to the database.

        Args:
            result: ValidationResult object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO validation_results (rule_id, patient_id, field_name, issue_description, status, detected_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    result.rule_id,
                    result.patient_id,
                    result.field_name,
                    result.issue_description,
                    result.status,
                    result.detected_at.isoformat(),
                ),
            )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error saving validation result: {e}")
            return False

    def get_patient_data(self, patient_id: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Get demographic and vitals data for a specific patient.

        Args:
            patient_id: ID of the patient

        Returns:
            Tuple of (demographics DataFrame, vitals DataFrame)
        """
        try:
            conn = sqlite3.connect(self.db_path)

            # Get patient demographics - fix column name from patient_id to id
            demographics = pd.read_sql_query(
                "SELECT * FROM patients WHERE id = ?", conn, params=(patient_id,)
            )

            # Get patient vitals
            vitals = pd.read_sql_query(
                "SELECT * FROM vitals WHERE patient_id = ?", conn, params=(patient_id,)
            )

            # Log info for debugging
            if not vitals.empty:
                logger.debug(
                    f"Vitals data for patient {patient_id}: {len(vitals)} rows"
                )
                logger.debug(f"Vitals columns: {list(vitals.columns)}")
                logger.debug(f"Sample vitals data: {vitals.head(1).to_dict('records')}")

                # Use our new helper to convert date strings to datetime objects
                # Important: set utc=False to maintain tz-naive datetimes
                if "date" in vitals.columns:
                    vitals = convert_df_dates(vitals, ["date"], utc=False)

            conn.close()
            return demographics, vitals

        except Exception as e:
            logger.error(f"Error retrieving patient data: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def validate_patient(self, patient_id: str) -> List[ValidationResult]:
        """
        Validate a specific patient against all active rules.

        Args:
            patient_id: ID of the patient to validate

        Returns:
            List of ValidationResult objects for issues found
        """
        # Make sure rules are loaded
        if not self.rules:
            self.load_rules_from_db()

        # Get patient data
        demographics, vitals = self.get_patient_data(patient_id)

        if demographics.empty:
            logger.error(f"No data found for patient {patient_id}")
            return []

        results = []

        # Apply each rule
        for rule in self.rules:
            field_name = (
                rule.parameters.get("field")
                if isinstance(rule.parameters, dict)
                else None
            )
            # Skip temporarily disabled fields
            if field_name and field_name in self.SKIPPED_FIELDS:
                continue

            logic = rule.validation_logic

            try:
                if logic == "date_diff_check":
                    # Skip weight frequency checks; BMI already covers adequacy of measurement timing
                    if rule.parameters.get("field") == "weight":
                        continue
                    results.extend(
                        self._check_measurement_frequency(
                            patient_id,
                            vitals,
                            rule.parameters.get("field", ""),
                            rule.parameters.get("max_days_between", 60),
                            rule,
                        )
                    )
                elif logic == "range_check":
                    results.extend(
                        self._check_value_range(
                            patient_id,
                            vitals,
                            rule.parameters.get("field", ""),
                            rule.parameters.get("min_value"),
                            rule.parameters.get("max_value"),
                            rule,
                        )
                    )
                elif logic == "not_null_check":
                    results.extend(
                        self._check_not_null(
                            patient_id,
                            demographics,
                            vitals,
                            rule.parameters.get("field", ""),
                            rule,
                        )
                    )
                elif logic == "allowed_values_check":
                    results.extend(
                        self._check_allowed_values(
                            patient_id,
                            demographics,
                            vitals,
                            rule.parameters.get("field", ""),
                            rule.parameters.get("allowed_values", []),
                            rule,
                        )
                    )
                    # Optionally enforce presence
                    if rule.parameters.get("not_null"):
                        results.extend(
                            self._check_not_null(
                                patient_id,
                                demographics,
                                vitals,
                                rule.parameters.get("field", ""),
                                rule,
                            )
                        )
                elif logic == "conditional_not_null_check":
                    results.extend(
                        self._check_conditional_not_null(
                            patient_id,
                            demographics,
                            vitals,
                            rule.parameters.get("field", ""),
                            rule.parameters.get("required_if", []),
                            rule,
                        )
                    )
                else:
                    # Unsupported logic – skip for now
                    continue
            except Exception as exc:
                logger.error(
                    "Rule %s failed for patient %s: %s", rule.rule_id, patient_id, exc
                )

        # Save results to database
        for result in results:
            self.save_validation_result(result)

        return results

    def _check_measurement_frequency(
        self,
        patient_id: str,
        vitals: pd.DataFrame,
        field: str,
        max_days: int,
        rule: ValidationRule,
    ) -> List[ValidationResult]:
        """
        Check if a measurement is being taken frequently enough.

        Args:
            patient_id: ID of the patient
            vitals: DataFrame of vital measurements
            field: Name of the field to check
            max_days: Maximum allowed days between measurements
            rule: The validation rule being applied

        Returns:
            List of ValidationResult objects for issues found
        """
        results = []

        # Skip if field doesn't exist or no data
        if field not in vitals.columns or vitals.empty:
            return results

        # Filter for rows where this field is not null
        field_data = vitals[vitals[field].notnull()].copy()

        if field_data.empty:
            # No measurements at all
            result = ValidationResult(
                rule_id=rule.rule_id,
                patient_id=patient_id,
                field_name=field,
                issue_description=f"No {field} measurements found for patient",
            )
            results.append(result)
            return results

        # Ensure date column is datetime type
        if "date" in field_data.columns:
            # Convert dates without timezone information (keep tz-naive)
            field_data = convert_df_dates(field_data, ["date"], utc=False)

        # Sort by date
        field_data = field_data.sort_values("date")

        # Check gaps between consecutive measurements
        prev_date = None
        for _, row in field_data.iterrows():
            current_date = row["date"]

            # Skip rows with invalid dates
            if pd.isna(current_date):
                continue

            if prev_date is not None:
                # Use our safe_date_diff_days function to avoid timezone issues
                gap_days = safe_date_diff_days(current_date, prev_date)

                if gap_days and gap_days > max_days:
                    result = ValidationResult(
                        rule_id=rule.rule_id,
                        patient_id=patient_id,
                        field_name=field,
                        issue_description=f"Gap of {gap_days} days between {field} measurements (max allowed: {max_days})",
                    )
                    results.append(result)

            prev_date = current_date

        # Check if it's been too long since the last measurement
        if not field_data.empty:
            # Get the last valid date
            last_dates = field_data["date"].dropna()
            if not last_dates.empty:
                last_date = last_dates.max()

                # Format using our helper for consistent display
                last_date_str = format_date_for_display(last_date)

                # Get current time as tz-naive for consistent comparison
                now = get_now()

                # Calculate days since last measurement using safe function
                days_since_last = safe_date_diff_days(now, last_date)

                if days_since_last and days_since_last > max_days:
                    result = ValidationResult(
                        rule_id=rule.rule_id,
                        patient_id=patient_id,
                        field_name=field,
                        issue_description=f"No {field} measurement in {days_since_last} days (last: {last_date_str})",
                    )
                    results.append(result)

        return results

    def _check_value_range(
        self,
        patient_id: str,
        vitals: pd.DataFrame,
        field: str,
        min_value: Optional[float],
        max_value: Optional[float],
        rule: ValidationRule,
    ) -> List[ValidationResult]:
        """
        Check if values for a field are within the expected range.

        Args:
            patient_id: ID of the patient
            vitals: DataFrame of vital measurements
            field: Name of the field to check
            min_value: Minimum allowed value (None if no minimum)
            max_value: Maximum allowed value (None if no maximum)
            rule: The validation rule being applied

        Returns:
            List of ValidationResult objects for issues found
        """
        results = []

        # Skip if field doesn't exist or no data
        if field not in vitals.columns or vitals.empty:
            return results

        # Filter for rows where this field is not null
        field_data = vitals[vitals[field].notnull()].copy()

        if field_data.empty:
            return results

        # Check for values outside the allowed range
        for _, row in field_data.iterrows():
            value = row[field]
            date = row["date"]

            # Skip rows with invalid dates
            if pd.isna(date):
                continue

            # Format date for display using our helper
            date_str = format_date_for_display(date)

            # ---------------------------------------------
            # Suppress redundant weight issues
            # If the weight is high and BMI is already outside
            # its own allowed range we skip flagging weight.
            # This prevents double-counting of essentially the
            # same clinical problem.
            # ---------------------------------------------
            if field == "weight" and "bmi" in row and pd.notna(row["bmi"]):
                bmi_val = row["bmi"]
                # Hard-coded to current rule limits (12-70) until we
                # introduce dynamic cross-rule look-ups.
                if bmi_val < 12 or bmi_val > 70:
                    # Skip emitting separate weight issue – BMI already flags
                    continue

            # Convert to float if possible
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            if min_value is not None and value < min_value:
                result = ValidationResult(
                    rule_id=rule.rule_id,
                    patient_id=patient_id,
                    field_name=field,
                    issue_description=f"{field} value {value} on {date_str} is below minimum {min_value}",
                )
                results.append(result)

            if max_value is not None and value > max_value:
                result = ValidationResult(
                    rule_id=rule.rule_id,
                    patient_id=patient_id,
                    field_name=field,
                    issue_description=f"{field} value {value} on {date_str} is above maximum {max_value}",
                )
                results.append(result)

        return results

    def _check_not_null(
        self,
        patient_id: str,
        demographics: pd.DataFrame,
        vitals: pd.DataFrame,
        field: str,
        rule: ValidationRule,
    ) -> List[ValidationResult]:
        """Ensure at least one non-null value exists for the field in either table."""
        results: List[ValidationResult] = []

        series = pd.Series(dtype="object")
        if field in demographics.columns:
            series = demographics[field]
        elif field in vitals.columns:
            series = vitals[field]

        # series may be multi-row; consider non-null overall
        if series.empty or series.dropna().empty:
            results.append(
                ValidationResult(
                    rule_id=rule.rule_id,
                    patient_id=patient_id,
                    field_name=field,
                    issue_description=f"{field} is missing for patient",
                )
            )
        return results

    def _check_allowed_values(
        self,
        patient_id: str,
        demographics: pd.DataFrame,
        vitals: pd.DataFrame,
        field: str,
        allowed_values: List[Any],
        rule: ValidationRule,
    ) -> List[ValidationResult]:
        """Validate that all values fall inside allowed set."""
        results: List[ValidationResult] = []

        if allowed_values is None:
            # nothing to validate
            return results

        # Build combined series from both tables if field exists
        values = []
        if field in demographics.columns:
            values.extend(demographics[field].dropna().unique().tolist())
        if field in vitals.columns:
            values.extend(vitals[field].dropna().unique().tolist())

        # If no data present we treat separately with not_null rule
        if not values:
            return results

        for val in values:
            # Canonicalise to string for comparison
            if str(val) not in [str(a) for a in allowed_values]:
                results.append(
                    ValidationResult(
                        rule_id=rule.rule_id,
                        patient_id=patient_id,
                        field_name=field,
                        issue_description=f"{field} value '{val}' not in allowed set {allowed_values}",
                    )
                )
        return results

    def _check_conditional_not_null(
        self,
        patient_id: str,
        demographics: pd.DataFrame,
        vitals: pd.DataFrame,
        field: str,
        conditions: list,
        rule: ValidationRule,
    ) -> List[ValidationResult]:
        """Enforce not-null only when *any* condition in *conditions* is true.

        Each condition dict supports keys: field, operator, value. Supported
        operators: ==, !=, >, <, >=, <=.
        """
        if not conditions:
            # Fallback – behave like plain not_null_check
            return self._check_not_null(patient_id, demographics, vitals, field, rule)

        # Helper to fetch a scalar value (first non-null) from demo/vitals
        def _get_value(col: str):
            if col in demographics.columns and not demographics[col].dropna().empty:
                return demographics[col].dropna().iloc[0]
            if col in vitals.columns and not vitals[col].dropna().empty:
                return vitals[col].dropna().iloc[0]
            return None

        def _eval(operator: str, lhs, rhs):
            try:
                if operator == "==":
                    return lhs == rhs
                if operator == "!=":
                    return lhs != rhs
                if operator == ">":
                    return lhs > rhs
                if operator == "<":
                    return lhs < rhs
                if operator == ">=":
                    return lhs >= rhs
                if operator == "<=":
                    return lhs <= rhs
            except Exception:
                return False
            return False

        # If any condition matches, field becomes required
        required = False
        for cond in conditions:
            c_field = cond.get("field")
            operator = cond.get("operator", "==")
            value = cond.get("value")
            lhs_val = _get_value(c_field)
            if lhs_val is None:
                continue
            if _eval(operator, lhs_val, value):
                required = True
                break

        if not required:
            return []

        # Now defer to not_null logic
        return self._check_not_null(patient_id, demographics, vitals, field, rule)

    def validate_all_patients(self) -> Dict[str, List[ValidationResult]]:
        """
        Validate all patients in the database.

        Returns:
            Dictionary mapping patient IDs to lists of validation results
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all patient IDs - fix column name from patient_id to id
            cursor.execute("SELECT id FROM patients WHERE id IS NOT NULL")
            patient_ids = [row[0] for row in cursor.fetchall()]

            conn.close()

            # Validate each patient
            results = {}
            for patient_id in patient_ids:
                if patient_id is not None:  # Extra check to ensure no None values
                    patient_results = self.validate_patient(patient_id)
                    if patient_results:
                        results[patient_id] = patient_results

            return results

        except Exception as e:
            logger.error(f"Error validating all patients: {e}")
            return {}

    def get_issues_summary(self) -> Dict[str, int]:
        """
        Get a summary of validation issues by status.

        Returns:
            Dictionary with counts of issues by status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT status, COUNT(*) FROM validation_results GROUP BY status"
            )
            results = {row[0]: row[1] for row in cursor.fetchall()}

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Error getting issues summary: {e}")
            return {}

    def get_patient_issues(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Get all validation issues for a specific patient.

        Args:
            patient_id: ID of the patient

        Returns:
            List of dictionaries with issue details
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT MIN(vr.result_id) AS result_id,
                       vr.rule_id,
                       vr.field_name,
                       MAX(vr.issue_description) AS issue_description,
                       MAX(vr.detected_at)  AS detected_at,
                       MAX(vr.status)        AS status,
                       vru.description,
                       vru.severity,
                       COUNT(*)              AS occurrences
                FROM validation_results vr
                JOIN validation_rules vru ON vr.rule_id = vru.rule_id
                WHERE vr.patient_id = ?
                GROUP BY vr.rule_id, vr.field_name, vru.description, vru.severity
                ORDER BY detected_at DESC
            """,
                (patient_id,),
            )

            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "result_id": row[0],
                        "rule_id": row[1],
                        "field_name": row[2],
                        "issue_description": row[3],
                        "detected_at": row[4],
                        "status": row[5],
                        "rule_description": row[6],
                        "severity": row[7],
                        "occurrences": row[8],
                    }
                )

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Error getting patient issues: {e}")
            return []
