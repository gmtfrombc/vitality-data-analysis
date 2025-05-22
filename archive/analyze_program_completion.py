#!/usr/bin/env python3
"""
Program Completion Analysis

This script analyzes differences between program completers and dropouts
in the Metabolic Health Program, examining key health metrics and demographics.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import logging
from pathlib import Path

from app.utils import db_query
from app.utils.patient_attributes import is_program_completer, is_program_dropout

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_data():
    """Load and prepare patient data for analysis."""
    logger.info("Loading patient data...")

    # Retrieve patient & visit data
    patients_df = db_query.get_all_patients()

    # Get provider_visits for all patients
    visit_df = db_query.query_dataframe(
        "SELECT patient_id, provider_visits FROM patient_visit_metrics"
    )

    # Get vitals data
    vitals_df = db_query.get_all_vitals()

    # Get lab results
    labs_df = db_query.query_dataframe(
        """
        SELECT patient_id, date, score_type, score_value 
        FROM lab_results
        """
    )

    # Merge patient and visit data
    merged = (
        patients_df[
            [
                "id",
                "active",
                "gender",
                "ethnicity",
                "program_start_date",
                "program_end_date",
            ]
        ]
        .merge(
            visit_df,
            left_on="id",
            right_on="patient_id",
            how="left",
        )
        .rename(columns={"id": "patient_id"})
    )

    # Identify program completers and dropouts
    merged["is_completer"] = merged.apply(
        lambda row: is_program_completer(row["active"], row.get("provider_visits")),
        axis=1,
    )

    merged["is_dropout"] = merged.apply(
        lambda row: is_program_dropout(row["active"], row.get("provider_visits")),
        axis=1,
    )

    merged["status"] = merged.apply(
        lambda row: (
            "Completer"
            if row["is_completer"]
            else ("Dropout" if row["is_dropout"] else "Active")
        ),
        axis=1,
    )

    return merged, vitals_df, labs_df


def analyze_completion_rates(patient_df):
    """Calculate completion and dropout rates."""
    total_patients = len(patient_df)
    completers = patient_df["is_completer"].sum()
    dropouts = patient_df["is_dropout"].sum()
    active = total_patients - completers - dropouts

    completion_rate = round(completers / total_patients * 100, 1)
    dropout_rate = round(dropouts / total_patients * 100, 1)

    logger.info(f"Total patients: {total_patients}")
    logger.info(f"Completers: {completers} ({completion_rate}%)")
    logger.info(f"Dropouts: {dropouts} ({dropout_rate}%)")
    logger.info(f"Active: {active} ({round(active / total_patients * 100, 1)}%)")

    # Create pie chart
    labels = ["Completers", "Dropouts", "Active"]
    sizes = [completers, dropouts, active]
    colors = ["#4CAF50", "#F44336", "#2196F3"]

    plt.figure(figsize=(8, 6))
    plt.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90)
    plt.axis("equal")
    plt.title("Patient Program Status Distribution")

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / "program_status_distribution.png")
    plt.close()

    return {
        "total_patients": total_patients,
        "completers": completers,
        "completion_rate": completion_rate,
        "dropouts": dropouts,
        "dropout_rate": dropout_rate,
        "active": active,
    }


def compare_visit_counts(patient_df):
    """Compare provider visit counts between completers and dropouts."""
    # Filter for completers and dropouts
    completers = patient_df[patient_df["is_completer"]]
    dropouts = patient_df[patient_df["is_dropout"]]

    # Calculate average provider visits
    avg_visits_completers = completers["provider_visits"].mean()
    avg_visits_dropouts = dropouts["provider_visits"].mean()

    logger.info(f"Average provider visits for completers: {avg_visits_completers:.1f}")
    logger.info(f"Average provider visits for dropouts: {avg_visits_dropouts:.1f}")

    # Create bar chart
    plt.figure(figsize=(10, 6))

    # Plot visit distribution
    plt.subplot(1, 2, 1)
    sns.histplot(
        data=patient_df,
        x="provider_visits",
        hue="status",
        bins=range(0, max(patient_df["provider_visits"]) + 1),
        multiple="stack",
        discrete=True,
    )
    plt.title("Provider Visit Distribution by Status")
    plt.xlabel("Number of Provider Visits")
    plt.ylabel("Count of Patients")

    # Plot average visits
    plt.subplot(1, 2, 2)
    status_groups = ["Completer", "Dropout"]
    visit_avgs = [avg_visits_completers, avg_visits_dropouts]

    bar_plot = plt.bar(status_groups, visit_avgs, color=["#4CAF50", "#F44336"])

    # Add value labels on bars
    for bar in bar_plot:
        height = bar.get_height()
        plt.annotate(
            f"{height:.1f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),  # 3 points vertical offset
            textcoords="offset points",
            ha="center",
            va="bottom",
        )

    plt.title("Average Provider Visits")
    plt.ylabel("Number of Visits")

    plt.tight_layout()
    plt.savefig("output/visit_analysis.png")
    plt.close()

    return {
        "avg_visits_completers": avg_visits_completers,
        "avg_visits_dropouts": avg_visits_dropouts,
    }


def analyze_health_metrics(patient_df, vitals_df):
    """Compare key health metrics between completers and dropouts."""
    # Get patient IDs for each group
    completer_ids = patient_df.loc[patient_df["is_completer"], "patient_id"].tolist()
    dropout_ids = patient_df.loc[patient_df["is_dropout"], "patient_id"].tolist()

    # Filter vitals data for each group
    completer_vitals = vitals_df[vitals_df["patient_id"].isin(completer_ids)]
    dropout_vitals = vitals_df[vitals_df["patient_id"].isin(dropout_ids)]

    # Calculate average metrics
    metrics = {
        "BMI": "bmi",
        "Weight": "weight",
        "Systolic BP": "sbp",
        "Diastolic BP": "dbp",
    }

    results = {}

    plt.figure(figsize=(12, 10))
    plot_count = 1

    for metric_name, column in metrics.items():
        # Skip if column doesn't exist
        if column not in vitals_df.columns:
            logger.warning(f"Column {column} not found in vitals data")
            continue

        # Calculate averages
        completer_avg = completer_vitals[column].mean()
        dropout_avg = dropout_vitals[column].mean()

        results[f"{metric_name}_completer_avg"] = completer_avg
        results[f"{metric_name}_dropout_avg"] = dropout_avg

        logger.info(f"Average {metric_name} for completers: {completer_avg:.1f}")
        logger.info(f"Average {metric_name} for dropouts: {dropout_avg:.1f}")

        # Create subplot
        plt.subplot(2, 2, plot_count)

        # Create boxplot
        plot_data = pd.DataFrame(
            {
                "Status": ["Completer"] * len(completer_vitals)
                + ["Dropout"] * len(dropout_vitals),
                metric_name: list(completer_vitals[column])
                + list(dropout_vitals[column]),
            }
        )

        sns.boxplot(x="Status", y=metric_name, data=plot_data)
        plt.title(f"{metric_name} Comparison")

        plot_count += 1

    plt.tight_layout()
    plt.savefig("output/health_metrics_comparison.png")
    plt.close()

    return results


def analyze_demographics(patient_df):
    """Analyze demographic distribution between completers and dropouts."""
    # Get data for each group
    completers = patient_df[patient_df["is_completer"]]
    dropouts = patient_df[patient_df["is_dropout"]]

    # Analyze gender distribution
    plt.figure(figsize=(12, 6))

    # Gender distribution
    plt.subplot(1, 2, 1)
    gender_completers = completers["gender"].value_counts(normalize=True) * 100
    gender_dropouts = dropouts["gender"].value_counts(normalize=True) * 100

    gender_df = (
        pd.DataFrame({"Completers": gender_completers, "Dropouts": gender_dropouts})
        .fillna(0)
        .round(1)
    )

    gender_df.plot(kind="bar", ax=plt.gca())
    plt.title("Gender Distribution (%)")
    plt.ylabel("Percentage")
    plt.xticks(rotation=0)

    # Ethnicity distribution
    plt.subplot(1, 2, 2)
    ethnicity_completers = completers["ethnicity"].value_counts(normalize=True) * 100
    ethnicity_dropouts = dropouts["ethnicity"].value_counts(normalize=True) * 100

    ethnicity_df = (
        pd.DataFrame(
            {"Completers": ethnicity_completers, "Dropouts": ethnicity_dropouts}
        )
        .fillna(0)
        .round(1)
    )

    ethnicity_df.plot(kind="bar", ax=plt.gca())
    plt.title("Ethnicity Distribution (%)")
    plt.ylabel("Percentage")
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig("output/demographic_comparison.png")
    plt.close()

    return {
        "gender_completers": gender_completers.to_dict(),
        "gender_dropouts": gender_dropouts.to_dict(),
        "ethnicity_completers": ethnicity_completers.to_dict(),
        "ethnicity_dropouts": ethnicity_dropouts.to_dict(),
    }


def main():
    """Main function to run the analysis."""
    parser = argparse.ArgumentParser(description="Analyze program completion data")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output",
        help="Output directory for generated files",
    )
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    logger.info("Starting program completion analysis...")

    # Load data
    patient_df, vitals_df, labs_df = load_data()

    # Run analyses
    completion_stats = analyze_completion_rates(patient_df)
    visit_stats = compare_visit_counts(patient_df)
    health_metrics = analyze_health_metrics(patient_df, vitals_df)
    demographic_stats = analyze_demographics(patient_df)

    # Write summary to file
    with open(output_dir / "completion_analysis_summary.txt", "w") as f:
        f.write("METABOLIC HEALTH PROGRAM - COMPLETION ANALYSIS SUMMARY\n")
        f.write("=====================================================\n\n")

        f.write("PROGRAM STATUS\n")
        f.write(f"Total patients: {completion_stats['total_patients']}\n")
        f.write(
            f"Program completers: {completion_stats['completers']} ({completion_stats['completion_rate']}%)\n"
        )
        f.write(
            f"Program dropouts: {completion_stats['dropouts']} ({completion_stats['dropout_rate']}%)\n"
        )
        f.write(f"Active patients: {completion_stats['active']}\n\n")

        f.write("PROVIDER VISITS\n")
        f.write(
            f"Average provider visits for completers: {visit_stats['avg_visits_completers']:.1f}\n"
        )
        f.write(
            f"Average provider visits for dropouts: {visit_stats['avg_visits_dropouts']:.1f}\n\n"
        )

        f.write("HEALTH METRICS COMPARISON (Completers vs Dropouts)\n")
        for key, value in health_metrics.items():
            if "_completer_avg" in key:
                metric = key.replace("_completer_avg", "")
                dropout_key = key.replace("_completer_avg", "_dropout_avg")
                if dropout_key in health_metrics:
                    f.write(
                        f"{metric}: {value:.1f} vs {health_metrics[dropout_key]:.1f}\n"
                    )

        f.write("\nAnalysis complete. Check the output directory for visualizations.\n")

    logger.info(f"Analysis complete. Results saved to {output_dir}")


if __name__ == "__main__":
    main()
