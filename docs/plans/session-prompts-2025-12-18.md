# Session Start Prompts for Infrastructure Work

**Created:** 2025-12-18
**Status:** Current open issues organized by priority tier

## Overview

Use these prompts when starting new Claude sessions to provide context for infrastructure work. Each prompt includes:
- Issue context and parent relationships
- Technical details and file paths
- Recommended superpowers skills to use

## Issue Summary (20 open)

| Category | Issues |
|----------|--------|
| **Bugs** | #354 (old analysis), #343 (5min timeout) |
| **Features** | #388 (tiered recs - includes #383, #330), #276 (binder context) |
| **Infrastructure** | #229 (epic), #389 (prod import - sub-epic), #295, #293, #287, #235, #234, #233, #232, #228 |
| **CI/CD** | #310 (Lambda versioning), #299 (eBay smoke test) |
| **Cleanup** | #191, #190, #189 (Phase 4 admin cleanup) |
| **Tech debt** | #166 (Tailwind v4) |

## Priority Structure

```
#229 EPIC: Staging/Prod Parity
├── #389 Sub-epic: Prod Imports (5 phases)
├── #293 Cross-account S3 (Tier 1 - foundation)
├── #295 Lambda concurrency limit (Tier 1 - submit now)
├── #287 Auto-sync Cognito (Tier 2 - needs #293)
├── #235 Pre-deploy drift (Tier 2 - needs #389)
├── #228 Auto-gen CLAUDE.md (Tier 2)
├── #232 Standardize env vars (Tier 3)
├── #234 Standardize naming (Tier 3)
└── #233 Staging images domain (Tier 3)
```

---

## Tier 1: Foundation

### #293 - Cross-Account S3 Access for GitHub Actions

```
I'm working on infrastructure issue #293 - Add cross-account Terraform state S3 access to GitHub Actions OIDC role.

**Context:**
- Parent epic: #229 (Staging/Prod Parity)
- This unblocks: #287 (Auto-sync Cognito config)
- Problem: GitHub Actions in staging account (652617421195) can't access Terraform state bucket in prod account (266672885920)
- Root cause: Cross-account S3 needs BOTH bucket policy AND IAM role policy

**Current state:**
- Bucket policy added ✅
- IAM policy on github-actions-deploy role ❌

**Options documented in issue:**
1. Manual IAM fix via AWS Console
2. Enable github-oidc module in Terraform
3. Separate TF state buckets per environment

**Files involved:**
- `infra/terraform/modules/github-oidc/main.tf`
- `infra/terraform/envs/staging.tfvars` (enable_github_oidc = false)
- `.github/workflows/deploy.yml`

Use the superpowers:brainstorming skill to evaluate options, then superpowers:writing-plans for implementation.
```

---

### #295 - Lambda Concurrency Limit Increase

```
I'm working on infrastructure issue #295 - Request AWS Lambda concurrency limit increase for provisioned concurrency.

**Context:**
- Parent epic: #229 (Staging/Prod Parity)
- Problem: Prod AWS account has 10 concurrent execution limit (minimum required for unreserved)
- Impact: Can't enable provisioned concurrency for warm starts
- Current config: `lambda_provisioned_concurrency = 0` in prod.tfvars line 17

**Action needed:**
1. Submit AWS Support request for limit increase (10 → 100)
2. Document the request
3. After approval, update prod.tfvars to enable provisioned concurrency

This is a support request task - use superpowers:verification-before-completion to confirm request was submitted with correct details.
```

---

### #389 - Import Production Resources (Sub-Epic)

```
I'm working on infrastructure issue #389 - Import production resources into Terraform state.

**Context:**
- Parent epic: #229 (Staging/Prod Parity)
- Absorbs: #296 (API Gateway), #226 (RDS), #231 (VPC endpoints)
- Reference: Staging has 109 resources across 14 modules

**Phases:**
1. Core: S3 buckets (frontend, images), CloudFront distributions
2. Lambda: API function, API Gateway, analysis worker, eval runbook worker
3. Database: RDS instance, Secrets Manager, Cognito
4. Networking: VPC endpoints for S3, Secrets Manager
5. Scraper: Scraper Lambda, EventBridge warmup

**Key files:**
- `infra/terraform/envs/prod.tfvars` - enable_* flags
- `infra/terraform/modules/` - all modules
- `docs/PROD_MIGRATION_CHECKLIST.md` - reference

**Import pattern:**
```bash
AWS_PROFILE=bmx-prod terraform import 'module.X.aws_Y.this' <resource-id>
```

Use superpowers:brainstorming to plan each phase, superpowers:writing-plans for detailed import steps, superpowers:verification-before-completion after each import to confirm terraform plan shows no changes.
```

