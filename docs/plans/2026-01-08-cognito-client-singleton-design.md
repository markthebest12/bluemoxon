# Design: Cognito Client Singleton (#860)

## Problem

`backend/app/api/v1/users.py` creates a new Cognito client in 7 different functions, violating DRY and missing connection reuse.

## Solution

Create a cached Cognito client using `@lru_cache`.

## Implementation

### 1. New Service Module

**File: `backend/app/services/cognito.py`**

```python
"""Cognito client service with caching."""

from functools import lru_cache

from mypy_boto3_cognito_idp import CognitoIdentityProviderClient
import boto3

from app.config import get_settings


@lru_cache
def get_cognito_client() -> CognitoIdentityProviderClient:
    """Get cached Cognito Identity Provider client.

    Raises:
        ValueError: If AWS region is not configured.
    """
    settings = get_settings()
    if not settings.aws_region:
        raise ValueError("AWS region not configured (settings.aws_region is empty)")
    return boto3.client("cognito-idp", region_name=settings.aws_region)
```

### 2. Changes to `users.py`

Replace 7 occurrences of:
```python
cognito = boto3.client("cognito-idp", region_name=settings.aws_region)
```

With:
```python
from app.services.cognito import get_cognito_client

# In each function:
cognito = get_cognito_client()
```

**Affected functions:**
- `invite_user` (line 114)
- `delete_user` (line 306)
- `get_user_mfa_status` (line 347)
- `disable_user_mfa` (line 424)
- `enable_user_mfa` (line 466)
- `reset_user_password` (line 521)
- `impersonate_user` (line 577)

Also remove `import boto3` from users.py (keep `ClientError` from botocore).

### 3. Dependencies

Add to `pyproject.toml` dev dependencies:
```toml
mypy-boto3-cognito-idp = "^1.35"
```

### 4. Testing

Mock pattern:
```python
@patch("app.services.cognito.get_cognito_client")
def test_invite_user(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    # ...
```

Clear cache for error condition tests:
```python
get_cognito_client.cache_clear()
```

## Files Changed

- `backend/app/services/cognito.py` (new)
- `backend/app/api/v1/users.py` (modified)
- `pyproject.toml` (modified)
- `backend/tests/test_users.py` (modified, if exists)
