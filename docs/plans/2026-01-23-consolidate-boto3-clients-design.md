# Design: Consolidate boto3 Client Factories

**Issue:** #1262
**Date:** 2026-01-23
**Status:** Approved

## Problem

The codebase has 10 duplicate boto3 client factory functions across 7 files:

| Service | Implementations | With Region | With @lru_cache |
|---------|-----------------|-------------|-----------------|
| S3 | 4 | 2/4 | 3/4 |
| SQS | 3 | 2/3 | 3/3 |
| Lambda | 3 | 1/3 | 3/3 |

Problems:
- Inconsistent region configuration
- Code duplication makes configuration changes error-prone
- Multiple cached instances per service type

## Solution

Create `backend/app/services/aws_clients.py` with three cached factory functions:

```python
from functools import lru_cache
import os
import boto3
from app.config import get_settings

@lru_cache(maxsize=1)
def get_s3_client():
    settings = get_settings()
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("s3", region_name=region)

@lru_cache(maxsize=1)
def get_sqs_client():
    settings = get_settings()
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("sqs", region_name=region)

@lru_cache(maxsize=1)
def get_lambda_client():
    settings = get_settings()
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("lambda", region_name=region)
```

## Files to Modify

### New Files
- `backend/app/services/aws_clients.py` - central factory module
- `backend/tests/unit/services/test_aws_clients.py` - unit tests

### Consumer Updates

| File | Remove | Add Import |
|------|--------|------------|
| `services/scraper.py` | `get_s3_client()`, `get_lambda_client()` | Both from aws_clients |
| `services/bedrock.py` | `get_s3_client()` | From aws_clients |
| `api/v1/images.py` | `get_s3_client()` | From aws_clients |
| `services/sqs.py` | `get_sqs_client()` | From aws_clients |
| `services/image_processing.py` | `get_sqs_client()` | From aws_clients |
| `workers/tracking_dispatcher.py` | `get_sqs_client()` | From aws_clients |
| `services/fmv_lookup.py` | `_get_lambda_client()` | `get_lambda_client` from aws_clients |

### Unchanged (Keep Specialized Configs)
- `api/v1/health.py` - health check timeouts (5s)
- `services/bedrock.py` - `get_bedrock_client()` with 540s timeout
- `lambdas/image_processor/handler.py` - cold start optimization pattern
- `services/cognito.py` - already standalone

## Out of Scope

- Bedrock client consolidation (specialized timeout config)
- Cognito client (already fine)
- Health check clients (specialized timeout config)
- Image processor Lambda (different runtime context)

## Validation

```bash
poetry run ruff check backend/
poetry run ruff format --check backend/
poetry run pytest backend/tests/unit/
```
