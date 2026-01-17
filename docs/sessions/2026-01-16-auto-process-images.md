# Session: Auto-Process Images Infrastructure

**Date:** 2026-01-16/17
**Issue:** #1136
**PRs:** #1139, #1141, #1142, #1143, #1145, #1148 (all merged or pending)

## Summary

Deployed infrastructure for automatic image processing during book eval import. Images are queued to SQS and processed by a Lambda worker that removes backgrounds.

**Feature flow:** eBay import → copy images → queue primary image to SQS → Lambda processes → background removed

---

## Current Status (Post-Compaction 4)

| Phase | Status | Details |
|-------|--------|---------|
| **Phase 1: Infrastructure** | ✅ DONE | SQS queue, IAM, health checks, Lambda resource (staging + prod) |
| **Phase 2: Lambda Deployment** | 🔶 CODE DONE | Implementation complete, bootstrap image pending |
| **Phase 3: API Integration** | ✅ DONE | PR #1143 - `queue_image_processing()` called during import |

### Phase 2 Implementation Progress

All code tasks complete on `feat/auto-process-images` branch:

| Task | Status | Commit |
|------|--------|--------|
| 1. ECR repository (Terraform) | ✅ Done | `1d6a348` |
| 2. Supporting files (Dockerfile, requirements.txt, download_models.py) | ✅ Done | `0a91d34` |
| 3. Smoke test handler | ✅ Done | `164ac27` |
| 4. Push bootstrap image | ⏳ Pending | Manual step |
| 5. Lambda module for container | ✅ Done | `25c10fb` |
| 6. Unit tests (30 passing) | ✅ Done | `b39628f` |
| 7. CI/CD workflow | ✅ Done | `078aca5` |
| 8. Test end-to-end in staging | ⏳ Pending | After bootstrap |
| 9. Deploy to production | ⏳ Pending | After staging |

**Key files created/modified:**
- `infra/terraform/ecr.tf` - ECR repository
- `infra/terraform/modules/image-processor/main.tf` - Container-based Lambda
- `infra/terraform/outputs.tf` - Added image processor outputs
- `backend/lambdas/image_processor/Dockerfile` - ARM64 container build
- `backend/lambdas/image_processor/requirements.txt` - rembg + dependencies
- `backend/lambdas/image_processor/download_models.py` - Pre-download models
- `backend/lambdas/image_processor/handler.py` - Added smoke test support
- `backend/lambdas/image_processor/tests/` - 30 unit tests
- `.github/workflows/deploy.yml` - CI/CD for image processor

### API Key Fix - COMPLETED

| Item | Status |
|------|--------|
| Staging Lambda API key | ✅ Updated |
| Prod Lambda API key | ✅ Updated |
| Local ~/.bmx/ keys | ✅ Updated |
| GitHub secrets | ✅ Updated |
| CI workflow | ✅ Passing (run 21087968669) |

**Keys stored in Secrets Manager:**
- `bluemoxon-staging/api-key`
- `bluemoxon-prod/api-key`

### Phase 2 Design - COMPLETED

**Design document:** `docs/plans/2026-01-17-image-processor-container.md`

**Key decisions:**
- ARM64 container on Graviton2 (20% cost savings)
- Models baked into container (instant cold starts)
- Copy `backend/app/models/` for single source of truth
- CI updates Lambda directly, Terraform ignores `image_uri`

---

## IMMEDIATE Next Steps (Resume Here)

### Task 4: Push Bootstrap Image - IN PROGRESS

**Status:** ECR repository created, but Docker build failed due to rembg version issue.

**Issue:** `rembg[cpu]==2.0.50` is not available for ARM64. Available versions: 2.0.55-2.0.72

**Fix needed:** Update `backend/lambdas/image_processor/requirements.txt` to use `rembg[cpu]>=2.0.55` or pin to latest stable version.

**ECR URL:** `652617421195.dkr.ecr.us-west-2.amazonaws.com/bluemoxon-staging-image-processor`

**Steps to complete Task 4:**
1. Fix requirements.txt rembg version
2. Rebuild: `docker build --platform linux/arm64 -f backend/lambdas/image_processor/Dockerfile -t 652617421195.dkr.ecr.us-west-2.amazonaws.com/bluemoxon-staging-image-processor:latest /Users/mark/projects/bluemoxon/.worktrees/auto-process-images`
3. Push: `docker push 652617421195.dkr.ecr.us-west-2.amazonaws.com/bluemoxon-staging-image-processor:latest`
4. Apply full Terraform: `AWS_PROFILE=bmx-staging terraform -chdir=/Users/mark/projects/bluemoxon/.worktrees/auto-process-images/infra/terraform apply -var-file=envs/staging.tfvars`

**Also fixed during this session:**
- Removed duplicate `image_processor_ecr_url` output (was in both ecr.tf and outputs.tf)
- Updated main.tf to use `ecr_repository_url` instead of `s3_bucket`/`s3_key`
- Fixed `image_processor_function_name` output to use `[0]` index for count-based module

### After Bootstrap: Create PR to Staging

Once bootstrap is complete, create PR and validate in staging before promoting to production

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

## Key Files

| File | Purpose |
|------|---------|
| `docs/plans/2026-01-17-image-processor-container.md` | Phase 2 design document |
| `backend/lambdas/image_processor/handler.py` | Lambda handler (exists) |
| `infra/terraform/modules/image-processor/main.tf` | Terraform module (needs refactor) |

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
12. **ARM64 package availability differs** - rembg 2.0.50 not available for ARM64; check PyPI for ARM-compatible versions before pinning
