"""Tests for error handling utilities."""


def test_custom_exceptions_exist():
    """Custom exception classes should be defined."""
    from app.utils.errors import (
        BMXError,
        ConflictError,
        DatabaseError,
        ExternalServiceError,
        ResourceNotFoundError,
        ValidationError,
    )

    # All should inherit from BMXError
    assert issubclass(ExternalServiceError, BMXError)
    assert issubclass(DatabaseError, BMXError)
    assert issubclass(ValidationError, BMXError)
    assert issubclass(ResourceNotFoundError, BMXError)
    assert issubclass(ConflictError, BMXError)


def test_external_service_error_attributes():
    """ExternalServiceError should have service name and retry hint."""
    from app.utils.errors import ExternalServiceError

    err = ExternalServiceError("S3", "Failed to upload", retryable=True)
    assert err.service == "S3"
    assert err.message == "Failed to upload"
    assert err.retryable is True
    assert str(err) == "S3 error: Failed to upload"


def test_resource_not_found_error():
    """ResourceNotFoundError should have resource type and id."""
    from app.utils.errors import ResourceNotFoundError

    err = ResourceNotFoundError("Book", 123)
    assert err.resource_type == "Book"
    assert err.resource_id == 123
    assert str(err) == "Book not found: 123"


def test_conflict_error():
    """ConflictError should describe the conflict."""
    from app.utils.errors import ConflictError

    err = ConflictError("Analysis job already in progress")
    assert str(err) == "Analysis job already in progress"


def test_database_error():
    """DatabaseError should describe the operation that failed."""
    from app.utils.errors import DatabaseError

    err = DatabaseError("commit", "Connection lost")
    assert err.operation == "commit"
    assert str(err) == "Database commit failed: Connection lost"


def test_validation_error():
    """ValidationError should describe the field and issue."""
    from app.utils.errors import ValidationError

    err = ValidationError("email", "Invalid format")
    assert err.field == "email"
    assert str(err) == "Validation error on 'email': Invalid format"


def test_to_http_exception_mapping():
    """BMXError should map to appropriate HTTP status codes."""
    from app.utils.errors import (
        ConflictError,
        DatabaseError,
        ExternalServiceError,
        ResourceNotFoundError,
        ValidationError,
        to_http_exception,
    )

    # External service → 502 Bad Gateway
    err = ExternalServiceError("S3", "Connection refused")
    http_err = to_http_exception(err)
    assert http_err.status_code == 502
    assert "S3" in http_err.detail

    # External service retryable → 503 Service Unavailable
    err = ExternalServiceError("SQS", "Timeout", retryable=True)
    http_err = to_http_exception(err)
    assert http_err.status_code == 503

    # Resource not found → 404
    err = ResourceNotFoundError("Book", 123)
    http_err = to_http_exception(err)
    assert http_err.status_code == 404

    # Validation → 400
    err = ValidationError("email", "Invalid format")
    http_err = to_http_exception(err)
    assert http_err.status_code == 400

    # Conflict → 409
    err = ConflictError("Already exists")
    http_err = to_http_exception(err)
    assert http_err.status_code == 409

    # Database → 500
    err = DatabaseError("commit", "Connection lost")
    http_err = to_http_exception(err)
    assert http_err.status_code == 500


def test_log_and_raise():
    """log_and_raise should log and raise HTTPException."""
    import pytest

    from app.utils.errors import ExternalServiceError, log_and_raise
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        log_and_raise(
            ExternalServiceError("Bedrock", "Model not available"),
            context={"book_id": 123, "model": "claude-3"},
        )

    assert exc_info.value.status_code == 502
    assert "Bedrock" in exc_info.value.detail
