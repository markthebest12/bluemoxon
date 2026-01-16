# Design: Cleanup Lambda S3 Structure Integration Test

**Issue:** #687
**Date:** 2026-01-15
**Status:** Approved

## Problem

Current tests use mocked S3 responses and don't catch structural drift between actual S3 bucket structure and test assumptions. The key format mismatch bug (`books/515/...` vs `515/...`) would not have been caught by unit tests.

## Solution

Add integration test that validates S3 objects under `books/` prefix match expected patterns.

## Test Structure

**File:** `backend/tests/integration/test_cleanup_s3_structure.py`

**Behavior:**

- Connects to staging S3 using `AWS_PROFILE=bmx-staging`
- Lists objects under `books/` prefix (read-only)
- Validates each key matches one of the expected patterns
- Fails if unexpected patterns found

**Valid Patterns:**

| Format | Pattern | Example |
|--------|---------|---------|
| Nested (scraper) | `books/{book_id}/...` | `books/515/image_00.webp` |
| Nested thumbnail | `books/thumb_{book_id}/...` | `books/thumb_515/image_00.webp` |
| Flat (uploads) | `books/{book_id}_{uuid}.{ext}` | `books/10_abc-123.jpg` |

**Skip conditions:**

- Requires `RUN_INTEGRATION_TESTS=1` environment variable
- Samples up to 1000 objects to prevent timeout

## CI Workflow

**File:** `.github/workflows/integration-tests.yml`

**Schedule:** Weekly on Sundays at 06:00 UTC

**Trigger options:**

- Scheduled (weekly)
- Manual via `workflow_dispatch`

**Steps:**

1. Checkout code
2. Setup Python with poetry
3. Configure AWS credentials (staging OIDC role)
4. Run integration tests
5. Create GitHub issue on failure (alerting)

## Files to Create/Modify

| File | Action |
|------|--------|
| `backend/tests/integration/test_cleanup_s3_structure.py` | Create |
| `.github/workflows/integration-tests.yml` | Create |
| `docs/plans/2026-01-15-cleanup-s3-integration-test-design.md` | This document |

## Acceptance Criteria

- [x] Design approved
- [ ] Integration test exists in `backend/tests/integration/`
- [ ] Test queries real S3 bucket structure
- [ ] Test validates prefix matches expected patterns
- [ ] Scheduled CI job runs test weekly
- [ ] Test failures create GitHub issue for alerting
