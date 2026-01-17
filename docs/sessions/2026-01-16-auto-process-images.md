# Session: Auto-Process Images Infrastructure

**Date:** 2026-01-16/17
**Issue:** #1136
**PRs:** #1139, #1141, #1142, #1143, #1145, #1148 (all merged or pending)

## Summary

Deployed infrastructure for automatic image processing during book eval import. Images are queued to SQS and processed by a Lambda worker that removes backgrounds.

**Feature flow:** eBay import → copy images → queue primary image to SQS → Lambda processes → background removed

---

## Current Status (Post E2E Testing)

| Phase | Status | Details |
|-------|--------|---------|
| **Phase 1: Infrastructure** | ✅ DONE | SQS queue, IAM, health checks, Lambda resource (staging + prod) |
| **Phase 2: Lambda Deployment** | ✅ DONE | E2E tested in staging, pending PR |
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
| 8. Test end-to-end in staging | ✅ Done | `5829d22` (v6-models deployed) |
| 9. Deploy to production | ⏳ Pending | After staging PR |

### E2E Test Evidence

**Book 33, Image 2673** was successfully processed:

| Metric | Value |
|--------|-------|
| Model used | isnet-general-use (u2net failed validation) |
| Subject brightness | 59 (dark → black background) |
| New image ID | 5515 |
| S3 path | `books/33/processed_94a7d321-0cdd-4ff4-a6e5-dab3dea234e7.png` |
| Processing time | 155 seconds |
| Memory used | 6199 MB |
| Memory allocated | 10240 MB |

---

## IMMEDIATE Next Steps (Resume Here)

### Code Review Fixes In Progress (PR #1148)

| Issue | Status | Description |
|-------|--------|-------------|
| CI platform mismatch | ✅ Done | deploy.yml: linux/arm64 → linux/amd64 |
| Memory default 10GB | ✅ Done | variables.tf: 10240 → 7168 MB |
| display_order logic | ✅ Done | handler.py: use len(existing_images)+1 |
| No image size validation | ✅ Done | handler.py: MAX_IMAGE_DIMENSION=4096 |
| S3 key format | ✅ Done | handler.py: flat format `{book_id}_processed_{uuid}.png` |
| No secrets caching | ✅ Done | handler.py: added `_db_secret_cache` |
| Magic numbers | ✅ Done | handler.py: extracted constants, GH #1149 for admin |
| ECR lifecycle | ✅ Done | ecr.tf: keep 10 most recent tagged images |

### Remaining Steps

1. Run tests and ruff on handler.py
2. Commit handler.py changes
3. Push all commits to PR #1148
4. Wait for CI to pass
5. After staging merge: `terraform apply` in prod (creates ECR)
6. Promote staging → main

### Production ECR Blocker

Prod ECR repository doesn't exist yet. After staging merge, run:
```bash
cd infra/terraform
AWS_PROFILE=bmx-prod terraform init -backend-config=backends/prod.hcl -reconfigure
AWS_PROFILE=bmx-prod terraform apply -var-file=envs/prod.tfvars
```

---

## Issues Fixed This Session

### 1. ONNX Runtime Crash on Lambda ARM64 (FIXED)

**Problem:** ONNX Runtime crashes at module import on Lambda Graviton2 due to cpuinfo parsing failure.

**Error:**
```
Error in cpuinfo: failed to parse the list of possible processors
onnxruntime::OnnxRuntimeException: Attempt to use DefaultLogger but none has been registered
```

**Solution:** Switched from ARM64 to x86_64 architecture (commit `5829d22`).

### 2. Environment Variable Naming Mismatch (FIXED)

**Problem:** Lambda failed with `DATABASE_SECRET_ARN environment variable not set`.

**Root cause:** Terraform set `DB_SECRET_ARN` but handler expected `DATABASE_SECRET_ARN`.

**Solution:** Fixed Terraform to use consistent naming:
- `DATABASE_SECRET_ARN` (not `DB_SECRET_ARN`)
- `IMAGES_BUCKET` (not `BMX_IMAGES_BUCKET`)
- `IMAGES_CDN_DOMAIN` (not `BMX_IMAGES_CDN_DOMAIN`)

### 3. rembg Model Download at Runtime (FIXED)

**Problem:** Lambda failed with `[Errno 30] Read-only file system: '/home/sbx_user1051'`.

**Root cause:** rembg tries to download models to `~/.u2net/` but Lambda home directory is read-only.

**Solution:**
- Set `U2NET_HOME=/opt/u2net` in Dockerfile during build
- Set `U2NET_HOME=/opt/u2net` in Lambda environment variables
- Models pre-downloaded to `/opt/u2net` during Docker build

### 4. Numba Cache Location (FIXED)

**Problem:** Lambda failed with `cannot cache function '_make_tree': no locator available`.

**Root cause:** pymatting uses Numba JIT with `cache=True` which tries to write to read-only package directory.

**Solution:** Set `NUMBA_CACHE_DIR=/tmp` in Lambda environment variables.

