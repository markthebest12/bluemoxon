# Session: Auto-Process Images Infrastructure

**Date:** 2026-01-16/17
**Issue:** #1136
**PRs:** #1139, #1141, #1142, #1143, #1145, #1148 (all merged or pending)

## Summary

Deployed infrastructure for automatic image processing during book eval import. Images are queued to SQS and processed by a Lambda worker that removes backgrounds.

**Feature flow:** eBay import → copy images → queue primary image to SQS → Lambda processes → background removed

---

## Current Status (Post-Compaction 5)

| Phase | Status | Details |
|-------|--------|---------|
| **Phase 1: Infrastructure** | ✅ DONE | SQS queue, IAM, health checks, Lambda resource (staging + prod) |
| **Phase 2: Lambda Deployment** | 🔶 NEARLY DONE | Bootstrap image deployed, one fix remaining |
| **Phase 3: API Integration** | ✅ DONE | PR #1143 - `queue_image_processing()` called during import |

### Phase 2 Implementation Progress

| Task | Status | Commit |
|------|--------|--------|
| 1. ECR repository (Terraform) | ✅ Done | `1d6a348` |
| 2. Supporting files (Dockerfile, requirements.txt, download_models.py) | ✅ Done | `0a91d34` |
| 3. Smoke test handler | ✅ Done | `164ac27` |
| 4. Push bootstrap image | ✅ Done | `839aba9` (v2 deployed) |
| 5. Lambda module for container | ✅ Done | `25c10fb` |
| 6. Unit tests (30 passing) | ✅ Done | `b39628f` |
| 7. CI/CD workflow | ✅ Done | `078aca5` |
| 8. Test end-to-end in staging | 🔶 IN PROGRESS | Missing constants.py in container |
| 9. Deploy to production | ⏳ Pending | After staging |

---

## IMMEDIATE Next Steps (Resume Here)

### Task 8: Fix Missing constants.py - IN PROGRESS

**Status:** Smoke test passes, but real job processing fails.

**Issue:** Lambda fails with `No module named 'app.constants'` when processing actual SQS messages.

**Root cause:** Dockerfile copies `backend/app/models/` but `analysis_job.py` imports from `app.constants`.

**Fix already staged (not committed):**

```dockerfile
# In backend/lambdas/image_processor/Dockerfile, line 7-9:
COPY backend/app/__init__.py /opt/python/app/
COPY backend/app/constants.py /opt/python/app/   # ADD THIS LINE
COPY backend/app/models/ /opt/python/app/models/
```

**Steps to complete:**
1. Commit the Dockerfile fix
2. Rebuild: `docker build --platform linux/arm64 --provenance=false -f backend/lambdas/image_processor/Dockerfile -t 652617421195.dkr.ecr.us-west-2.amazonaws.com/bluemoxon-staging-image-processor:v3 /Users/mark/projects/bluemoxon/.worktrees/auto-process-images`
3. Push: `docker push 652617421195.dkr.ecr.us-west-2.amazonaws.com/bluemoxon-staging-image-processor:v3`
4. Update Lambda: `AWS_PROFILE=bmx-staging aws lambda update-function-code --function-name bluemoxon-staging-image-processor --image-uri 652617421195.dkr.ecr.us-west-2.amazonaws.com/bluemoxon-staging-image-processor:v3`
5. Test with SQS message: `AWS_PROFILE=bmx-staging aws sqs send-message --queue-url https://sqs.us-west-2.amazonaws.com/652617421195/bluemoxon-staging-image-processing --message-body '{"job_id": "test-456", "book_id": 634, "image_id": 5512}'`
6. Check logs for success

### After E2E Test Passes

1. Update Terraform module default tag to v3
2. Create PR to staging
3. Validate in staging environment
4. Promote to production

---

## Issues Fixed This Session

### 1. ONNX Runtime Crash on Lambda ARM64 (FIXED)

**Problem:** ONNX Runtime crashes at module import on Lambda Graviton2 due to cpuinfo parsing failure.

**Error:**
```
Error in cpuinfo: failed to parse the list of possible processors
onnxruntime::OnnxRuntimeException: Attempt to use DefaultLogger but none has been registered
```

**Root cause:** The rembg import at module load triggers ONNX Runtime initialization, which fails because `/sys/devices/system/cpu/possible` doesn't exist in Lambda containers.

