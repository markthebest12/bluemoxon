# Session: Auto-Process Images Infrastructure

**Date:** 2026-01-16/17
**Issue:** #1136
**PRs:** #1139, #1141, #1142, #1143, #1145 (all merged)

## Summary

Deployed infrastructure for automatic image processing during book eval import. Images are queued to SQS and processed by a Lambda worker that removes backgrounds.

**Feature flow:** eBay import → copy images → queue primary image to SQS → Lambda processes → background removed

---

## Current Status (Post-Compaction 2)

| Phase | Status | Details |
|-------|--------|---------|
| **Phase 1: Infrastructure** | ✅ DONE | SQS queue, IAM, health checks, Lambda resource (staging + prod) |
| **Phase 2: Lambda Deployment** | ❌ Not done | Lambda has placeholder - needs container image with rembg |
| **Phase 3: API Integration** | ✅ DONE | PR #1143 - `queue_image_processing()` called during import |

### Phase 3 Complete - Details

- `queue_image_processing()` IS called during eBay import
- Queues first successfully copied image (not just idx=0)
- Recovery mechanism for failed queue operations (`queue_failed` status)

### Phase 2 Remaining Work

1. Create Dockerfile for image processor Lambda
2. Refactor Terraform from zip-based to container-based
3. Add ECR repository + CI/CD workflow
4. Deploy and test end-to-end

**Note:** Queue showing 0 messages is expected - Lambda has placeholder code. Messages may go to DLQ if Lambda errors, or SQS send fails (saved as `queue_failed` for retry via issue #1144).

### What Was Completed This Session

| Task | Status | Details |
|------|--------|---------|
| Merge PR #1143 | ✅ Done | API integration merged to staging (admin merge) |
| Merge PR #1145 | ✅ Done | Infrastructure promoted to prod (admin merge) |
| Terraform apply prod | ✅ Done | Created SQS queues in prod (31 resources added) |
| Prod health check | ✅ Fixed | All SQS queues now healthy (analysis, eval_runbook, image_processing) |
| API docs issue | ✅ Created | Issue #1146 for missing API documentation |
| Secrets Manager | ✅ Created | API keys stored in `bluemoxon-staging/api-key` and `bluemoxon-prod/api-key` |

### CI Auth Failure - ROOT CAUSE FOUND

**Issue:** Deploy workflow smoke tests and migrations failing with HTTP 401.

**Root Cause:** `BMX_API_KEY` environment variable is **EMPTY** in both Lambda functions.

**Evidence:**
```
AWS_PROFILE=bmx-staging aws lambda get-function-configuration \
  --function-name bluemoxon-staging-api \
  --query 'Environment.Variables.BMX_API_KEY'
Result: ''  (empty string)
```

**Secrets created but not yet applied to Lambda:**
- `bluemoxon-staging/api-key` - Staging API key in Secrets Manager
- `bluemoxon-prod/api-key` - Prod API key in Secrets Manager

---

## IMMEDIATE Next Steps (Resume Here)

1. **Update Lambda environment variables with new API keys:**
   - Staging: `6eQjoyosw3ZkLwVfyMScpHme9xv2CoaC39Gl1anruko`
   - Prod: `xdpVz67qEejVpDe3A3Lb_OuRe01nEVKcnVtzKCMLqPw`

2. **Update GitHub secrets:**
   - `BMX_STAGING_API_KEY` → new staging key
   - `BMX_API_KEY` → new prod key

3. **Update local files:**
   - `~/.bmx/staging.key`
   - `~/.bmx/prod.key`

4. **Verify CI passes** by re-running deploy workflow

5. **Create GitHub issue** for Lambda S3 key config errors (terraform apply warning)

6. **Cleanup worktree** after verification

---

## Related Issues

- #1136 - Main feature issue (auto-process images)
- #1140 - Checklist for adding new async workers
- #1144 - Retry mechanism for `queue_failed` jobs
- #1146 - API documentation for undocumented endpoints

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
4. Use `superpowers:dispatching-parallel-agents` for independent fixes
5. Always run `ruff format` before pushing - CI checks formatting
6. Prod uses `enable_database = false` (Aurora managed externally)
7. **Always verify Lambda environment variables** - empty values cause silent auth failures
8. Store API keys in Secrets Manager for better security and auditability
9. Use `terraform init -backend-config=backends/prod.hcl -reconfigure` when switching environments
