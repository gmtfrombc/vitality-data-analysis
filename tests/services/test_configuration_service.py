"""
Tests for Configuration Service

Sprint 3.1 Testing:
- Configuration management
- Alert rule creation
- User preferences
- Configuration history
"""

import pytest
from datetime import datetime

from app.services.configuration_service import ConfigurationService, AlertRule


class TestConfigurationService:
    """Test cases for ConfigurationService."""

    @pytest.fixture
    def config_service(self, tmp_path):
        """Create configuration service with test database."""
        db_path = tmp_path / "test_config.db"
        return ConfigurationService(str(db_path))

    def test_get_configuration(self, config_service):
        """Test getting configuration values."""
        # Should have default configurations
        config = config_service.get_configuration("dashboard.refresh_interval")

        assert config is not None
        assert config.key == "dashboard.refresh_interval"
        assert config.value == 30  # Default value
        assert config.config_type == "integer"
        assert config.category == "dashboard"

    def test_set_configuration(self, config_service):
        """Test setting configuration values."""
        # Set a new value
        success = config_service.set_configuration(
            "dashboard.refresh_interval",
            60,
            "test_user",
            "Testing configuration update",
        )

        assert success is True

        # Verify the value was set
        config = config_service.get_configuration("dashboard.refresh_interval")
        assert config.value == 60
        assert config.updated_by == "test_user"

    def test_get_configuration_by_category(self, config_service):
        """Test getting configuration by category."""
        dashboard_configs = config_service.get_configuration_by_category("dashboard")

        assert len(dashboard_configs) > 0
        assert all(config.category == "dashboard" for config in dashboard_configs)

        # Check for expected dashboard configurations
        config_keys = [config.key for config in dashboard_configs]
        assert "dashboard.refresh_interval" in config_keys
        assert "dashboard.theme" in config_keys

    def test_get_all_categories(self, config_service):
        """Test getting all configuration categories."""
        categories = config_service.get_all_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "dashboard" in categories
        assert "performance" in categories
        assert "alerts" in categories

    def test_parse_config_value(self, config_service):
        """Test configuration value parsing."""
        # Boolean values
        assert config_service._parse_config_value("true", "boolean") is True
        assert config_service._parse_config_value("false", "boolean") is False
        assert config_service._parse_config_value("1", "boolean") is True
        assert config_service._parse_config_value("0", "boolean") is False

        # Integer values
        assert config_service._parse_config_value("42", "integer") == 42
        assert config_service._parse_config_value("-10", "integer") == -10

        # Float values
        assert config_service._parse_config_value("3.14", "float") == 3.14
        assert config_service._parse_config_value("-2.5", "float") == -2.5

        # JSON values
        json_value = config_service._parse_config_value('{"key": "value"}', "json")
        assert isinstance(json_value, dict)
        assert json_value["key"] == "value"

        # String values
        assert config_service._parse_config_value("test", "string") == "test"

    def test_create_alert_rule(self, config_service):
        """Test creating alert rules."""
        rule = AlertRule(
            rule_id="test_rule",
            rule_name="Test Alert",
            metric_name="db_response_time_ms",
            condition_type="greater_than",
            threshold_value=1000.0,
            severity="warning",
            enabled=True,
            escalation_rules={},
            notification_channels=["email"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        success = config_service.create_alert_rule(rule)
        assert success is True

        # Verify the rule was created
        rules = config_service.get_alert_rules()
        assert len(rules) > 0

        created_rule = next((r for r in rules if r.rule_id == "test_rule"), None)
        assert created_rule is not None
        assert created_rule.rule_name == "Test Alert"
        assert created_rule.threshold_value == 1000.0

    def test_get_alert_rules(self, config_service):
        """Test getting alert rules."""
        # Create a test rule first
        rule = AlertRule(
            rule_id="test_rule_2",
            rule_name="Another Test Alert",
            metric_name="error_rate",
            condition_type="greater_than",
            threshold_value=0.1,
            severity="error",
            enabled=True,
            escalation_rules={},
            notification_channels=["dashboard"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        config_service.create_alert_rule(rule)

        # Get all rules
        rules = config_service.get_alert_rules()

        assert isinstance(rules, list)
        assert len(rules) > 0

        # Check rule structure
        for rule in rules:
            assert hasattr(rule, "rule_id")
            assert hasattr(rule, "rule_name")
            assert hasattr(rule, "metric_name")
            assert hasattr(rule, "threshold_value")
            assert hasattr(rule, "severity")

    def test_delete_alert_rule(self, config_service):
        """Test deleting alert rules."""
        # Create a rule to delete
        rule = AlertRule(
            rule_id="delete_test_rule",
            rule_name="Rule to Delete",
            metric_name="memory_usage",
            condition_type="greater_than",
            threshold_value=90.0,
            severity="critical",
            enabled=True,
            escalation_rules={},
            notification_channels=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        config_service.create_alert_rule(rule)

        # Verify it exists
        rules_before = config_service.get_alert_rules()
        rule_exists = any(r.rule_id == "delete_test_rule" for r in rules_before)
        assert rule_exists is True

        # Delete the rule
        success = config_service.delete_alert_rule("delete_test_rule")
        assert success is True

        # Verify it's gone
        rules_after = config_service.get_alert_rules()
        rule_exists = any(r.rule_id == "delete_test_rule" for r in rules_after)
        assert rule_exists is False

    def test_user_preferences(self, config_service):
        """Test user preference management."""
        user_id = "test_user"

        # Set preferences
        success1 = config_service.set_user_preference(user_id, "theme", "dark")
        success2 = config_service.set_user_preference(user_id, "notifications", True)
        success3 = config_service.set_user_preference(
            user_id, "dashboard_layout", {"columns": 2}
        )

        assert success1 is True
        assert success2 is True
        assert success3 is True

        # Get preferences
        preferences = config_service.get_user_preferences(user_id)

        assert isinstance(preferences, dict)
        assert preferences["theme"] == "dark"
        assert preferences["notifications"] is True
        assert preferences["dashboard_layout"]["columns"] == 2

    def test_configuration_history(self, config_service):
        """Test configuration change history."""
        # Make some configuration changes
        config_service.set_configuration(
            "test.setting1", "value1", "user1", "Initial setup"
        )
        config_service.set_configuration(
            "test.setting1", "value2", "user2", "Updated value"
        )
        config_service.set_configuration(
            "test.setting2", "another_value", "user1", "New setting"
        )

        # Get history for specific key
        history = config_service.get_configuration_history("test.setting1", 30)

        assert isinstance(history, list)
        assert len(history) >= 2  # Should have at least 2 changes

        # Check history structure
        for change in history:
            assert "config_key" in change
            assert "old_value" in change
            assert "new_value" in change
            assert "changed_by" in change
            assert "changed_at" in change

        # Get all history
        all_history = config_service.get_configuration_history(None, 30)
        assert len(all_history) >= 3  # Should have at least 3 changes