**Solution (commit `839aba9`):**
- Lazy-load rembg imports (defer to first actual use)
- Added `_ensure_rembg_loaded()` function in handler.py
- Smoke tests now pass because rembg isn't imported until actual processing

**Files changed:**
- `backend/lambdas/image_processor/handler.py` - Lazy loading
- `backend/lambdas/image_processor/requirements.txt` - `rembg[cpu]>=2.0.55`
- `infra/terraform/modules/image-processor/variables.tf` - Added `image_tag` variable
- `infra/terraform/modules/image-processor/main.tf` - Use `image_tag` variable

### 2. rembg Version Incompatibility (FIXED)

**Problem:** `rembg[cpu]==2.0.50` not available for ARM64.

**Solution:** Changed to `rembg[cpu]>=2.0.55` (versions 2.0.55-2.0.72 available for ARM64).

### 3. Docker Manifest Format (FIXED)

**Problem:** Docker Desktop creates multi-arch manifests with attestations that Lambda rejects.

**Solution:** Use `--provenance=false` flag when building:
```bash
docker build --platform linux/arm64 --provenance=false -f Dockerfile -t IMAGE:TAG .
```

### 4. ECR IMMUTABLE Tags (FIXED)

**Problem:** ECR has IMMUTABLE tag policy, can't reuse `:latest`.

**Solution:**
- Added `image_tag` variable to Terraform module (default: "v2")
- Use versioned tags (v1, v2, v3, etc.) for each build

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/lambdas/image_processor/handler.py` | Lambda handler with lazy rembg loading |
| `backend/lambdas/image_processor/Dockerfile` | ARM64 container build (NEEDS constants.py) |
| `infra/terraform/modules/image-processor/main.tf` | Container-based Lambda module |
| `infra/terraform/modules/image-processor/variables.tf` | Module variables including image_tag |

---

## CRITICAL: Continuation Instructions

### Superpowers Skills - MANDATORY (NO EXCEPTIONS)

**You MUST invoke Superpowers skills at ALL stages. This is non-negotiable.**

| Task Type | Required Skill | When to Use |
|-----------|---------------|-------------|
| Starting session | `superpowers:using-superpowers` | First thing |
| Any bug/issue | `superpowers:systematic-debugging` | Before proposing ANY fix |
| Writing code | `superpowers:test-driven-development` | Before writing implementation |
| Before claiming done | `superpowers:verification-before-completion` | Before ANY completion claim |
| Multiple independent tasks | `superpowers:dispatching-parallel-agents` | When 2+ tasks can parallelize |
| Planning implementation | `superpowers:writing-plans` | Before multi-step implementation |
| Executing plans | `superpowers:subagent-driven-development` | For Phase 2 implementation |
| Receiving feedback | `superpowers:receiving-code-review` | When reviewing PR feedback |
| Creating PRs | `superpowers:requesting-code-review` | Before creating any PR |
| Finishing work | `superpowers:finishing-a-development-branch` | When implementation complete |

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

### PR Review Requirements

1. PRs to staging need user review before merge
2. PRs to prod (staging→main) need user review before merge
3. Use `superpowers:requesting-code-review` before creating PRs

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
10. For container Lambda: use `ignore_changes = [image_uri]` and let CI update directly
11. Add deployment tracking via Lambda tags when bypassing Terraform for updates
12. **ARM64 package availability differs** - rembg 2.0.50 not available for ARM64; check PyPI for ARM-compatible versions
13. **ONNX Runtime cpuinfo crash** - Lazy-load rembg to defer ONNX init past smoke test
14. **Docker provenance** - Use `--provenance=false` for Lambda-compatible images
15. **ECR IMMUTABLE tags** - Use versioned tags (v1, v2, etc.), not :latest
16. **Model imports cascade** - When copying models/, also copy any files they import (constants.py)

---

## Related Issues & PRs

| Reference | Description |
|-----------|-------------|
| #1136 | Main feature issue (auto-process images) |
| #1140 | Checklist for adding new async workers |
| #1144 | Retry mechanism for `queue_failed` jobs |
| #1146 | API documentation for undocumented endpoints |
| #1147 | Lambda S3 key config errors |
| #1148 | Session log updates (pending) |

---

## ECR & Lambda Details

**ECR URL:** `652617421195.dkr.ecr.us-west-2.amazonaws.com/bluemoxon-staging-image-processor`

**Current deployed tag:** `v2`

**Lambda function:** `bluemoxon-staging-image-processor`

**SQS Queue:** `bluemoxon-staging-image-processing`
