"""
Query State Management and Persistence for AI Assistant

This module handles loading, saving, and managing saved queries for the AI Assistant.
Persistence is currently file-based, but the interface is designed for future extensibility.
"""

import os
import json
from typing import List, Dict, Any

# Default file path for saved queries
QUERIES_FILE = "saved_queries.json"


def load_saved_queries(file_path: str = QUERIES_FILE) -> List[Dict[str, Any]]:
    """
    Load saved queries from a JSON file.

    Args:
        file_path: Path to the saved queries JSON file.

    Returns:
        List of saved query dicts.
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            # Log or handle error as needed
            return []
    return []


def save_queries_to_file(
    queries: List[Dict[str, Any]], file_path: str = QUERIES_FILE
) -> None:
    """
    Save the list of queries to a JSON file.

    Args:
        queries: List of query dicts to save.
        file_path: Path to the saved queries JSON file.
    """
    try:
        with open(file_path, "w") as f:
            json.dump(queries, f, indent=2)
    except Exception as e:
        # Log or handle error as needed
        pass


def add_or_update_query(
    queries: List[Dict[str, Any]], new_query: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Add a new query or update an existing one by name.

    Args:
        queries: Current list of saved queries.
        new_query: Query dict to add or update.

    Returns:
        Updated list of queries.
    """
    existing_names = [q["name"] for q in queries]
    if new_query["name"] in existing_names:
        for i, query in enumerate(queries):
            if query["name"] == new_query["name"]:
                queries[i] = new_query
                break
    else:
        queries.append(new_query)
    return queries


def delete_query(queries: List[Dict[str, Any]], name: str) -> List[Dict[str, Any]]:
    """
    Delete a query by name.

    Args:
        queries: Current list of saved queries.
        name: Name of the query to delete.

    Returns:
        Updated list of queries.
    """
    return [q for q in queries if q["name"] != name]
