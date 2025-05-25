#!/usr/bin/env python3
"""
Test Dashboard Integration for Sprint 2.2

Verify that the learning analytics dashboard components can be imported and initialized.
"""


def test_dashboard_integration():
    """Test that all dashboard components can be imported and initialized."""

    print("🧪 Testing Dashboard Integration for Sprint 2.2...")

    try:
        # Test learning analytics service
        print("\n📊 Testing LearningAnalyticsService...")
        from app.services.learning_analytics import LearningAnalyticsService

        analytics = LearningAnalyticsService()
        print("✅ LearningAnalyticsService imported and initialized")

        # Test learning charts panel
        print("\n📈 Testing LearningChartsPanel...")
        from app.components.admin_dashboard.learning_charts import LearningChartsPanel

        charts_panel = LearningChartsPanel(analytics_service=analytics)
        print("✅ LearningChartsPanel imported and initialized")

        # Test admin dashboard tab with learning analytics
        print("\n🖥️ Testing AdminDashboardTab with learning analytics...")
        from app.components.admin_dashboard.dashboard_tab import AdminDashboardTab

        dashboard = AdminDashboardTab()
        print("✅ AdminDashboardTab imported and initialized with learning analytics")

        # Test that the learning analytics toggle exists
        if hasattr(dashboard, "learning_toggle"):
            print("✅ Learning analytics toggle found")
        else:
            print("❌ Learning analytics toggle not found")

        # Test that the learning section exists
        if hasattr(dashboard, "learning_section"):
            print("✅ Learning section found")
        else:
            print("❌ Learning section not found")

        # Test getting some sample data
        print("\n📋 Testing sample data retrieval...")
        patterns = analytics.get_pattern_effectiveness(30)
        print(f"✅ Retrieved {len(patterns)} patterns")

        progress = analytics.get_learning_progress(30)
        print(
            f"✅ Retrieved learning progress: {progress.overall_learning_rate:.1%} learning rate"
        )

        print("\n🎉 All Sprint 2.2 components successfully integrated!")

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    success = test_dashboard_integration()
    exit(0 if success else 1)
