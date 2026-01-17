# Session: Auto-Process Images Infrastructure

**Date:** 2026-01-16/17
**Issue:** #1136
**PRs:** #1139, #1141, #1142 (merged), #1143 (pending)

## Summary

Deployed infrastructure for automatic image processing during book eval import. Images are queued to SQS and processed by a Lambda worker that removes backgrounds.

---

## Historical Issues (Resolved)

| Issue | Resolution |
|-------|------------|
| Terraform `-target` changed RDS password | Added `use_existing_database_credentials` variable |
| SQS health check permissions | Added `GetQueueUrl`, `GetQueueAttributes` to IAM |
| Admin page missing SQS status | Added `check_sqs()` call to system-info endpoint |
| Import not queueing images | Added `queue_image_processing()` to books.py |

---

## Current Status

| Phase | Status | Details |
|-------|--------|---------|
| **Phase 1: Infrastructure** | ✅ Complete | SQS queue, IAM, health checks, Lambda resource |
| **Phase 2: Lambda Deployment** | ❌ Not started | Needs container-based Lambda (rembg native deps) |
| **Phase 3: API Integration** | ✅ Complete | PR #1143 with code review fixes |

### PR #1143 Code Review Fixes

| Fix | Description |
|-----|-------------|
| Stack trace logging | Added `exc_info=True` |
| Recovery mechanism | Jobs saved with `queue_failed` status (Issue #1144 for retry) |
| First-image fallback | Queues first successfully copied image |
| Integration test | Verifies actual DB record creation |
| DB optimization | Flush only for first successful image |
| Terraform docs | Warning for chicken-egg scenario |

### Verification

- 87 tests pass (77 test_books.py + 10 test_image_processing_service.py)
- `ruff check` clean

---

## Next Steps

1. [x] Merge PR #1143
2. [ ] **Phase 2: Container Lambda deployment**
   - Create Dockerfile for image processor
   - Refactor Terraform from zip to container-based
   - Add ECR repository and CI/CD workflow
   - Reference: `modules/scraper-lambda/` pattern
3. [ ] Test end-to-end: import → queue → process → new image

---

## Related Issues

- #1136 - Main feature issue
- #1140 - Checklist for adding new async workers
- #1144 - Retry mechanism for queue_failed jobs

---

## Continuation Instructions

### Superpowers Skills - MANDATORY

| Task Type | Required Skill |
|-----------|---------------|
| Any bug/issue | `superpowers:systematic-debugging` |
| Writing code | `superpowers:test-driven-development` |
| Before claiming done | `superpowers:verification-before-completion` |
| Multiple independent tasks | `superpowers:dispatching-parallel-agents` |
| Receiving feedback | `superpowers:receiving-code-review` |

### Bash Command Formatting

**NEVER use:** `#` comments, `\` continuations, `$(...)`, `&&`/`||` chaining, `!` in strings

**ALWAYS use:** Simple single-line commands, separate Bash tool calls, `bmx-api` for API calls

---

## Lessons Learned

1. Never use `-var="db_password=..."` with terraform - use `use_existing_database_credentials`
2. Health check permissions are separate from send permissions
3. Admin endpoints need explicit health check calls
4. Use `superpowers:dispatching-parallel-agents` for independent fixes
