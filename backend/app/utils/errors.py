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
from collections.abc import Callable
from typing import Any, NoReturn

from fastapi import HTTPException

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


# Error to HTTP status code mapping
ERROR_STATUS_MAP: dict[type, int | Callable[["BMXError"], int]] = {
    ExternalServiceError: lambda e: 503 if e.retryable else 502,
    DatabaseError: 500,
    ValidationError: 400,
    ResourceNotFoundError: 404,
    ConflictError: 409,
}


def to_http_exception(error: BMXError) -> HTTPException:
    """Convert a BMXError to an appropriate HTTPException."""
    error_type = type(error)

    # Get status code from map
    status_getter = ERROR_STATUS_MAP.get(error_type, 500)
    if callable(status_getter):
        status_code = status_getter(error)
    else:
        status_code = status_getter

    return HTTPException(status_code=status_code, detail=str(error))


def log_and_raise(
    error: BMXError,
    context: dict[str, Any] | None = None,
) -> NoReturn:
    """Log error with context and raise as HTTPException.

    Args:
        error: The domain error that occurred
        context: Additional context for logging (book_id, user_id, etc.)

    Raises:
        HTTPException: Always raises, never returns
    """
    context = context or {}
    context_str = " ".join(f"{k}={v}" for k, v in context.items())

    # Log at appropriate level based on error type
    if isinstance(error, (ResourceNotFoundError, ValidationError)):
        logger.warning("%s [%s]", error, context_str)
    else:
        logger.error("%s [%s]", error, context_str, exc_info=True)

    raise to_http_exception(error) from None
