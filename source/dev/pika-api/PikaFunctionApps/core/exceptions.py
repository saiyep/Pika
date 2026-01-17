"""Custom exceptions for Pika life automation service."""


class PikaException(Exception):
    """Base exception for Pika service."""
    pass


class InvalidTaskTypeException(PikaException):
    """Raised when an invalid task type is provided."""
    pass


class StorageAuthenticationException(PikaException):
    """Raised when storage authentication fails."""
    pass


class VisionProcessingException(PikaException):
    """Raised when vision processing fails."""
    pass


class NotionUpdateException(PikaException):
    """Raised when Notion database update fails."""
    pass