### 5. Out of Memory (FIXED)

**Problem:** Lambda ran out of memory at 1024 MB and 3072 MB.

**Root cause:** rembg with u2net model requires ~6.2 GB memory for processing.

**Solution:** Increased memory to 10240 MB (maximum). Actual usage: ~6199 MB.

### 6. Duplicate books/ in S3 Key (FIXED)

**Problem:** CloudFront URL had `books/books/` path duplication.

**Root cause:** Handler stored `books/33/processed_...` in DB, but API adds `S3_IMAGES_PREFIX` (`books/`) when constructing URLs.

**Solution:** Handler now stores `db_s3_key` (without `books/`) in DB and uses `full_s3_key` (with `books/`) for S3 upload.

### 7. rembg Version Incompatibility (FIXED)

**Problem:** `rembg[cpu]==2.0.50` not available for ARM64.

**Solution:** Changed to `rembg[cpu]>=2.0.55` (versions 2.0.55-2.0.72 available for ARM64).

### 8. Docker Manifest Format (FIXED)

**Problem:** Docker Desktop creates multi-arch manifests with attestations that Lambda rejects.

**Solution:** Use `--provenance=false` flag when building.

### 9. ECR IMMUTABLE Tags (FIXED)

**Problem:** ECR has IMMUTABLE tag policy, can't reuse `:latest`.

**Solution:** Use versioned tags (v1, v2, v3, v5-x86, v6-models, etc.).

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/lambdas/image_processor/handler.py` | Lambda handler with lazy rembg loading |
| `backend/lambdas/image_processor/Dockerfile` | x86_64 container with pre-downloaded models |
| `infra/terraform/modules/image-processor/main.tf` | Container-based Lambda module |
| `infra/terraform/modules/image-processor/variables.tf` | Module variables (memory: 3072 default) |

---

## Lambda Configuration Summary

| Setting | Value | Reason |
|---------|-------|--------|
| Architecture | x86_64 | ONNX Runtime crashes on ARM64 Lambda |
| Memory | 10240 MB (staging) | u2net needs ~6.2 GB |
| Default Memory | 7168 MB (terraform) | Actual usage ~6.2GB + headroom |
| Timeout | 300 seconds | Processing takes 60-150 seconds |
| `U2NET_HOME` | `/opt/u2net` | Pre-downloaded models location |
| `NUMBA_CACHE_DIR` | `/tmp` | Writable cache for JIT |

**Memory:** Terraform default updated to 7168 MB (actual usage ~6.2GB + headroom). Staging was manually set to 10240 MB during testing.

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
13. **ONNX Runtime cpuinfo crash on ARM64** - Use x86_64 architecture instead
14. **Docker provenance** - Use `--provenance=false` for Lambda-compatible images
15. **ECR IMMUTABLE tags** - Use versioned tags (v1, v2, etc.), not :latest
16. **Model imports cascade** - When copying models/, also copy any files they import (constants.py)
17. **rembg model location** - Set `U2NET_HOME` to control where models are stored/loaded
18. **Numba JIT cache** - Set `NUMBA_CACHE_DIR=/tmp` for Lambda's read-only filesystem
19. **rembg memory requirements** - u2net model needs ~6.2 GB RAM; plan for 10 GB
20. **S3 key prefixes** - API adds `books/` prefix; don't double-add in handler

---

## Related Issues & PRs

| Reference | Description |
|-----------|-------------|
| #1136 | Main feature issue (auto-process images) |
| #1140 | Checklist for adding new async workers |
| #1144 | Retry mechanism for `queue_failed` jobs |
| #1146 | API documentation for undocumented endpoints |
| #1147 | Lambda S3 key config errors |
| #1148 | Image processor Lambda PR (in review) |
| #1149 | Display image processing constants in admin config |

---

## Files Modified This Session (Uncommitted)

**handler.py changes:**
- Extracted constants: `MIN_AREA_RATIO`, `MAX_ASPECT_DIFF`, `MAX_IMAGE_DIMENSION`, `U2NET_FALLBACK_ATTEMPT`
- Added `_db_secret_cache` for secrets caching between warm invocations
- Added `validate_image_size()` function
- Fixed S3 key format: `{book_id}_processed_{uuid}.png` (flat, matches other images)
- Fixed display_order: uses `len(existing_images) + 1` instead of broken `max_display_order + 1`
- Removed unused `func` import

**Other files (already committed by subagents):**
- deploy.yml: `--platform linux/amd64` (was arm64)
- variables.tf: `default = 7168` (was 10240)
- ecr.tf: Added lifecycle rule to keep 10 most recent tagged images

---

## ECR & Lambda Details

**ECR URL:** `652617421195.dkr.ecr.us-west-2.amazonaws.com/bluemoxon-staging-image-processor`

**Current deployed tag:** `v6-models`

**Lambda function:** `bluemoxon-staging-image-processor`

**SQS Queue:** `bluemoxon-staging-image-processing`

**Memory (staging):** 10240 MB (manually increased for testing; CI will use Terraform default of 3072)
