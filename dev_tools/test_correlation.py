#!/usr/bin/env python
"""
Simple test script to manually test the correlation analysis feature.
This script connects to the actual patient_data.db and runs a correlation analysis
between weight and BMI, displaying the results.
"""

import pandas as pd
import sqlite3
import holoviews as hv
from pathlib import Path
import panel as pn
from app.utils.plots import scatter_plot

# Initialize HoloViews
hv.extension("bokeh")

# Define paths
DB_PATH = Path("patient_data.db")


def test_correlation_with_real_data():
    """Test correlation analysis with real data from patient_data.db."""
    print("Testing correlation analysis with real data...")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    # Query for weight-BMI correlation (same table)
    weight_bmi_sql = """
    SELECT 
        weight AS metric_x, 
        bmi AS metric_y
    FROM vitals
    WHERE weight IS NOT NULL AND bmi IS NOT NULL
    """

    weight_bmi_df = pd.read_sql_query(weight_bmi_sql, conn)
    print(f"Retrieved {len(weight_bmi_df)} records for weight-BMI correlation")

    # Calculate correlation
    weight_bmi_corr = weight_bmi_df["metric_x"].corr(weight_bmi_df["metric_y"])
    print(f"Weight-BMI Correlation: {weight_bmi_corr:.4f}")

    # Assert correlation is positive and significant (BMI should correlate with weight)
    assert (
        weight_bmi_corr > 0.5
    ), f"Expected strong positive correlation, got {weight_bmi_corr}"

    # Generate visualization
    plot1 = scatter_plot(
        weight_bmi_df,
        x="metric_x",
        y="metric_y",
        xlabel="Weight",
        ylabel="BMI",
        title="Correlation: Weight vs BMI",
        correlation=True,
        regression=True,
    )
    assert plot1 is not None, "Failed to generate weight vs BMI plot"

    # Query for weight-engagement score correlation (cross-table)
    weight_engagement_sql = """
    SELECT 
        v.weight AS metric_x, 
        p.engagement_score AS metric_y
    FROM vitals v
    JOIN patients p ON v.patient_id = p.id
    WHERE v.weight IS NOT NULL AND p.engagement_score IS NOT NULL
    """

    weight_engagement_df = pd.read_sql_query(weight_engagement_sql, conn)
    print(
        f"Retrieved {len(weight_engagement_df)} records for weight-engagement score correlation"
    )

    # Calculate correlation
    weight_eng_corr = weight_engagement_df["metric_x"].corr(
        weight_engagement_df["metric_y"]
    )
    print(f"Weight-Engagement Score Correlation: {weight_eng_corr:.4f}")

    # Just verify we got a valid correlation value (no assumption about direction)
    assert (
        -1.0 <= weight_eng_corr <= 1.0
    ), f"Expected correlation in range [-1,1], got {weight_eng_corr}"

    # Generate visualization
    plot2 = scatter_plot(
        weight_engagement_df,
        x="metric_x",
        y="metric_y",
        xlabel="Weight",
        ylabel="Engagement Score",
        title="Correlation: Weight vs Engagement Score",
        correlation=True,
        regression=True,
    )
    assert plot2 is not None, "Failed to generate weight vs engagement plot"

    # Query for SBP-DBP correlation (blood pressure components)
    bp_sql = """
    SELECT 
        sbp AS metric_x, 
        dbp AS metric_y
    FROM vitals
    WHERE sbp IS NOT NULL AND dbp IS NOT NULL
    """

    bp_df = pd.read_sql_query(bp_sql, conn)
    print(f"Retrieved {len(bp_df)} records for SBP-DBP correlation")

    # Calculate correlation
    bp_corr = bp_df["metric_x"].corr(bp_df["metric_y"])
    print(f"SBP-DBP Correlation: {bp_corr:.4f}")

    # SBP and DBP should be positively correlated
    assert (
        bp_corr > 0
    ), f"Expected positive correlation between SBP and DBP, got {bp_corr}"

    # Generate visualization
    plot3 = scatter_plot(
        bp_df,
        x="metric_x",
        y="metric_y",
        xlabel="Systolic BP",
        ylabel="Diastolic BP",
        title="Correlation: SBP vs DBP",
        correlation=True,
        regression=True,
    )
    assert plot3 is not None, "Failed to generate SBP vs DBP plot"

    conn.close()

    # Skip visualization panel creation in test mode - uncomment for manual testing
    # dashboard = pn.Column(
    #     pn.pane.Markdown("# Correlation Analysis Test"),
    #     pn.pane.Markdown("## Weight vs BMI Correlation"),
    #     pn.pane.HoloViews(plot1, sizing_mode="stretch_width"),
    #     pn.pane.Markdown("## Weight vs Engagement Score Correlation"),
    #     pn.pane.HoloViews(plot2, sizing_mode="stretch_width"),
    #     pn.pane.Markdown("## SBP vs DBP Correlation"),
    #     pn.pane.HoloViews(plot3, sizing_mode="stretch_width"),
    # )

    # For manual testing only - not used in automated tests
    if __name__ == "__main__":
        # Create live dashboard when running as script
        dashboard = pn.Column(
            pn.pane.Markdown("# Correlation Analysis Test"),
            pn.pane.Markdown("## Weight vs BMI Correlation"),
            pn.pane.HoloViews(plot1, sizing_mode="stretch_width"),
            pn.pane.Markdown("## Weight vs Engagement Score Correlation"),
            pn.pane.HoloViews(plot2, sizing_mode="stretch_width"),
            pn.pane.Markdown("## SBP vs DBP Correlation"),
            pn.pane.HoloViews(plot3, sizing_mode="stretch_width"),
        )
        dashboard.servable()
