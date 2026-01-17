# Session: Auto-Process Images Infrastructure

**Date:** 2026-01-16/17
**Issue:** #1136
**PRs:** #1139, #1141, #1142 (merged), #1143 (CI passing, ready to merge), #1145 (infra to prod)

## Summary

Deployed infrastructure for automatic image processing during book eval import. Images are queued to SQS and processed by a Lambda worker that removes backgrounds.

**Feature flow:** eBay import → copy images → queue primary image to SQS → Lambda processes → background removed

---

## Current Status

| Phase | Status | Details |
|-------|--------|---------|
| **Phase 1: Infrastructure** | ✅ Staging done, PR #1145 for prod | SQS queue, DLQ, IAM, health checks, Lambda resource |
| **Phase 2: Lambda Deployment** | ❌ Not started | Needs container-based Lambda (rembg native deps) |
| **Phase 3: API Integration** | ✅ PR #1143 ready | `queue_image_processing()` added to import flow |

**Deployment Strategy:** Push infrastructure to prod first (PR #1145), then API integration separately.

### PR #1143 Code Review Fixes (All Addressed)

| Fix | Description |
|-----|-------------|
| Stack trace logging | Added `exc_info=True` to logger.warning |
| Recovery mechanism | Jobs saved with `queue_failed` status for retry |
| First-image fallback | Queues first successfully copied image (not just idx=0) |
| Integration test | Verifies actual `ImageProcessingJob` DB record |
| DB optimization | `db.flush()` only for first successful image |
| Terraform docs | Warning for chicken-egg scenario in variable description |

### Verification (Fresh Run)

- 87 tests pass (77 test_books.py + 10 test_image_processing_service.py)
- `ruff check` and `ruff format` clean
- CI: Backend Quality, Backend Validation, Terraform Validate all passing

---

## Next Steps

1. [ ] **Merge PR #1143** (API integration to staging) - CI passing
2. [ ] **Merge PR #1145** (infrastructure to prod) - awaiting approval
3. [ ] **Promote PR #1143 to prod** after staging validation
4. [ ] **Phase 2: Container Lambda deployment**
   - Create Dockerfile for image processor
   - Refactor Terraform from zip to container-based
   - Add ECR repository and CI/CD workflow
   - Reference: `modules/scraper-lambda/` pattern
5. [ ] Test end-to-end: import → queue → process → new image

---

## Related Issues

- #1136 - Main feature issue (auto-process images)
- #1140 - Checklist for adding new async workers
- #1144 - Retry mechanism for `queue_failed` jobs
- #1145 - Infrastructure promotion to prod

---

## CRITICAL: Continuation Instructions

### Superpowers Skills - MANDATORY (NO EXCEPTIONS)

**You MUST invoke Superpowers skills at ALL stages. This is non-negotiable.**

| Task Type | Required Skill | When to Use |
|-----------|---------------|-------------|
| Any bug/issue | `superpowers:systematic-debugging` | Before proposing ANY fix |
| Writing code | `superpowers:test-driven-development` | Before writing implementation |
| Before claiming done | `superpowers:verification-before-completion` | Before ANY completion claim |
| Multiple independent tasks | `superpowers:dispatching-parallel-agents` | When 2+ tasks can parallelize |
| Planning implementation | `superpowers:writing-plans` | Before multi-step implementation |
| Receiving feedback | `superpowers:receiving-code-review` | When reviewing PR feedback |
| Creating PRs | `superpowers:requesting-code-review` | Before creating any PR |

**If you think there's even 1% chance a skill applies, INVOKE IT.**

### Bash Command Formatting - CRITICAL

**NEVER use these (trigger permission prompts):**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

**Example - WRONG:**
```bash
cd /path && npm test  # Run tests
```

**Example - CORRECT:**
```bash
cd /path
```
Then separate Bash tool call:
```bash
npm test
```

---

## Key Files Modified

| File | Change |
|------|--------|
| `backend/app/api/v1/books.py` | Added `queue_image_processing()` to import flow |
| `backend/app/services/image_processing.py` | Added `queue_failed` status recovery |
| `backend/tests/test_books.py` | Integration test for job creation |
| `backend/tests/services/test_image_processing_service.py` | Tests for queue_failed handling |
| `infra/terraform/main.tf` | Chicken-egg warning comment |
| `infra/terraform/variables.tf` | Extended `use_existing_database_credentials` description |

---

## Lessons Learned

1. Never use `-var="db_password=..."` with terraform - use `use_existing_database_credentials`
2. Health check permissions are separate from send permissions (need `GetQueueUrl`, `GetQueueAttributes`)
3. Admin endpoints need explicit health check calls
4. Use `superpowers:dispatching-parallel-agents` for independent fixes (3 agents fixed 3 domains in parallel)
5. Always run `ruff format` before pushing - CI checks formatting
6. Prod uses `enable_database = false` (Aurora managed externally) - no `use_existing_database_credentials` needed
