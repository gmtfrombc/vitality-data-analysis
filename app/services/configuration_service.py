"""
Configuration Service for AAA Admin Monitoring

This service manages system configuration, user preferences,
and advanced settings for the admin dashboard.

Sprint 3.1 Features:
- System configuration management
- User preference storage
- Alert rule configuration
- Performance tuning settings
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.utils.saved_questions_db import DB_FILE

logger = logging.getLogger(__name__)


@dataclass
class ConfigurationItem:
    """Individual configuration item."""

    key: str
    value: Any
    config_type: str  # 'string', 'integer', 'float', 'boolean', 'json'
    description: str
    category: str
    requires_restart: bool
    updated_at: datetime
    updated_by: str


@dataclass
class AlertRule:
    """Alert rule configuration."""

    rule_id: str
    rule_name: str
    metric_name: str
    condition_type: str  # 'greater_than', 'less_than', 'equals', 'not_equals'
    threshold_value: float
    severity: str  # 'info', 'warning', 'error', 'critical'
    enabled: bool
    escalation_rules: Dict[str, Any]
    notification_channels: List[str]
    created_at: datetime
    updated_at: datetime


class ConfigurationService:
    """Service for system configuration management."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the configuration service.

        Args:
            db_path: Optional database path (for testing)
        """
        self.db_path = db_path or DB_FILE
        self._ensure_config_tables()
        self._initialize_default_config()

    def _ensure_config_tables(self):
        """Ensure configuration tables exist."""
        try:
            with self._get_connection() as conn:
                # System configuration table
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS system_configuration (
                    config_key TEXT PRIMARY KEY,
                    config_value TEXT NOT NULL,
                    config_type TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    requires_restart BOOLEAN DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT DEFAULT 'system'
                )
                """
                )

                # Alert rules table
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id TEXT PRIMARY KEY,
                    rule_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    condition_type TEXT NOT NULL,
                    threshold_value REAL NOT NULL,
                    severity TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    escalation_rules TEXT,
                    notification_channels TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
                )

                # User preferences table
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT NOT NULL,
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, preference_key)
                )
                """
                )

                # Configuration history for audit trail
                conn.execute(
                    """
                CREATE TABLE IF NOT EXISTS configuration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    change_reason TEXT
                )
                """
                )

        except Exception as e:
            logger.error(f"Error creating configuration tables: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_default_config(self):
        """Initialize default configuration values."""
        default_configs = [
            # Dashboard settings
            (
                "dashboard.refresh_interval",
                "30",
                "integer",
                "Dashboard auto-refresh interval in seconds",
                "dashboard",
                False,
            ),
            (
                "dashboard.max_chart_points",
                "100",
                "integer",
                "Maximum data points to display in charts",
                "dashboard",
                False,
            ),
            (
                "dashboard.theme",
                "light",
                "string",
                "Dashboard theme (light/dark)",
                "dashboard",
                False,
            ),
            # Performance settings
            (
                "performance.cache_ttl",
                "300",
                "integer",
                "Cache time-to-live in seconds",
                "performance",
                False,
            ),
            (
                "performance.query_timeout",
                "30",
                "integer",
                "Database query timeout in seconds",
                "performance",
                True,
            ),
            (
                "performance.max_concurrent_queries",
                "10",
                "integer",
                "Maximum concurrent database queries",
                "performance",
                True,
            ),
            # Alert settings
            (
                "alerts.default_severity",
                "warning",
                "string",
                "Default alert severity level",
                "alerts",
                False,
            ),
            (
                "alerts.notification_cooldown",
                "300",
                "integer",
                "Cooldown period between notifications in seconds",
                "alerts",
                False,
            ),
            (
                "alerts.max_alerts_per_hour",
                "20",
                "integer",
                "Maximum alerts to send per hour",
                "alerts",
                False,
            ),
            # Maintenance settings
            (
                "maintenance.auto_vacuum_enabled",
                "true",
                "boolean",
                "Enable automatic database vacuum",
                "maintenance",
                False,
            ),
            (
                "maintenance.log_retention_days",
                "30",
                "integer",
                "Number of days to retain log files",
                "maintenance",
                False,
            ),
            (
                "maintenance.backup_retention_days",
                "90",
                "integer",
                "Number of days to retain backup files",
                "maintenance",
                False,
            ),
            # Learning system settings
            (
                "learning.pattern_confidence_threshold",
                "0.8",
                "float",
                "Minimum confidence threshold for patterns",
                "learning",
                False,
            ),
            (
                "learning.max_patterns_per_type",
                "1000",
                "integer",
                "Maximum patterns to store per type",
                "learning",
                False,
            ),
            (
                "learning.auto_cleanup_enabled",
                "true",
                "boolean",
                "Enable automatic cleanup of old patterns",
                "learning",
                False,
            ),
            # Export settings
            (
                "export.max_file_size_mb",
                "100",
                "integer",
                "Maximum export file size in MB",
                "export",
                False,
            ),
            (
                "export.temp_file_retention_hours",
                "24",
                "integer",
                "Hours to retain temporary export files",
                "export",
                False,
            ),
            (
                "export.default_format",
                "pdf",
                "string",
                "Default export format",
                "export",
                False,
            ),
        ]

        try:
            with self._get_connection() as conn:
                for (
                    key,
                    value,
                    config_type,
                    description,
                    category,
                    requires_restart,
                ) in default_configs:
                    # Only insert if not exists
                    cursor = conn.execute(
                        "SELECT 1 FROM system_configuration WHERE config_key = ?",
                        (key,),
                    )
                    if not cursor.fetchone():
                        conn.execute(
                            """
                        INSERT INTO system_configuration 
                        (config_key, config_value, config_type, description, category, requires_restart)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (
                                key,
                                value,
                                config_type,
                                description,
                                category,
                                requires_restart,
                            ),
                        )

                conn.commit()

        except Exception as e:
            logger.error(f"Error initializing default configuration: {e}")

    def get_configuration(self, key: str) -> Optional[ConfigurationItem]:
        """Get a configuration item by key."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                SELECT * FROM system_configuration WHERE config_key = ?
                """,
                    (key,),
                )

                row = cursor.fetchone()
                if row:
                    return ConfigurationItem(
                        key=row["config_key"],
                        value=self._parse_config_value(
                            row["config_value"], row["config_type"]
                        ),
                        config_type=row["config_type"],
                        description=row["description"],
                        category=row["category"],
                        requires_restart=bool(row["requires_restart"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        updated_by=row["updated_by"],
                    )

                return None

        except Exception as e:
            logger.error(f"Error getting configuration {key}: {e}")
            return None

    def get_configuration_by_category(self, category: str) -> List[ConfigurationItem]:
        """Get all configuration items in a category."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                SELECT * FROM system_configuration WHERE category = ?
                ORDER BY config_key
                """,
                    (category,),
                )

                items = []
                for row in cursor.fetchall():
                    item = ConfigurationItem(
                        key=row["config_key"],
                        value=self._parse_config_value(
                            row["config_value"], row["config_type"]
                        ),
                        config_type=row["config_type"],
                        description=row["description"],
                        category=row["category"],
                        requires_restart=bool(row["requires_restart"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        updated_by=row["updated_by"],
                    )
                    items.append(item)

                return items

        except Exception as e:
            logger.error(f"Error getting configuration for category {category}: {e}")
            return []

    def set_configuration(
        self, key: str, value: Any, updated_by: str = "system", change_reason: str = ""
    ) -> bool:
        """Set a configuration value."""
        try:
            # Get current value for history
            current_config = self.get_configuration(key)
            old_value = current_config.value if current_config else None

            # Convert value to string for storage
            if isinstance(value, bool):
                str_value = "true" if value else "false"
                config_type = "boolean"
            elif isinstance(value, int):
                str_value = str(value)
                config_type = "integer"
            elif isinstance(value, float):
                str_value = str(value)
                config_type = "float"
            elif isinstance(value, (dict, list)):
                str_value = json.dumps(value)
                config_type = "json"
            else:
                str_value = str(value)
                config_type = "string"

            with self._get_connection() as conn:
                # Update configuration
                conn.execute(
                    """
                UPDATE system_configuration 
                SET config_value = ?, config_type = ?, updated_at = ?, updated_by = ?
                WHERE config_key = ?
                """,
                    (str_value, config_type, datetime.now(), updated_by, key),
                )

                # Add to history
                conn.execute(
                    """
                INSERT INTO configuration_history 
                (config_key, old_value, new_value, changed_by, change_reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        key,
                        str(old_value) if old_value is not None else None,
                        str_value,
                        updated_by,
                        change_reason,
                    ),
                )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error setting configuration {key}: {e}")
            return False

    def _parse_config_value(self, value: str, config_type: str) -> Any:
        """Parse configuration value based on type."""
        try:
            if config_type == "boolean":
                return value.lower() in ("true", "1", "yes", "on")
            elif config_type == "integer":
                return int(value)
            elif config_type == "float":
                return float(value)
            elif config_type == "json":
                return json.loads(value)
            else:
                return value

        except Exception as e:
            logger.error(f"Error parsing config value {value} as {config_type}: {e}")
            return value

    def get_all_categories(self) -> List[str]:
        """Get all configuration categories."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                SELECT DISTINCT category FROM system_configuration 
                ORDER BY category
                """
                )

                return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Error getting configuration categories: {e}")
            return []

    def create_alert_rule(self, rule: AlertRule) -> bool:
        """Create a new alert rule."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                INSERT OR REPLACE INTO alert_rules 
                (rule_id, rule_name, metric_name, condition_type, threshold_value, 
                 severity, enabled, escalation_rules, notification_channels)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        rule.rule_id,
                        rule.rule_name,
                        rule.metric_name,
                        rule.condition_type,
                        rule.threshold_value,
                        rule.severity,
                        rule.enabled,
                        json.dumps(rule.escalation_rules),
                        json.dumps(rule.notification_channels),
                    ),
                )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error creating alert rule: {e}")
            return False

    def get_alert_rules(self) -> List[AlertRule]:
        """Get all alert rules."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                SELECT * FROM alert_rules ORDER BY rule_name
                """
                )

                rules = []
                for row in cursor.fetchall():
                    rule = AlertRule(
                        rule_id=row["rule_id"],
                        rule_name=row["rule_name"],
                        metric_name=row["metric_name"],
                        condition_type=row["condition_type"],
                        threshold_value=row["threshold_value"],
                        severity=row["severity"],
                        enabled=bool(row["enabled"]),
                        escalation_rules=(
                            json.loads(row["escalation_rules"])
                            if row["escalation_rules"]
                            else {}
                        ),
                        notification_channels=(
                            json.loads(row["notification_channels"])
                            if row["notification_channels"]
                            else []
                        ),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                    )
                    rules.append(rule)

                return rules

        except Exception as e:
            logger.error(f"Error getting alert rules: {e}")
            return []

    def delete_alert_rule(self, rule_id: str) -> bool:
        """Delete an alert rule."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM alert_rules WHERE rule_id = ?", (rule_id,))
                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error deleting alert rule {rule_id}: {e}")
            return False

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                SELECT preference_key, preference_value FROM user_preferences 
                WHERE user_id = ?
                """,
                    (user_id,),
                )

                preferences = {}
                for row in cursor.fetchall():
                    try:
                        # Try to parse as JSON first
                        preferences[row["preference_key"]] = json.loads(
                            row["preference_value"]
                        )
                    except json.JSONDecodeError:
                        # Fall back to string value
                        preferences[row["preference_key"]] = row["preference_value"]

                return preferences

        except Exception as e:
            logger.error(f"Error getting user preferences for {user_id}: {e}")
            return {}

    def set_user_preference(self, user_id: str, key: str, value: Any) -> bool:
        """Set a user preference."""
        try:
            # Convert value to JSON string
            if isinstance(value, (dict, list, bool, int, float)):
                str_value = json.dumps(value)
            else:
                str_value = str(value)

            with self._get_connection() as conn:
                conn.execute(
                    """
                INSERT OR REPLACE INTO user_preferences 
                (user_id, preference_key, preference_value)
                VALUES (?, ?, ?)
                """,
                    (user_id, key, str_value),
                )

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error setting user preference {key} for {user_id}: {e}")
            return False

    def get_configuration_history(
        self, key: Optional[str] = None, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get configuration change history."""
        try:
            with self._get_connection() as conn:
                if key:
                    cursor = conn.execute(
                        """
                    SELECT * FROM configuration_history 
                    WHERE config_key = ? AND changed_at >= datetime('now', '-{} days')
                    ORDER BY changed_at DESC
                    """.format(
                            days
                        ),
                        (key,),
                    )
                else:
                    cursor = conn.execute(
                        """
                    SELECT * FROM configuration_history 
                    WHERE changed_at >= datetime('now', '-{} days')
                    ORDER BY changed_at DESC
                    """.format(
                            days
                        )
                    )

                history = []
                for row in cursor.fetchall():
                    history.append(
                        {
                            "config_key": row["config_key"],
                            "old_value": row["old_value"],
                            "new_value": row["new_value"],
                            "changed_by": row["changed_by"],
                            "changed_at": row["changed_at"],
                            "change_reason": row["change_reason"],
                        }
                    )

                return history

        except Exception as e:
            logger.error(f"Error getting configuration history: {e}")
            return []
