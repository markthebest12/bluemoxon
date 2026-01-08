# Error Handling Guide

## Overview

This guide documents the standardized error handling patterns used in the BlueMoxon backend API.

## Exception Hierarchy

All custom exceptions inherit from `BMXError`:

```
BMXError (base)
├── ExternalServiceError  - AWS, external APIs (S3, SQS, Cognito, Bedrock, etc.)
├── DatabaseError         - SQLAlchemy/PostgreSQL errors
├── ValidationError       - Input validation failures
├── ResourceNotFoundError - 404 cases
└── ConflictError         - State conflicts (duplicate jobs, etc.)
```

## HTTP Status Code Mapping

| Exception Type | HTTP Status | When to Use |
|----------------|-------------|-------------|
| `ValidationError` | 400 | Invalid input from client |
| `ResourceNotFoundError` | 404 | Resource doesn't exist |
| `ConflictError` | 409 | Operation conflicts with state |
| `ExternalServiceError` | 502 | External service failure (non-retryable) |
| `ExternalServiceError` (retryable=True) | 503 | External service failure (retryable) |
| `DatabaseError` | 500 | Database operation failed |

## Usage Pattern

### Basic Pattern

```python
from app.utils.errors import ExternalServiceError, log_and_raise

try:
    result = external_service.call()
except ServiceException as e:
    log_and_raise(
        ExternalServiceError("ServiceName", str(e), retryable=True),
        context={"resource_id": id}
    )
```

### Conflict Errors (409)

```python
from app.utils.errors import ConflictError, log_and_raise
from sqlalchemy.exc import IntegrityError

try:
    db.add(record)
    db.commit()
except IntegrityError:
    db.rollback()
    log_and_raise(
        ConflictError("Resource already exists"),
        context={"resource_id": id}
    )
```

### Validation Errors (400)

```python
from app.utils.errors import ValidationError, log_and_raise

if not is_valid(input_data):
    log_and_raise(
        ValidationError("field_name", "Invalid format"),
        context={"value": input_data}
    )
```

## Logging Behavior

The `log_and_raise` function handles logging automatically:

- `ValidationError`, `ResourceNotFoundError`: Logged at WARNING level
- All other errors: Logged at ERROR level with stack trace

Context is included in all log messages for debugging.

## Design Decisions

### S3 Delete Failures

S3 delete failures are caught and logged but don't fail the operation. The database record is the source of truth, and orphaned S3 objects can be cleaned up by lifecycle rules.

### External Service Retryability

- `retryable=True` → 503 Service Unavailable (client should retry)
- `retryable=False` → 502 Bad Gateway (permanent failure)

Use `retryable=True` for transient failures like rate limits or timeouts.
