# Session: Issue #1262 - Consolidate Duplicate boto3 Client Factories

**Date:** 2026-01-23
**Issue:** https://github.com/markthebest12/bluemoxon/issues/1262
**PR:** https://github.com/markthebest12/bluemoxon/pull/1271
**Status:** PR Ready for Final Review (post code review fixes applied)

---

## CRITICAL SESSION RULES

### 1. ALWAYS Use Superpowers Skills

**Invoke relevant skills BEFORE any response or action.** Even a 1% chance a skill might apply means invoke it.

Key skills for this work:
- `superpowers:brainstorming` - Before any design work
- `superpowers:test-driven-development` - Before writing any implementation code
- `superpowers:receiving-code-review` - When receiving feedback (verify before implementing)
- `superpowers:verification-before-completion` - Before claiming work is done

### 2. Bash Command Formatting - NEVER USE

These trigger permission prompts - NEVER use them:
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

### 3. Bash Command Formatting - ALWAYS USE

- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

---

## Background

PR #1260 added `@lru_cache` to multiple boto3 client factory functions. However, duplicate implementations existed across 7+ files with inconsistent region configuration.

### Original Problem (10 duplicate implementations)

**S3 Clients (4):** bedrock.py, scraper.py, images.py, image_processor/handler.py
**SQS Clients (3):** sqs.py, image_processing.py, tracking_dispatcher.py
**Lambda Clients (3):** scraper.py, fmv_lookup.py, health.py

---

## Solution Implemented

### New Central Module: `backend/app/services/aws_clients.py`

```python
@lru_cache(maxsize=1)
def get_s3_client():
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("s3", region_name=region)

@lru_cache(maxsize=1)
def get_sqs_client():
    # Same pattern...

@lru_cache(maxsize=1)
def get_lambda_client():
    # Same pattern...
```

### Consumer Modules Updated (Pattern A - Direct Import)

All 7 modules now use direct import at module level:
```python
from app.services.aws_clients import get_s3_client
```

Files updated:
- `app/services/scraper.py` - S3 + Lambda
- `app/services/bedrock.py` - S3
- `app/api/v1/images.py` - S3
- `app/services/sqs.py` - SQS
- `app/services/image_processing.py` - SQS
- `app/workers/tracking_dispatcher.py` - SQS
- `app/services/fmv_lookup.py` - Lambda

### Kept Separate (Specialized Configs)

- `health.py` - 5-second timeout for health checks
- `bedrock.py` get_bedrock_client - 540-second timeout for Claude
- `lambdas/image_processor/handler.py` - Different deployment package

---

## Code Review Feedback Applied

| Issue | Resolution |
|-------|------------|
| P1 - Inconsistent patterns (wrapper vs direct import) | All modules now use Pattern A (direct import) |
| P2 - Late imports without justification | All imports at module level |
| P3 - Dead boto3 import in sqs.py | NOT dead - used for STS client in `_get_queue_url()` |
| P4/P5 - Scattered/redundant tests | Consolidated into single `test_aws_clients.py` with simpler identity tests |

---

## Current State

- **Branch:** `refactor/consolidate-boto3-clients`
- **Commits:** 2 (initial + review fixes)
- **Tests:** 1904 passing (consolidated from 1910)
- **Linting:** Clean

---

## Next Steps

1. **User reviews PR #1271** - Awaiting approval
2. **Merge to staging** - Use `gh pr merge 1271 --squash`
3. **Validate staging** - Check staging environment works
4. **Watch deploy** - `gh run list --workflow Deploy --limit 1` then `gh run watch <id> --exit-status`
5. **Create staging→main PR** - `gh pr create --base main --head staging --title "chore: Promote staging"`
6. **User reviews promotion PR**
7. **Merge to main** - Use `gh pr merge <n> --merge` (NOT squash for promotions)
8. **Watch prod deploy**

---

## Files Changed Summary

### New Files
- `backend/app/services/aws_clients.py`
- `backend/tests/services/test_aws_clients.py`
- `docs/plans/2026-01-23-consolidate-boto3-clients-design.md`

### Modified Files
- `backend/app/services/scraper.py`
- `backend/app/services/bedrock.py`
- `backend/app/api/v1/images.py`
- `backend/app/services/sqs.py`
- `backend/app/services/image_processing.py`
- `backend/app/workers/tracking_dispatcher.py`
- `backend/app/services/fmv_lookup.py`
- `backend/tests/test_books.py` (mock updates)

### Deleted Files
- `backend/tests/test_boto3_caching.py` (consolidated)

---

## Validation Commands

```bash
# Backend linting
poetry run ruff check backend/
poetry run ruff format --check backend/

# Run tests
poetry run pytest backend/tests/ --ignore=backend/tests/integration/ -q

# Check PR status
gh pr view 1271
gh pr checks 1271
```