---

## Tier 2: Automation

### #287 - Auto-Sync Cognito Config from Terraform

```
I'm working on infrastructure issue #287 - Auto-sync Cognito config from Terraform outputs.

**Context:**
- Parent epic: #229 (Staging/Prod Parity)
- Blocked by: #293 (cross-account S3 access)
- Problem: Static config files (infra/config/*.json) drift from Terraform state
- Symptom: "User pool client does not exist" errors after Terraform recreates Cognito

**Proposed solution from issue:**
Replace static config read in deploy.yml with:
```yaml
- name: Get Terraform outputs
  run: |
    terraform init -backend-config="..."
    echo "cognito_user_pool_id=$(terraform output -raw cognito_user_pool_id)" >> $GITHUB_OUTPUT
```

**Files involved:**
- `.github/workflows/deploy.yml` - currently reads static config (line 79)
- `.github/workflows/deploy-staging.yml` - same pattern
- `infra/config/staging.json`, `infra/config/prod.json` - static configs
- `infra/terraform/outputs.tf` - Terraform outputs

Use superpowers:brainstorming to validate approach, superpowers:writing-plans for implementation, superpowers:test-driven-development to add validation tests.
```

---

### #235 - Pre-Deploy Terraform Drift Check

```
I'm working on infrastructure issue #235 - Add pre-deploy Terraform drift check to deploy workflow.

**Context:**
- Parent epic: #229 (Staging/Prod Parity)
- Blocked by: #389 (prod resources must be in Terraform first)
- Goal: Run `terraform plan -detailed-exitcode` before deploy, warn/block on drift

**Options from issue:**
1. Warn only - log warning, continue deploy
2. Fail deploy - block until drift resolved
3. Require approval - pause for manual approval

**Proposed addition to deploy.yml:**
```yaml
- name: Check for infrastructure drift
  run: |
    terraform plan -detailed-exitcode -var-file=envs/$ENV.tfvars
    # Exit code 2 = drift detected
