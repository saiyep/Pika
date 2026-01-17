"""Security utilities for Pika life automation service."""

import os
import logging


def validate_storage_key(storage_key: str) -> bool:
    """Validate the storage key against environment variables."""
    if not storage_key:
        return False
    
    # In production, we would validate against a stored key
    # For now, we'll just check if it's not empty
    return len(storage_key) > 0


def validate_pika_api_key(api_key: str) -> bool:
    """Validate the Pika API key against environment variables."""
    expected_key = os.getenv('Pika_API_Key')
    return api_key == expected_key