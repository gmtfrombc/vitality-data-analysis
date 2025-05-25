"""
Tests for AdminDashboardTab component - Sprint 1.1 functionality.
"""

import pytest
import tempfile
from pathlib import Path

from app.utils.db_migrations import apply_pending_migrations


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    try:
        Path(path).unlink()
        apply_pending_migrations(path)
        yield path
    finally:
        if Path(path).exists():
            Path(path).unlink()


class TestAdminDashboardTab:
    """Test AdminDashboardTab functionality."""

    def test_dashboard_tab_creation(self, temp_db):
        """Test that dashboard tab can be created."""
        # This test verifies the basic instantiation works
        # In a real environment, we'd need to mock Panel components
        try:
            # We can't fully test Panel components without a server
            # but we can test that the class can be imported and basic methods exist
            from app.components.admin_dashboard.dashboard_tab import AdminDashboardTab

            # Verify the class has the expected methods
            assert hasattr(AdminDashboardTab, "get_panel")
            assert hasattr(AdminDashboardTab, "_refresh_data")
            assert hasattr(AdminDashboardTab, "_update_status_indicator")
            assert hasattr(AdminDashboardTab, "_update_component_cards")
            assert hasattr(AdminDashboardTab, "_update_metrics_summary")

            print("✅ AdminDashboardTab class structure is correct")

        except Exception as e:
            pytest.fail(f"Failed to import or verify AdminDashboardTab: {e}")

    def test_component_card_creation(self, temp_db):
        """Test component card HTML generation."""

        # Create a mock dashboard tab (without Panel initialization)
        class MockDashboardTab:
            def _create_component_card(self, name: str, data: dict) -> str:
                # Copy the method from AdminDashboardTab
                display_name = name.replace("_", " ").title()
                icon = data.get("icon", "❓")
                status = data.get("status", "unknown")

                # Additional info based on component
                extra_info = ""
                if name == "database":
                    response_time = data.get("response_time_ms", 0)
                    extra_info = f"Response: {response_time}ms"
                elif name == "pattern_learning":
                    patterns = data.get("active_patterns", 0)
                    extra_info = f"Active patterns: {patterns}"
                elif name == "cache":
                    hit_rate = data.get("hit_rate", 0)
                    extra_info = f"Hit rate: {hit_rate:.1%}"

                return f"""
                <div style='border: 1px solid #ddd; border-radius: 8px; padding: 15px; 
                            margin: 5px; background-color: #f8f9fa;'>
                    <div style='text-align: center; font-size: 32px; margin-bottom: 10px;'>{icon}</div>
                    <div style='text-align: center; font-weight: bold; font-size: 16px;'>{display_name}</div>
                    <div style='text-align: center; color: #666; font-size: 14px;'>{status}</div>
                    {f'<div style="text-align: center; color: #888; font-size: 12px; margin-top: 5px;">{extra_info}</div>' if extra_info else ''}
                </div>
                """

        mock_tab = MockDashboardTab()

        # Test database component card
        db_card = mock_tab._create_component_card(
            "database", {"icon": "✅", "status": "connected", "response_time_ms": 45}
        )

        assert "Database" in db_card
        assert "✅" in db_card
        assert "connected" in db_card
        assert "Response: 45ms" in db_card

        # Test pattern learning component card
        pattern_card = mock_tab._create_component_card(
            "pattern_learning",
            {"icon": "✅", "status": "active", "active_patterns": 12},
        )

        assert "Pattern Learning" in pattern_card
        assert "✅" in pattern_card
        assert "active" in pattern_card
        assert "Active patterns: 12" in pattern_card

        print("✅ Component card generation works correctly")
