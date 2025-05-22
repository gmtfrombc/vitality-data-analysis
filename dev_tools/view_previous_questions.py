#!/usr/bin/env python3
"""view_previous_questions.py - Display previously asked test questions

This utility helps prevent repetition during testing by showing questions that
have already been asked to the system, allowing you to focus on new scenarios
or variations during your daily tests.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import argparse
from app.config import get_vp_data_db


def get_db_path():
    """Return the path to the patient database."""
    return get_vp_data_db()


def fetch_previous_questions(days=7, limit=50, include_feedback=True):
    """Fetch previously asked questions from the database.

    Parameters:
    -----------
    days : int
        Number of days to look back (default: 7)
    limit : int
        Maximum number of questions to return (default: 50)
    include_feedback : bool
        Whether to include feedback data (default: True)

    Returns:
    --------
    pd.DataFrame: DataFrame containing previous questions with metadata
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row

    # Get recent questions from assistant_logs
    date_cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    query = f"""
    SELECT 
        query, 
        created_at,
        intent_json
    FROM 
        assistant_logs
    WHERE 
        created_at >= '{date_cutoff}'
    ORDER BY 
        created_at DESC
    LIMIT {limit}
    """

    logs_df = pd.read_sql_query(query, conn)

    # If requested, also get feedback data
    if include_feedback and table_exists(conn, "assistant_feedback"):
        feedback_query = f"""
        SELECT 
            question,
            rating,
            comment,
            created_at
        FROM 
            assistant_feedback
        WHERE 
            created_at >= '{date_cutoff}'
        ORDER BY 
            created_at DESC
        LIMIT {limit}
        """
        feedback_df = pd.read_sql_query(feedback_query, conn)
        feedback_df = feedback_df.rename(columns={"question": "query"})

        # Add a source column to identify where each question came from
        logs_df["source"] = "logs"
        feedback_df["source"] = "feedback"

        # Combine the datasets
        combined_df = pd.concat([logs_df, feedback_df], ignore_index=True)
        combined_df = combined_df.sort_values("created_at", ascending=False)

        result_df = combined_df
    else:
        result_df = logs_df

    conn.close()
    return result_df


def table_exists(conn, table_name):
    """Check if a table exists in the database."""
    query = f"""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='{table_name}'
    """
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchone() is not None


def print_questions(df, show_intents=False):
    """Print questions in a formatted way."""
    if df.empty:
        print("No questions found in the specified time period.")
        return

    # Format the dataframe for display
    if "rating" in df.columns:
        # For feedback data
        display_cols = ["query", "created_at", "rating", "source"]
        if "comment" in df.columns:
            feedback_mask = ~df["comment"].isna() & (df["comment"] != "")
            df.loc[feedback_mask, "query"] += " [has feedback]"
    else:
        # For logs only
        display_cols = ["query", "created_at"]

    # Add intent overview if requested
    if show_intents and "intent_json" in df.columns:
        df["intent_type"] = df["intent_json"].str.extract(r'"intent_type":\s*"([^"]+)"')
        display_cols.append("intent_type")

    # Print in a nice format
    print(f"\n{'='*80}\n  PREVIOUS QUESTIONS ({len(df)} total)\n{'='*80}")

    for i, row in df[display_cols].iterrows():
        date_str = pd.to_datetime(row["created_at"]).strftime("%Y-%m-%d %H:%M")

        # Format based on available columns
        if "rating" in display_cols and "source" in display_cols:
            rating_display = (
                "👍"
                if row.get("rating") == 1
                else "👎" if row.get("rating") == 0 else "⚪"
            )
            source_display = f"[{row.get('source', 'log')}]"
            print(f"{i+1:3d}. {date_str} {rating_display} {source_display}")
        else:
            print(f"{i+1:3d}. {date_str}")

        print(f"     {row['query']}")

        if show_intents and "intent_type" in display_cols and row.get("intent_type"):
            print(f"     Intent: {row.get('intent_type', 'unknown')}")

        print("")


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description="View previously asked questions to avoid repetition during testing."
    )
    parser.add_argument(
        "--days", type=int, default=7, help="Number of days to look back (default: 7)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of questions to show (default: 50)",
    )
    parser.add_argument(
        "--intents",
        action="store_true",
        help="Show detected intent types for each question",
    )
    parser.add_argument(
        "--no-feedback",
        action="store_true",
        help="Exclude questions from the feedback table",
    )

    args = parser.parse_args()

    df = fetch_previous_questions(
        days=args.days, limit=args.limit, include_feedback=not args.no_feedback
    )

    print_questions(df, show_intents=args.intents)

    print("\nTIP: To see more options, run: python view_previous_questions.py --help")


if __name__ == "__main__":
    main()
