"""Path utilities for Pika life automation service."""

import os
from datetime import datetime
from .date_utils import format_date_for_storage, format_date_for_filename


def build_blob_path(task_type: str, date_obj: datetime, original_filename: str = None) -> str:
    """Build a blob path based on task type, date, and optional original filename."""
    date_path = format_date_for_storage(date_obj)
    
    if original_filename:
        # Preserve the original filename but put it in the right date folder
        # Prepend with 'data/' as per the storage structure
        return f"data/{task_type}/{date_path}/{original_filename}"
    else:
        # Generate a filename based on the current timestamp
        timestamp = format_date_for_filename(date_obj)
        extension = ".png"  # Default to png for screenshots
        return f"data/{task_type}/{date_path}/{timestamp}{extension}"


def get_processed_path(original_path: str, task_type: str) -> str:
    """Get the processed path for a given blob path."""
    # If the original path starts with 'data/', replace it with '{task_type}/processed/data/'
    if original_path.startswith('data/'):
        path_without_data = original_path[5:]  # Remove 'data/' prefix
        return f"{task_type}/processed/{path_without_data}"
    else:
        # Fallback: if not starting with 'data/', just prepend processed path
        path_parts = original_path.split('/')
        return f"{task_type}/processed/{'/'.join(path_parts[1:])}"