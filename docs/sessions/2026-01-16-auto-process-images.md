# Session: Auto-Process Images Infrastructure

**Date:** 2026-01-16/17
**Issue:** #1136
**PRs:** #1139, #1141, #1142, #1143, #1145, #1148 (all merged or pending)

## Summary

Deployed infrastructure for automatic image processing during book eval import. Images are queued to SQS and processed by a Lambda worker that removes backgrounds.

**Feature flow:** eBay import → copy images → queue primary image to SQS → Lambda processes → background removed

---

## Current Status (Post-Compaction 3)

| Phase | Status | Details |
|-------|--------|---------|
| **Phase 1: Infrastructure** | ✅ DONE | SQS queue, IAM, health checks, Lambda resource (staging + prod) |
| **Phase 2: Lambda Deployment** | 🔶 DESIGN DONE | Design complete, ready for implementation |
| **Phase 3: API Integration** | ✅ DONE | PR #1143 - `queue_image_processing()` called during import |

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

### Phase 2 Implementation - Use Subagent-Driven Development

**Required skill:** `superpowers:subagent-driven-development`

**Approach:** Maximum parallelism with worktrees for isolated work

**Implementation tasks (from design doc):**

1. **Create ECR repository** (Terraform) - independent
2. **Push bootstrap image** (manual, one-time) - depends on 1
3. **Update Lambda module** (Terraform) - depends on 1
4. **Add supporting files** (Dockerfile, requirements.txt, download_models.py) - independent
5. **Add smoke test handler** (handler.py modification) - independent
6. **Add unit tests** (tests/) - depends on 5
7. **Update CI/CD workflow** (deploy.yml) - depends on 1, 4
8. **Test end-to-end** (staging) - depends on all above
9. **Deploy to prod** - depends on 8

**Parallelization opportunities:**
- Tasks 1, 4, 5 can run in parallel (independent)
- Task 6 can start once 5 is done
- Tasks 2, 3, 7 can run in parallel once 1 is done

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
