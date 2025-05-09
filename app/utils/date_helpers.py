"""
Date Handling Utilities

This module provides standardized date parsing and formatting functions
to ensure consistent date handling throughout the application.
"""

import pandas as pd
from datetime import datetime, timezone
import logging

# Set up logging
logger = logging.getLogger(__name__)


def parse_date_string(date_str, default_format=None):
    """
    Parse a date string into a datetime object with robust error handling.

    Args:
        date_str: String representation of a date
        default_format: Optional format string to try first

    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str

    # Check for NaT
    if pd.isna(date_str) or (hasattr(date_str, "is_nan") and date_str.is_nan()):
        return None

    try:
        # Try explicit format first if provided
        if default_format:
            try:
                return datetime.strptime(date_str, default_format)
            except ValueError:
                pass

        # Try ISO format with various options
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

        # Use pandas parser without timezone to keep tz-naive
        return pd.to_datetime(date_str, utc=False).to_pydatetime()
    except Exception as e:
        logger.error(f"Failed to parse date string '{date_str}': {e}")
        return None


def normalize_datetime(dt):
    """
    Normalize a datetime object to ensure consistent timezone handling.
    Converts to timezone-naive datetime to prevent timezone comparison issues.

    Args:
        dt: Datetime object or string to normalize

    Returns:
        Timezone-naive datetime object
    """
    if dt is None:
        return None

    # Check for NaT values
    if pd.isna(dt):
        return None

    try:
        # Convert string to datetime if needed
        if isinstance(dt, str):
            dt = parse_date_string(dt)
            if dt is None:
                return None

        # If it has timezone info, convert to UTC and then remove timezone
        if dt.tzinfo is not None:
            # Convert to UTC then remove timezone info
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

        return dt
    except Exception as e:
        logger.error(f"Failed to normalize datetime {dt}: {e}")
        return None


def safe_date_diff_days(date1, date2):
    """
    Calculate the difference in days between two dates with robust error handling.

    Args:
        date1: First date (string or datetime)
        date2: Second date (string or datetime)

    Returns:
        Integer number of days difference or None if calculation fails
    """
    try:
        # First normalize both dates to handle timezone issues
        norm_date1 = normalize_datetime(date1)
        norm_date2 = normalize_datetime(date2)

        # Calculate difference if both dates are valid
        if norm_date1 and norm_date2:
            return abs((norm_date1 - norm_date2).days)
        return None
    except Exception as e:
        logger.error(f"Failed to calculate date difference: {e}")
        return None


def format_date_for_display(date_obj, format_str="%Y-%m-%d"):
    """
    Format a date object as a string for display.

    Args:
        date_obj: Date to format (string or datetime)
        format_str: Format string for output

    Returns:
        Formatted date string or empty string if formatting fails
    """
    try:
        # Handle NaT values
        if pd.isna(date_obj):
            return ""

        # Parse date if it's a string
        if isinstance(date_obj, str):
            date_obj = parse_date_string(date_obj)

        # Format date if valid
        if date_obj:
            return date_obj.strftime(format_str)
        return ""
    except Exception as e:
        logger.error(f"Failed to format date for display: {e}")
        return ""


def convert_df_dates(df, date_columns, utc=False):
    """
    Convert date columns in a DataFrame to datetime objects.

    Args:
        df: Pandas DataFrame
        date_columns: List of column names containing dates
        utc: Whether to convert to UTC timezone

    Returns:
        DataFrame with date columns converted to datetime
    """
    if df.empty:
        return df

    df_copy = df.copy()

    for col in date_columns:
        if col in df_copy.columns:
            try:
                # Using errors='coerce' to convert invalid dates to NaT
                df_copy[col] = pd.to_datetime(df_copy[col], utc=utc, errors="coerce")
            except Exception as e:
                logger.error(f"Failed to convert column {col} to datetime: {e}")

    return df_copy


def get_now():
    """
    Get current datetime in a consistent format.

    Returns:
        Timezone-naive datetime object
    """
    return datetime.now().replace(microsecond=0)


def normalize_date_series(series, format_str="%Y-%m-%d"):
    """Return a pandas Series of consistently formatted date strings.

    This helper takes a Series (or list-like) containing heterogeneous date
    representations (ISO strings, timestamps, timezone-aware strings, datetime
    objects, etc.) and converts each value to a plain string in the requested
    ``format_str`` (default: ``YYYY-MM-DD``).  Values that cannot be parsed are
    returned as ``None`` so the caller can easily drop/inspect them.

    Parameters
    ----------
    series : pandas.Series | list
        Sequence of date representations to normalise.
    format_str : str, default "%Y-%m-%d"
        ``strftime`` pattern to use for the output.

    Returns
    -------
    pandas.Series
        Normalised string values or ``None`` where parsing failed.
    """

    if not isinstance(series, pd.Series):
        series = pd.Series(series)

    def _norm(val):
        # Early-out for NaN / None
        if pd.isna(val):
            return None
        try:
            dt = parse_date_string(val)
            if dt is None:
                return None
            return dt.strftime(format_str)
        except Exception as exc:  # pragma: no cover – defensive
            logger.error("normalize_date_series: failed to normalise %s (%s)", val, exc)
            return None

    return series.apply(_norm)


# Backwards-compatibility alias – keeps API flexible if we later accept DataFrames.
normalize_date_strings = normalize_date_series