```

**Files involved:**
- `.github/workflows/deploy.yml`
- `.github/workflows/deploy-staging.yml`
- `infra/terraform/envs/*.tfvars`

Use superpowers:brainstorming to decide warn vs block behavior, superpowers:writing-plans for implementation.
```

---

### #228 - Auto-Generate CLAUDE.md from Terraform

```
I'm working on infrastructure issue #228 - Auto-generate CLAUDE.md from Terraform outputs.

**Context:**
- Parent epic: #229 (Staging/Prod Parity)
- Problem: CLAUDE.md has hardcoded values that drift (e.g., Cognito pool IDs)
- Solution: Template + generation script + CI validation

**Proposed approach from issue:**
1. Create `CLAUDE.md.template` with `${VAR}` placeholders
2. Create `scripts/generate-claude-md.sh` using envsubst
3. Add CI step to validate CLAUDE.md matches Terraform

**Files involved:**
- `CLAUDE.md` - current file with hardcoded values
- `scripts/` - new generation script
- `.github/workflows/ci.yml` - add validation step

Use superpowers:brainstorming to identify which values to templatize, superpowers:writing-plans for implementation.
```

---

## Tier 3: Standardization

### #232 - Standardize Lambda Environment Variables

```
I'm working on infrastructure issue #232 - Standardize Lambda environment variables across environments.

**Context:**
- Parent epic: #229 (Staging/Prod Parity)
- Problem: Staging and prod use different env var names for same purpose

**Current differences from issue:**
| Purpose | Staging | Prod | Recommended |
|---------|---------|------|-------------|
| S3 bucket | IMAGES_BUCKET | S3_BUCKET | IMAGES_BUCKET |
| CDN domain | IMAGES_CDN_DOMAIN | CLOUDFRONT_DOMAIN | IMAGES_CDN_DOMAIN |
| API key | API_KEY_HASH | API_KEY | API_KEY_HASH |

**Risk:** Renaming requires coordinated deploy of code + config

**Files involved:**
- `infra/terraform/modules/lambda/main.tf` - env var definitions
- `backend/app/core/config.py` - Python settings reading env vars
- `infra/terraform/envs/*.tfvars` - environment-specific values

Use superpowers:brainstorming to plan migration strategy, superpowers:systematic-debugging if issues arise during testing.
```

---

### #234 - Standardize Lambda Naming Convention

```
I'm working on infrastructure issue #234 - Standardize Lambda function naming convention.

**Context:**
- Parent epic: #229 (Staging/Prod Parity)
- Problem: Inconsistent naming (staging vs production vs prod vs no prefix)

**Current state from issue:**
| Function | Staging | Production |
|----------|---------|------------|
| API | bluemoxon-staging-api | bluemoxon-api |
| Scraper | bluemoxon-staging-scraper | bluemoxon-production-scraper |

**Proposed convention:** `bluemoxon-{env}-{function}` where env is `staging` or `prod`

**Risk:** Changing Lambda names requires API Gateway integration updates + maintenance window

**Files involved:**
- `infra/terraform/modules/lambda/main.tf`
- `infra/terraform/envs/*.tfvars` - name overrides
- API Gateway integrations

Use superpowers:brainstorming to evaluate migration approach, superpowers:writing-plans for rollout strategy.
```

---

### #233 - Custom Domain for Staging Images

```
I'm working on infrastructure issue #233 - Add custom domain for staging images CloudFront.

**Context:**
- Parent epic: #229 (Staging/Prod Parity)
- Problem: Staging uses raw CloudFront domain, prod uses branded path

**Current state:**
| Environment | Pattern |
|-------------|---------|
| Staging | d5vxz9xesytgw.cloudfront.net/books/... |
| Production | app.bluemoxon.com/book-images/books/... |

**Options from issue:**
- Option A: `staging.images.bluemoxon.com` (dedicated subdomain)
- Option B: `staging.app.bluemoxon.com/book-images/` (match prod pattern)

**Files involved:**
- `infra/terraform/modules/images-cdn/main.tf`
- `infra/terraform/envs/staging.tfvars`
- Route53 records

Use superpowers:brainstorming to decide domain pattern, superpowers:writing-plans for implementation.
```

---

## CI/CD (Independent)

### #310 - Lambda Versioning and Smoke Tests

```
I'm working on CI/CD issue #310 - Add versioning and smoke tests for all Lambda functions.

**Context:**
- Independent of infrastructure epic
- Goal: Consistent version exposure and smoke tests across all Lambdas

**Current state from issue:**
| Lambda | Versioning | Smoke Test |
|--------|------------|------------|
| API | ✅ VERSION file | ✅ /health/version |
| Worker | ❌ None | ❌ None |
| Scraper | ✅ VERSION in Docker | ✅ Lambda invoke |

**Proposed changes:**
1. Worker Lambda versioning (uses same zip as API)
2. Worker smoke test with test payload
3. Consistent APP_VERSION env var and X-App-Version header

**Files involved:**
- `.github/workflows/deploy.yml` - add version publish + smoke tests
- `backend/app/` - version handling code

Use superpowers:writing-plans for implementation, superpowers:test-driven-development for smoke test design.
```

---

### #299 - eBay Extract Endpoint Smoke Test

```
I'm working on CI/CD issue #299 - Add smoke test for eBay URL extract endpoint.

**Context:**
- Independent of infrastructure epic
- Problem: `/api/v1/listings/extract` caused 502 errors that weren't caught by existing smoke tests
- Root causes: ENVIRONMENT vs BMX_ENVIRONMENT, IMAGES_BUCKET vs BMX_IMAGES_BUCKET

**Proposed smoke test:**
1. POST to /api/v1/listings/extract with known eBay URL
2. Validate 200 status or 429 (rate limit = endpoint working)
3. Validate presigned URLs returned (catches S3 bucket issues)

**Files involved:**
- `.github/workflows/deploy.yml` - smoke test section
- Need stable test eBay URL or mock validation

Use superpowers:writing-plans for test design, superpowers:systematic-debugging if test reveals issues.
```

---

## Features

### #388 - Tiered Recommendations

```
I'm working on feature issue #388 - Tiered recommendations with offer prices and reasoning.

**Context:**
- Incorporates: #383 (scoring+FMV), #330 (tier classification)
- Prerequisites: #384 (FMV Accuracy) ✅ implemented
- Design doc: `docs/plans/2025-12-17-tiered-recommendations-design.md`

**Goal:** Transform eval runbook from binary ACQUIRE/PASS to:
- STRONG_BUY | BUY | CONDITIONAL | PASS
- Suggested offer price for CONDITIONAL
- 1-2 sentence reasoning

**Recommendation matrix:**
| | Price < 80% FMV | Price 80-100% FMV | Price > 100% FMV |
|---|---|---|---|
| **Score >= 90** | STRONG BUY | BUY | CONDITIONAL |
| **Score 70-89** | BUY | CONDITIONAL | PASS |
| **Score < 70** | CONDITIONAL | PASS | PASS |

**Files involved:**
- `backend/app/services/eval_generation.py` - recommendation logic
- `backend/app/services/scoring.py` - quality score
- `backend/app/models/` - author, publisher, binder tier fields
- `frontend/src/components/` - eval runbook modal display

Use superpowers:brainstorming to validate design, superpowers:writing-plans for implementation phases, superpowers:test-driven-development for scoring logic.
```

---

### #276 - Binder Context in Analysis Prompts

```
I'm working on feature issue #276 - Analysis prompt enhancement for binder context (Phase 3 of #237).

**Context:**
- Parent: #237 (Analysis Enrichment)
- Problem: Analysis prompts don't include binder tier/quality info

**Current state:**
- Basic binder name included in `bedrock.py:266-267`
- Missing: tier, quality characteristics, image cues

**Goal:** When binder is assigned, add to prompt:
- Binder name and tier
- Known quality characteristics
- What to look for in images (stamps, signatures, binding style)

**Files involved:**
- `backend/app/services/bedrock.py` - prompt generation
- `backend/app/models/binder.py` - binder model (needs tier field from #330)

Use superpowers:brainstorming to design prompt enhancement, superpowers:writing-plans for implementation.
```

---

## Bugs

### #354 - Old Analysis Used for New Evaluations

```
I'm working on bug #354 - New addition to evaluations uses an old analysis.

**Problem:** When adding a book to evaluations in the acquisition flow, it sometimes uses stale/old analysis data instead of generating fresh analysis.

**Files to investigate:**
- `frontend/src/views/AcquisitionsView.vue`
- `backend/app/routers/books.py`
- `backend/app/services/` - analysis generation

Use superpowers:systematic-debugging to trace the issue, superpowers:root-cause-tracing to find where stale data originates.
```

---

### #343 - Napoleon Analysis 5-Minute Timeout

```
I'm working on bug #343 - Napoleon analysis takes exactly 5 minutes to generate.

**Problem:** Analysis generation consistently times out at exactly 5 minutes, suggesting a timeout configuration issue rather than actual processing time.

**Files to investigate:**
- `backend/app/services/bedrock.py` - Bedrock API calls
- `infra/terraform/modules/lambda/main.tf` - Lambda timeout config
- API Gateway timeout settings

Use superpowers:systematic-debugging to identify timeout source, superpowers:root-cause-tracing to find the limiting factor.
```

---

## Superpowers Skill Reference

| Task Type | Skill Chain |
|-----------|-------------|
| **New feature** | brainstorming → using-git-worktrees → writing-plans → subagent-driven-development |
| **Debugging** | systematic-debugging → root-cause-tracing → defense-in-depth |
| **Writing tests** | test-driven-development → condition-based-waiting → testing-anti-patterns |
| **Code review** | requesting-code-review → receiving-code-review |
| **Completing work** | verification-before-completion → finishing-a-development-branch |
