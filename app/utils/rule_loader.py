"""
Rule Loader Utility

This module provides functions for loading validation rules
from a JSON file into the database.
"""

import json
import os
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any
import yaml

# Set up logging
logger = logging.getLogger(__name__)


def load_rules_from_json(json_path: str, db_path: str) -> bool:
    """
    Load validation rules from a JSON file into the database.

    Args:
        json_path: Path to the JSON file containing rules
        db_path: Path to the SQLite database

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if files exist
        if not os.path.exists(json_path):
            logger.error(f"Rules file not found: {json_path}")
            return False

        if not os.path.exists(db_path):
            logger.error(f"Database file not found: {db_path}")
            return False

        # Load rules from JSON file
        with open(json_path, "r") as f:
            rules = json.load(f)

        if not rules:
            logger.warning("No rules found in JSON file")
            return False

        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Insert or update each rule
        for rule in rules:
            # Check if required fields are present
            required_fields = [
                "rule_id",
                "description",
                "rule_type",
                "validation_logic",
                "parameters",
                "severity",
            ]
            if not all(field in rule for field in required_fields):
                logger.warning(
                    f"Rule missing required fields: {rule.get('rule_id', 'unknown')}"
                )
                continue

            # Check if rule already exists
            cursor.execute(
                "SELECT 1 FROM validation_rules WHERE rule_id = ?", (rule["rule_id"],)
            )
            exists = cursor.fetchone() is not None

            # Convert parameters to JSON string if it's a dict
            if isinstance(rule["parameters"], dict):
                rule["parameters"] = json.dumps(rule["parameters"])

            if exists:
                # Update existing rule
                cursor.execute(
                    """UPDATE validation_rules 
                       SET description = ?, 
                           rule_type = ?, 
                           validation_logic = ?, 
                           parameters = ?, 
                           severity = ?, 
                           is_active = 1,
                           updated_at = CURRENT_TIMESTAMP 
                       WHERE rule_id = ?""",
                    (
                        rule["description"],
                        rule["rule_type"],
                        rule["validation_logic"],
                        rule["parameters"],
                        rule["severity"],
                        rule["rule_id"],
                    ),
                )
                logger.info(f"Updated rule: {rule['rule_id']}")
            else:
                # Insert new rule with all columns for new schema
                cursor.execute(
                    """INSERT INTO validation_rules 
                       (rule_id, description, rule_type, validation_logic, parameters, severity, created_at, updated_at, is_active) 
                       VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)""",
                    (
                        rule["rule_id"],
                        rule["description"],
                        rule["rule_type"],
                        rule["validation_logic"],
                        rule["parameters"],
                        rule["severity"],
                    ),
                )
                logger.info(f"Inserted rule: {rule['rule_id']}")

        # Commit changes and close connection
        conn.commit()
        conn.close()

        logger.info(f"Successfully loaded {len(rules)} rules into database")
        return True

    except Exception as e:
        logger.error(f"Error loading rules: {e}")
        return False


def get_default_rules_path() -> str:
    """
    Get the path to the default validation rules JSON file.

    Returns:
        Path to the default rules file
    """
    base_dir = Path(__file__).parent.parent.parent
    return os.path.join(base_dir, "data", "validation_rules.json")


def initialize_validation_rules(db_path: str) -> bool:
    """
    Initialize the validation rules in the database from the default rules file.

    Args:
        db_path: Path to the SQLite database

    Returns:
        True if successful, False otherwise
    """
    # Prefer YAML over JSON for human-editable config
    base_dir = Path(__file__).parent.parent.parent
    yaml_path = os.path.join(base_dir, "data", "validation_rules.yaml")
    if os.path.exists(yaml_path):
        return load_rules_from_yaml(yaml_path, db_path)

    # Fallback to JSON for backward compatibility
    json_path = os.path.join(base_dir, "data", "validation_rules.json")
    return load_rules_from_json(json_path, db_path)


# -----------------------------------------------------------
# Generic file loader (JSON or YAML)
# -----------------------------------------------------------


def _load_rules_from_stream(rules: List[Dict[str, Any]], db_path: str) -> bool:
    """Helper shared by JSON/YAML loaders to persist rule list."""
    try:
        if not rules:
            logger.warning("No rules provided to loader")
            return False

        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for rule in rules:
            required_fields = [
                "rule_id",
                "description",
                "rule_type",
                "validation_logic",
                "parameters",
                "severity",
            ]
            if not all(field in rule for field in required_fields):
                logger.warning(
                    f"Rule missing required fields: {rule.get('rule_id', 'unknown')}"
                )
                continue

            # Convert dict parameters to JSON str for DB storage
            if isinstance(rule["parameters"], dict):
                rule["parameters"] = json.dumps(rule["parameters"])

            # Upsert logic
            cursor.execute(
                "SELECT 1 FROM validation_rules WHERE rule_id = ?", (rule["rule_id"],)
            )
            exists = cursor.fetchone() is not None

            if exists:
                cursor.execute(
                    """UPDATE validation_rules SET description=?, rule_type=?, validation_logic=?, parameters=?, severity=?, is_active=1, updated_at=CURRENT_TIMESTAMP WHERE rule_id=?""",
                    (
                        rule["description"],
                        rule["rule_type"],
                        rule["validation_logic"],
                        rule["parameters"],
                        rule["severity"],
                        rule["rule_id"],
                    ),
                )
                logger.info(f"Updated rule: {rule['rule_id']}")
            else:
                cursor.execute(
                    """INSERT INTO validation_rules (rule_id, description, rule_type, validation_logic, parameters, severity, created_at, updated_at, is_active) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)""",
                    (
                        rule["rule_id"],
                        rule["description"],
                        rule["rule_type"],
                        rule["validation_logic"],
                        rule["parameters"],
                        rule["severity"],
                    ),
                )
                logger.info(f"Inserted rule: {rule['rule_id']}")

        conn.commit()
        conn.close()
        logger.info(f"Successfully loaded {len(rules)} rules into database")
        return True

    except Exception as exc:
        logger.error(f"Error loading rules: {exc}")
        return False


def load_rules_from_yaml(yaml_path: str, db_path: str) -> bool:
    """Load validation rules from a YAML file."""
    try:
        if not os.path.exists(yaml_path):
            logger.error(f"Rules file not found: {yaml_path}")
            return False

        with open(yaml_path, "r") as fp:
            rules = yaml.safe_load(fp)

        return _load_rules_from_stream(rules, db_path)

    except Exception as exc:
        logger.error(f"Error reading YAML rules: {exc}")
        return False


def load_rules_from_file(path: str, db_path: str) -> bool:
    """Load rules from JSON or YAML based on file extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext in {".yaml", ".yml"}:
        return load_rules_from_yaml(path, db_path)
    elif ext == ".json":
        return load_rules_from_json(path, db_path)  # existing function
    else:
        logger.error(f"Unsupported rules file extension: {ext}")
        return False
