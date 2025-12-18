# Infrastructure Standardization Design

> **For Claude:**
> - REQUIRED: Use `superpowers:subagent-driven-development` to execute this plan
> - Use `superpowers:test-driven-development` for any code changes
> - Use `superpowers:verification-before-completion` before claiming any phase complete
> - Use `superpowers:systematic-debugging` if issues arise during deployment
> - Use `superpowers:finishing-a-development-branch` when all phases complete

**Goal:** Standardize Lambda environment variables, function naming, and images CDN URLs across staging and production.

**Issues:** #232 (env vars), #233 (images domain - already done for staging), #234 (Lambda naming)

**Architecture:** Update Terraform modules and backend code to use consistent naming patterns. Rename production Lambdas to match staging convention.

**Tech Stack:** Terraform, AWS Lambda, API Gateway, Python/FastAPI

---

## Current State

### Environment Variables

| Variable | Staging | Prod | Action |
|----------|---------|------|--------|
| `BMX_DATABASE_SECRET_NAME` | ✓ (name) | ✗ | Remove from staging |
| `BMX_DATABASE_SECRET_ARN` | ✗ | ✓ | Add to staging |
| `BMX_IMAGES_CDN_URL` | `staging.app.bluemoxon.com/book-images` | `d1yejmcspwgw9x.cloudfront.net` | Fix prod to `app.bluemoxon.com/book-images` |

### Lambda Naming

| Function | Staging | Production | Target |
|----------|---------|------------|--------|
| API | `bluemoxon-staging-api` | `bluemoxon-api` | `bluemoxon-prod-api` |
| Scraper | `bluemoxon-staging-scraper` | `bluemoxon-production-scraper` | `bluemoxon-prod-scraper` |
| Analysis | `bluemoxon-staging-analysis-worker` | `bluemoxon-prod-analysis-worker` | ✓ No change |
| Eval Runbook | `bluemoxon-staging-eval-runbook-worker` | `bluemoxon-prod-eval-runbook-worker` | ✓ No change |

### Images CDN

- Staging: `staging.app.bluemoxon.com/book-images/` → 200 ✓ (already working)
- Production: `app.bluemoxon.com/book-images/` → 200 ✓ (path works, env var needs update)

**#233 is already complete for staging.** Only prod env var needs fixing.

---

## Implementation Phases

> **Skills per phase:**
> - Each task: `superpowers:test-driven-development` (write test, verify fail, implement, verify pass)
> - After each task: `superpowers:requesting-code-review` via subagent
> - Before marking complete: `superpowers:verification-before-completion`

### Phase 1: Low-Risk Changes (No Downtime)

**Task 1.1: Update backend code**
- File: `backend/app/core/config.py`
- Change: Use `BMX_DATABASE_SECRET_ARN` instead of `BMX_DATABASE_SECRET_NAME`
- The code should check for ARN first, fall back to name for backward compatibility during transition

**Task 1.2: Update Terraform Lambda module**
- File: `infra/terraform/modules/lambda/main.tf`
- Add `BMX_DATABASE_SECRET_ARN` environment variable
- Remove `BMX_DATABASE_SECRET_NAME` after code is deployed

**Task 1.3: Fix prod images CDN URL**
- File: `infra/terraform/envs/prod.tfvars` or Lambda module
- Change `BMX_IMAGES_CDN_URL` to `https://app.bluemoxon.com/book-images`

### Phase 2: Scraper Rename (Low Risk)

**Task 2.1: Rename production scraper**
- Current: `bluemoxon-production-scraper`
- Target: `bluemoxon-prod-scraper`
- Update `scraper_function_name_override` in prod.tfvars
- Update any `scraper_lambda_arn` references

**Note:** This requires Terraform to create new function, which may need manual state management or import.

### Phase 3: API Lambda Rename (High Risk - Downtime Acceptable)

**Task 3.1: Rename production API Lambda**
- Current: `bluemoxon-api`
- Target: `bluemoxon-prod-api`
- Update `lambda_function_name_override` in prod.tfvars

**Task 3.2: Update API Gateway integration**
- API Gateway must point to new Lambda name
- This happens automatically if Terraform manages the integration

**Rollback Plan:**
- Keep old Lambda for 24 hours
- If issues, revert Terraform and re-apply

---

## Verification Plan

> **CRITICAL:** Use `superpowers:verification-before-completion` - run ALL checks below and confirm output BEFORE claiming phase complete.

After each phase:

```bash
# Health check
curl https://staging.api.bluemoxon.com/api/v1/health/deep
curl https://api.bluemoxon.com/api/v1/health/deep

# Images load
curl -I https://staging.app.bluemoxon.com/book-images/books/1/cover.jpg
curl -I https://app.bluemoxon.com/book-images/books/1/cover.jpg

# API responds
bmx-api GET /books?limit=1
bmx-api --prod GET /books?limit=1

# Scraper works (staging)
AWS_PROFILE=bmx-staging aws lambda invoke --function-name bluemoxon-staging-scraper --payload '{"warmup": true}' .tmp/scraper-test.json
```

---

## Deployment Strategy

> **Workflow:** Use `superpowers:finishing-a-development-branch` after all phases complete.

```
1. Create feature branch from staging
   → Use superpowers:using-git-worktrees for isolation

2. PR to staging branch: Phase 1 changes
   ↓ merge, deploy, verify staging
   → Use superpowers:verification-before-completion

3. PR staging → main: Phase 1 + Phase 2 + Phase 3
   ↓ merge, deploy, verify production
   → Use superpowers:verification-before-completion

4. Close issues #232, #233, #234
   → Use superpowers:finishing-a-development-branch
```

## Troubleshooting

> **If any verification fails:** Use `superpowers:systematic-debugging`
> - Phase 1: Investigate → `superpowers:root-cause-tracing`
> - Do NOT guess at fixes
> - Trace data flow from env var → code → error

---

## Files to Modify

### Backend
- `backend/app/core/config.py` - Database secret ARN handling

### Terraform
- `infra/terraform/modules/lambda/main.tf` - Environment variables
- `infra/terraform/modules/lambda/variables.tf` - Variable definitions
- `infra/terraform/envs/prod.tfvars` - Name overrides, CDN URL
- `infra/terraform/main.tf` - Module invocations if needed

### Potentially
- `infra/terraform/modules/scraper-lambda/` - If scraper rename needs changes
- `.github/workflows/deploy.yml` - If Lambda names are hardcoded

---

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Database secret ARN | Low | Backward-compatible code change |
| Images CDN URL | Low | URL already works, just env var update |
| Scraper rename | Medium | Only API Lambda invokes it |
| API Lambda rename | High | Downtime acceptable, keep old Lambda 24hrs |

---

## Decision Log

- 2025-12-18: Chose to include Phase 3 (API rename) despite downtime risk
- 2025-12-18: Chose path-based images URL (`app.bluemoxon.com/book-images`) over subdomain
- 2025-12-18: Discovered #233 already complete for staging, only prod needs fix
