# Session: Dashboard Statistics Caching (#1002)

**Date:** 2026-01-10
**Issue:** #1002 - perf: Add caching layer for dashboard statistics
**Status:** IN PROGRESS - VPC Fix Required
**Worktree:** `/Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching`

---

## CRITICAL: Bash Command Rules

**NEVER use (triggers permission prompts):**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls

---

## CRITICAL: Superpowers Skills Required

**MUST invoke relevant skills at ALL stages:**
- `superpowers:using-superpowers` - Start of any task
- `superpowers:brainstorming` - Before implementing features
- `superpowers:test-driven-development` - When writing code
- `superpowers:writing-plans` - For multi-step tasks
- `superpowers:subagent-driven-development` - Executing plans
- `superpowers:finishing-a-development-branch` - After completion

---

## Context

From code review of #965, all stats endpoints hit the database on every request with no caching. With N users refreshing dashboards, we run N * 6+ aggregation queries.

**Design Decisions:**
- Cache scope: Batch level only (`/stats/dashboard`)
- Backend: Redis/ElastiCache Serverless
- Invalidation: TTL-only (5 minutes)
- Rollout: Staging first, then production

---

## Current State

### Completed
- [x] Phase 1: Design (docs/plans/2026-01-10-dashboard-caching-design.md)
- [x] Phase 2: Implementation with TDD (11 tests)
- [x] PR #1028 merged to staging
- [x] Fixed redis in requirements.txt (was missing, causing 500 errors)
- [x] Staging deploy succeeded
- [x] Staging validation passed
- [x] PR #1032 merged to main (code deployment)
- [x] PR #1033 merged to staging (enable_elasticache=true in prod.tfvars)
- [x] PR #1034 merged to main (prod tfvars change)
- [x] Production deploy succeeded (code is deployed)

### BLOCKER: VPC Mismatch
- [x] **FIXED in main.tf** - ElastiCache module was using `data.aws_vpc.default[0].id` instead of `local.lambda_vpc_id`
- [ ] **NEXT:** Commit fix, push through staging-first workflow, then apply Terraform

**Error encountered:**
```
Error: updating Security Group: You have specified two resources that belong to different networks.
```

**Root cause:** ElastiCache security group was being created in default VPC (`vpc-0d5fa6417423d70ff`) but Lambda security group is in dedicated VPC (`vpc-023f4b1dc7c2c4296`).

**Fix applied (not yet committed):**
```terraform
# main.tf line 269 - BEFORE:
vpc_id = data.aws_vpc.default[0].id

# AFTER:
vpc_id = local.lambda_vpc_id
```

### Pending
- [ ] Commit VPC fix to main.tf
- [ ] Push through staging-first workflow (PR to staging, then staging to main)
- [ ] Apply Terraform to production (will create ElastiCache)
- [ ] Verify BMX_REDIS_URL is set in Lambda
- [ ] Validate caching works with timing tests
- [ ] Clean up worktree with `superpowers:finishing-a-development-branch`

---

## Next Steps (Resume Here)

1. **Commit and push the VPC fix:**
   ```
   cd /Users/mark/projects/bluemoxon
   git add infra/terraform/main.tf
   git commit -m "fix(terraform): Use lambda_vpc_id for ElastiCache module (#1002)"
   git push origin <branch>
   ```

2. **Create PR to staging, merge, then promote to main**

3. **Apply Terraform after merge:**
   ```
   cd /Users/mark/projects/bluemoxon/infra/terraform
   AWS_PROFILE=bmx-prod terraform init -backend-config=backends/prod.hcl -reconfigure -input=false
   TF_VAR_db_password=not-used-db-disabled AWS_PROFILE=bmx-prod terraform apply -var-file=envs/prod.tfvars -target=module.elasticache -target=module.lambda -auto-approve
   ```

4. **Verify caching works:**
   ```
   AWS_PROFILE=bmx-prod aws lambda get-function-configuration --function-name bluemoxon-prod-api --query "Environment.Variables.BMX_REDIS_URL"
   bmx-api --prod GET /stats/dashboard
   ```

5. **Use `superpowers:finishing-a-development-branch` to clean up**

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/cache.py` | Cache module with @cached decorator |
| `backend/app/config.py` | Added `redis_url` setting |
| `backend/app/services/dashboard_stats.py` | Dashboard caching integration |
| `backend/requirements.txt` | Added redis>=5.0.0 |
| `infra/terraform/modules/elasticache/` | ElastiCache Terraform module |
| `infra/terraform/main.tf` | ElastiCache integration + BMX_REDIS_URL (VPC FIX APPLIED) |
| `infra/terraform/envs/staging.tfvars` | `enable_elasticache = true` |
| `infra/terraform/envs/prod.tfvars` | `enable_elasticache = true` |

---

## PRs and Commits

| PR | Status | Description |
|----|--------|-------------|
| #1028 | MERGED | Initial caching implementation → staging |
| #1032 | MERGED | Staging → main (code deployment) |
| #1033 | MERGED | enable_elasticache in prod.tfvars → staging |
| #1034 | MERGED | Staging → main (prod tfvars) |

---

## Test Results

- 11 new caching tests (8 cache module + 3 integration)
- 1540 total backend tests pass
- Staging UI validation passed via Playwright

---

## Troubleshooting Notes

**Issue 1:** `ModuleNotFoundError: No module named 'redis'`
- Root cause: `requirements.txt` is manually maintained, not auto-generated from poetry.lock
- Fix: Added `redis>=5.0.0` to `backend/requirements.txt`

**Issue 2:** VPC mismatch for ElastiCache security group
- Root cause: ElastiCache module using default VPC, Lambda in dedicated VPC
- Fix: Changed `vpc_id = data.aws_vpc.default[0].id` to `vpc_id = local.lambda_vpc_id` in main.tf

---

## Session Notes

- Dashboard caching code is deployed and working (graceful degradation when Redis unavailable)
- ElastiCache infrastructure not yet created due to VPC fix needed
- Production is functional but without Redis caching until Terraform is applied
