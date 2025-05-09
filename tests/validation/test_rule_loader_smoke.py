import sqlite3

import pytest
import yaml

from app.utils.rule_loader import load_rules_from_yaml


@pytest.fixture()
def tmp_db(tmp_path):
    """Create an empty SQLite DB with just the *validation_rules* table."""
    db_path = tmp_path / "rules.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE validation_rules (
            rule_id TEXT PRIMARY KEY,
            description TEXT,
            rule_type TEXT,
            validation_logic TEXT,
            parameters TEXT,
            severity TEXT,
            is_active INTEGER DEFAULT 1,
            updated_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()
    return str(db_path)


def test_rule_loader_upserts_duplicate_id(tmp_path, tmp_db):
    """Second occurrence of same rule_id should *update* row, not insert a duplicate."""
    yaml_path = tmp_path / "dup_rules.yaml"

    rules = [
        {
            "rule_id": "DUP_TEST",
            "description": "initial",
            "rule_type": "range_check",
            "validation_logic": "range_check",
            "parameters": {},
            "severity": "warning",
        },
        {
            "rule_id": "DUP_TEST",
            "description": "updated",
            "rule_type": "range_check",
            "validation_logic": "range_check",
            "parameters": {},
            "severity": "error",
        },
    ]
    yaml_path.write_text(yaml.safe_dump(rules))

    # Load rules twice to ensure idempotency as well
    assert load_rules_from_yaml(str(yaml_path), tmp_db)
    assert load_rules_from_yaml(str(yaml_path), tmp_db)

    conn = sqlite3.connect(tmp_db)
    cur = conn.execute(
        "SELECT description, severity FROM validation_rules WHERE rule_id = 'DUP_TEST'"
    )
    row = cur.fetchone()
    conn.close()

    assert row == ("updated", "error"), "Rule row should reflect last update"

    # Ensure only one row exists
    conn = sqlite3.connect(tmp_db)
    total = conn.execute(
        "SELECT COUNT(*) FROM validation_rules WHERE rule_id = 'DUP_TEST'"
    ).fetchone()[0]
    conn.close()
    assert total == 1
