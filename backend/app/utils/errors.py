"""
Centralized error handling utilities.

This module provides:
- Custom exception hierarchy for domain-specific errors
- Error-to-HTTPException mappers
- Consistent error logging patterns

Usage:
    from app.utils.errors import ExternalServiceError, log_and_raise

    try:
        response = s3.get_object(...)
    except ClientError as e:
        raise ExternalServiceError("S3", str(e), retryable=True) from e
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class BMXError(Exception):
    """Base exception for all BlueMoxon domain errors."""

    def __init__(self, message: str):
        self._message = message
        super().__init__(message)

    @property
    def message(self) -> str:
        """Return the error message."""
        return self._message


class ExternalServiceError(BMXError):
    """Error communicating with external service (S3, SQS, Cognito, etc.)."""

    def __init__(self, service: str, message: str, retryable: bool = False):
        self.service = service
        self._original_message = message
        self.retryable = retryable
        super().__init__(f"{service} error: {message}")

    @property
    def message(self) -> str:
        """Return original message (without service prefix)."""
        return self._original_message


class DatabaseError(BMXError):
    """Database operation failed."""

    def __init__(self, operation: str, message: str):
        self.operation = operation
        super().__init__(f"Database {operation} failed: {message}")


class ValidationError(BMXError):
    """Input validation failed."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validation error on '{field}': {message}")


class ResourceNotFoundError(BMXError):
    """Requested resource does not exist."""

    def __init__(self, resource_type: str, resource_id: Any):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} not found: {resource_id}")


class ConflictError(BMXError):
    """Operation conflicts with current state."""

    pass
