# Design: Separate S3 Bucket for Lambda Artifacts

**Date:** 2026-01-07
**Status:** Ready for Implementation
**Issue:** Recurring S3 deletion bug (fixes in #899, #908 session repeatedly lost)

---

## Problem Statement

Lambda artifacts (`backend.zip`, `layer-*.zip`) are stored in the frontend S3 bucket (`bluemoxon-frontend-{env}`). The frontend deploy job runs `aws s3 sync --delete`, which deletes the `lambda/` folder when running in parallel with Lambda deploys.

**Root cause:** Architectural coupling - two unrelated deployments sharing one S3 bucket.

**Why fixes keep getting lost:** The `--exclude lambda/*` workaround is a single line in a 1500-line workflow file. PRs that modify deploy.yml without rebasing can silently overwrite the fix.

---

## Solution

Create a dedicated `bluemoxon-artifacts-{env}` S3 bucket for Lambda artifacts, eliminating the coupling entirely.

### Architecture

```
BEFORE (coupled):
┌─────────────────────────────────────────────┐
│  bluemoxon-frontend-{env}                   │
│  ├── index.html          (frontend)         │
│  ├── assets/*            (frontend)         │
│  ├── lambda/backend.zip  (Lambda code)      │  <- COUPLING
│  └── lambda/layer-*.zip  (Lambda layer)     │  <- COUPLING
└─────────────────────────────────────────────┘
         ↑                        ↑
   frontend sync            Lambda deploy
   (--delete)               (reads artifacts)
         │
         └── RACE CONDITION: sync deletes lambda/*

AFTER (decoupled):
┌─────────────────────────┐  ┌─────────────────────────┐
│ bluemoxon-frontend-{env}│  │ bluemoxon-artifacts-{env}│
│ ├── index.html          │  │ ├── lambda/backend.zip   │
│ ├── assets/*            │  │ └── lambda/layer-*.zip   │
│ └── (no lambda/)        │  └─────────────────────────┘
└─────────────────────────┘           ↑
         ↑                      Lambda deploy
   frontend sync                (reads artifacts)
   (--delete is safe)
         │
         └── NO RACE: buckets are independent
```

---

## Implementation Tasks

### Task 1: Add artifacts bucket module (Terraform)

**File:** `infra/terraform/main.tf`

```hcl
# =============================================================================
# Artifacts Bucket (Lambda packages, build artifacts)
# =============================================================================

module "artifacts_bucket" {
  source = "./modules/s3"

  bucket_name         = "${var.app_name}-artifacts-${var.environment}"
  enable_versioning   = false  # Not needed for build artifacts
  block_public_access = true   # No public access needed
  enable_website      = false  # Not a website

  tags = local.common_tags
}
```

### Task 2: Add artifacts bucket output (Terraform)

**File:** `infra/terraform/outputs.tf`

```hcl
output "artifacts_bucket_name" {
  description = "S3 bucket for CI/CD artifacts (Lambda packages, layers)"
  value       = module.artifacts_bucket.bucket_name
}
```

### Task 3: Update GitHub OIDC IAM policy (Terraform)

**File:** `infra/terraform/modules/github-oidc/main.tf`

Add new variable and update IAM policy to allow access to artifacts bucket.

**File:** `infra/terraform/main.tf` (github_oidc module call)

```hcl
module "github_oidc" {
  # ...existing...
  artifacts_bucket_arns = [module.artifacts_bucket.bucket_arn]
}
```

### Task 4: Update Lambda layer to use artifacts bucket (Terraform)

**File:** `infra/terraform/main.tf`

```hcl
module "lambda_layer" {
  # ...
  s3_bucket = module.artifacts_bucket.bucket_id  # Changed from frontend_bucket
  s3_key    = "lambda/layer.zip"
}
```

### Task 5: Add artifacts_bucket to configure job outputs (Workflow)

**File:** `.github/workflows/deploy.yml`

In the `Read Terraform outputs` step:

```yaml
ARTIFACTS_BUCKET=$(terraform output -raw artifacts_bucket_name)
echo "artifacts_bucket=$ARTIFACTS_BUCKET" >> $GITHUB_OUTPUT
```

Add to job outputs:

```yaml
outputs:
  # ...existing...
  artifacts_bucket: ${{ steps.tf-outputs.outputs.artifacts_bucket }}
```

### Task 6: Update build-layer to use artifacts bucket (Workflow)

**File:** `.github/workflows/deploy.yml`

Update layer check step:

```yaml
S3_BUCKET="${{ needs.configure.outputs.artifacts_bucket }}"
if aws s3 ls "s3://${S3_BUCKET}/lambda/layer-${REQ_HASH}.zip" 2>/dev/null; then
```

Update upload step:

```yaml
S3_BUCKET="${{ needs.configure.outputs.artifacts_bucket }}"
aws s3 cp layer.zip "s3://${S3_BUCKET}/lambda/layer-${LOCK_HASH}.zip"
aws s3 cp layer.zip "s3://${S3_BUCKET}/lambda/layer.zip"
```

### Task 7: Update deploy-api-lambda to use artifacts bucket (Workflow)

**File:** `.github/workflows/deploy.yml`

Update S3 upload:

```yaml
aws s3 cp lambda-package.zip s3://${{ needs.configure.outputs.artifacts_bucket }}/lambda/backend.zip
```

Update layer publish:

```yaml
S3_BUCKET="${{ needs.configure.outputs.artifacts_bucket }}"
```

### Task 8: Remove --exclude lambda/* from frontend sync (Workflow)

**File:** `.github/workflows/deploy.yml`

Remove `--exclude "lambda/*"` from the frontend sync command (no longer needed).

---

## Rollout Plan

```
Phase 1: Terraform (staging)
├── Tasks 1-4
├── terraform apply -var-file=envs/staging.tfvars
└── Verify: aws s3 ls s3://bluemoxon-artifacts-staging/

Phase 2: Workflow (staging)
├── Tasks 5-8
├── Push to staging branch
└── Verify: deploy succeeds, layer publishes from new bucket

Phase 3: Production
├── terraform apply -var-file=envs/prod.tfvars
├── Merge staging → main
└── Verify: production deploy succeeds

Phase 4: Cleanup (optional)
├── Delete lambda/* from frontend buckets
└── Close issue #896
```

---

## Rollback Plan

If deploy fails after Terraform changes but before workflow changes:
- The `--exclude lambda/*` bandaid is still in place
- Safe to iterate on workflow changes

If deploy fails after workflow changes:
- Revert workflow to use `s3_frontend_bucket`
- Add `--exclude lambda/*` back temporarily
- Investigate and fix

---

## Success Criteria

1. Lambda deploys succeed using `bluemoxon-artifacts-{env}` bucket
2. Frontend deploys can run `--delete` without affecting Lambda
3. No `--exclude lambda/*` workaround needed
4. Parallel deploys work reliably

---

## Parallel Implementation Strategy

For maximum speed, tasks can be parallelized:

**Agent 1: Terraform**
- Tasks 1-4
- Apply to staging
- Verify bucket created

**Agent 2: Workflow (after Agent 1 completes staging)**
- Tasks 5-8
- Push to staging
- Monitor deploy

**Agent 3: Production (after staging verified)**
- Apply Terraform to prod
- Create staging→main PR

---

## Related

- Original issue: #896
- Previous fixes: #899, session in #908
- Session log: `docs/session-2026-01-06-deploy-path-filtering.md`
