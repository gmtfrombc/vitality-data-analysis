"""Seed Validation Rules from metric_catalogue.csv to YAML and DB

Usage:
    python -m etl.seed_validation_rules [--csv path] [--yaml path] [--db path]

If paths are omitted it will default to:
    csv  -> data/metric_catalogue.csv
    yaml -> data/validation_rules.yaml (overwrites)
    db   -> patient_data.db

The script converts each CSV row into a rule dict compatible with
ValidationEngine and persists them:
1. Writes `validation_rules.yaml` for human editing / version control.
2. Loads the YAML through `app.utils.rule_loader.load_rules_from_yaml` to
   populate / update the `validation_rules` table.

CSV columns expected (see metric_catalogue.csv):
    field,type,min,max,freq_days,allowed,unit,editable,description
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Local import after adjusting sys.path for module resolution when run as script
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from app.utils.rule_loader import load_rules_from_yaml  # noqa: E402

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _row_to_rule(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Map a CSV row to a validation rule dict."""
    field = row["field"].strip()
    rule_type_raw = row["type"].strip().lower()
    rule_id_base = field.upper()

    description = row.get("description", "").strip()

    # Build common shell for rule
    rule: Dict[str, Any] = {
        "rule_id": f"{rule_id_base}_{rule_type_raw.upper()}_CHECK",
        "description": description or f"Auto-generated rule for {field}",
        # placeholder, will adjust below
        "rule_type": "",  # populated later
        "validation_logic": "",  # populated later
        "parameters": {},
        "severity": "warning",  # default, may overwrite
    }

    # ---------------------------------------------------------------------
    # Map rule-specific details
    # ---------------------------------------------------------------------
    if rule_type_raw == "frequency":
        rule["rule_type"] = "missing_data"
        rule["validation_logic"] = "date_diff_check"
        freq_days = row.get("freq_days", "").strip()
        # If value like "not_null" treat as 0 – meaning at least one value must exist
        if freq_days and freq_days.isdigit():
            rule["parameters"] = {"field": field, "max_days_between": int(freq_days)}
        else:
            rule["parameters"] = {"field": field, "max_days_between": 0}
        rule["severity"] = "warning"

    elif rule_type_raw == "range":
        rule["rule_type"] = "range_check"
        rule["validation_logic"] = "range_check"
        min_val = row.get("min", "").strip()
        max_val = row.get("max", "").strip()
        parameters: Dict[str, Any] = {"field": field}
        if min_val:
            try:
                parameters["min_value"] = float(min_val)
            except ValueError:
                pass
        if max_val:
            try:
                parameters["max_value"] = float(max_val)
            except ValueError:
                pass
        rule["parameters"] = parameters
        rule["severity"] = "error"

    elif rule_type_raw == "categorical":
        # Not yet implemented by ValidationEngine but store for future use
        rule["rule_type"] = "categorical_check"
        rule["validation_logic"] = "allowed_values_check"
        allowed = row.get("allowed", "").strip()
        allowed_values = None
        if allowed and allowed.lower() != "not_null":
            allowed_values = allowed.split("|")
        rule["parameters"] = {
            "field": field,
            "allowed_values": allowed_values,
            "not_null": allowed.lower() == "not_null",
        }
        rule["severity"] = "warning"
    else:
        # Unknown type – skip
        return None

    return rule


# ---------------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------------


def main(csv_path: str, yaml_path: str, db_path: str) -> None:
    rules: List[Dict[str, Any]] = []

    with open(csv_path, newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            rule = _row_to_rule(row)
            if rule:
                rules.append(rule)

    if not rules:
        print("No rules generated from CSV – aborting.")
        sys.exit(1)

    # Write YAML
    with open(yaml_path, "w", encoding="utf-8") as fp:
        yaml.safe_dump(rules, fp, sort_keys=False, allow_unicode=True)
    print(f"Wrote {len(rules)} rules to {yaml_path}")

    # Load into DB
    ok = load_rules_from_yaml(yaml_path, db_path)
    if ok:
        print("Rules successfully loaded into DB.")
    else:
        print("Failed to load rules into DB – check logs for details.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed validation rules from CSV.")
    parser.add_argument("--csv", default=str(ROOT / "data" / "metric_catalogue.csv"))
    parser.add_argument("--yaml", default=str(ROOT / "data" / "validation_rules.yaml"))
    parser.add_argument("--db", default=str(ROOT / "patient_data.db"))
    args = parser.parse_args()

    main(args.csv, args.yaml, args.db)
