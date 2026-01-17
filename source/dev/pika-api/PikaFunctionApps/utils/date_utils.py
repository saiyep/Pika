"""Date utilities for Pika life automation service."""

from datetime import datetime
import re


def parse_date_string(date_str: str) -> datetime:
    """Parse a date string in various formats to a datetime object."""
    # Try standard ISO format first
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        pass
    
    # Try YYYY-MM-DD format
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        pass
    
    # Try YYYY/MM/DD format
    try:
        return datetime.strptime(date_str, '%Y/%m/%d')
    except ValueError:
        pass
    
    # Try YYYY.MM.DD format
    try:
        return datetime.strptime(date_str, '%Y.%m.%d')
    except ValueError:
        pass
    
    raise ValueError(f"Unable to parse date string: {date_str}")


def format_date_for_filename(dt: datetime) -> str:
    """Format a datetime object for use in filenames (YYYYMMDD_HHMM)."""
    return dt.strftime('%Y%m%d_%H%M')


def format_date_for_storage(dt: datetime) -> str:
    """Format a datetime object for Azure Storage path (year/month subfolders)."""
    return dt.strftime('%Y/%m')