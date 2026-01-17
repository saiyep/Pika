"""Validation utilities for Pika life automation service."""

import re
from typing import Any, Dict


def validate_storage_path(path: str) -> bool:
    """Validate that a storage path is well-formed."""
    if not path or len(path) > 1024:  # Azure Blob Storage has path limits
        return False
    
    # Check for invalid characters
    invalid_chars = ['<', '>', '*', '?' , '%', '&', ':', '@', '+', '/', '\\']
    if any(char in path for char in invalid_chars):
        return False
    
    # Path should not start or end with dot or slash
    if path.startswith('.') or path.startswith('/') or path.endswith('/'):
        return False
    
    return True


def validate_date_format(date_str: str) -> bool:
    """Validate that a date string is in YYYY-MM-DD format."""
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, date_str))


def validate_task_type(task_type: str) -> bool:
    """Validate that a task type is supported."""
    valid_types = ['health', 'running', 'swimming']
    return task_type in valid_types


def validate_storage_key(key: str) -> bool:
    """Basic validation of storage key format."""
    # Storage keys are base64 encoded and typically 88 characters with '=' padding
    if len(key) < 60:  # Minimum reasonable length
        return False
    
    # Should be base64-like format (alphanumeric, +, /, =)
    pattern = r'^[A-Za-z0-9+/]*={0,2}$'
    return bool(re.match(pattern, key))


def validate_params_structure(params: Dict[str, Any], required_keys: list) -> Dict[str, str]:
    """Validate that required keys exist in params and return any errors."""
    errors = {}
    
    for key in required_keys:
        if key not in params:
            errors[key] = f"Required parameter '{key}' is missing"
    
    return errors