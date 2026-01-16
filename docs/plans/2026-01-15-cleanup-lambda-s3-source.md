# Cleanup Lambda S3 Source Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modify cleanup-lambda Terraform module to use S3 source instead of local file paths, preventing issues when running Terraform locally.

**Architecture:** Replace `filename`/`source_code_hash` with `s3_bucket`/`s3_key` pattern (matching lambda-layer module). CI/CD already uploads Lambda packages to S3, so no workflow changes needed.

**Tech Stack:** Terraform (AWS Lambda, S3)

**Issue:** #1127

---

## Task 1: Update cleanup-lambda Module Variables

**Files:**

- Modify: `infra/terraform/modules/cleanup-lambda/variables.tf:39-48`

**Step 1: Replace package_path and source_code_hash variables with S3 variables**

Remove these existing variables (lines 39-48):

```hcl
variable "package_path" {
  description = "Path to the Lambda deployment package"
  type        = string
}

variable "source_code_hash" {
  description = "Source code hash for the Lambda package"
  type        = string
  default     = null
}
```

Add these new variables in their place:

```hcl
variable "s3_bucket" {
  description = "S3 bucket containing the Lambda deployment package"
  type        = string
}

variable "s3_key" {
  description = "S3 key (path) to the Lambda deployment package"
  type        = string
}
```

**Step 2: Validate Terraform syntax**

Run: `terraform -chdir=infra/terraform validate`
Expected: Error about missing s3_bucket/s3_key values in root module (expected until Task 3)

**Step 3: Commit variables change**

```bash
git add infra/terraform/modules/cleanup-lambda/variables.tf
git commit -m "refactor(cleanup-lambda): replace package_path with S3 source variables

Part of #1127"
```

---

## Task 2: Update cleanup-lambda Module to Use S3 Source

**Files:**

- Modify: `infra/terraform/modules/cleanup-lambda/main.tf:121-122`

**Step 1: Change Lambda function to use S3 source**

Find the `aws_lambda_function` resource (around line 113-158) and replace the `filename`/`source_code_hash` lines:

Current (lines 121-122):

```hcl
  filename         = var.package_path
  source_code_hash = var.source_code_hash
```

Replace with:

```hcl
  s3_bucket = var.s3_bucket
  s3_key    = var.s3_key
```

**Step 2: Update lifecycle ignore_changes block**

Find the lifecycle block (around line 151-157) and update it:

Current:

```hcl
  lifecycle {
    ignore_changes = [
      filename,
      source_code_hash,
      layers,
    ]
  }
```

Replace with:

```hcl
  lifecycle {
    ignore_changes = [
      s3_bucket,
      s3_key,
      layers,
    ]
  }
```

**Step 3: Validate Terraform syntax**

Run: `terraform -chdir=infra/terraform validate`
Expected: Error about missing s3_bucket/s3_key values (expected until Task 3)

**Step 4: Commit module changes**

```bash
git add infra/terraform/modules/cleanup-lambda/main.tf
git commit -m "refactor(cleanup-lambda): use S3 source for Lambda package

Changes aws_lambda_function to use s3_bucket/s3_key instead of
filename/source_code_hash, matching the lambda-layer pattern.

Part of #1127"
```

---

## Task 3: Update Root Module to Pass S3 Config

**Files:**

- Modify: `infra/terraform/main.tf:681-682`

**Step 1: Update cleanup_lambda module call**

Find the cleanup_lambda module (around line 674) and replace the package_path/source_code_hash lines:

Current (lines 681-682):

```hcl
  package_path     = var.lambda_package_path
  source_code_hash = var.lambda_source_code_hash
```

Replace with:

```hcl
  s3_bucket = module.artifacts_bucket.bucket_id
  s3_key    = "lambda/backend.zip"
```

**Step 2: Validate Terraform configuration**

Run: `terraform -chdir=infra/terraform validate`
Expected: Success

**Step 3: Verify plan shows no destructive changes**

Run: `AWS_PROFILE=bmx-staging terraform -chdir=infra/terraform plan -var-file=infra/terraform/envs/staging.tfvars`
Expected: No changes (or minor in-place updates to lifecycle), NO destroy operations

**Step 4: Commit root module changes**

```bash
git add infra/terraform/main.tf
git commit -m "refactor: pass S3 source config to cleanup-lambda module

Completes #1127 - cleanup-lambda now uses S3 source for packages,
preventing issues when running Terraform locally without a local
lambda.zip file.

Closes #1127"
```

---

## Task 4: Create PR for Staging

**Step 1: Push branch and create PR**

```bash
git push -u origin refactor/cleanup-lambda-s3-source
```

Create PR targeting staging:

```bash
gh pr create --base staging --title "refactor: Modify cleanup-lambda to use S3 source" --body "## Summary
- Modifies cleanup-lambda module to use S3 source instead of local file paths
- Prevents issues when running Terraform locally (like incident in #1126)
- Matches pattern used by lambda-layer module

## Changes
- \`modules/cleanup-lambda/variables.tf\`: Replace \`package_path\`/\`source_code_hash\` with \`s3_bucket\`/\`s3_key\`
- \`modules/cleanup-lambda/main.tf\`: Use S3 source in aws_lambda_function
- \`main.tf\`: Pass S3 config to cleanup-lambda module

## Test Plan
- [ ] CI passes
- [ ] Terraform plan shows no destructive changes
- [ ] Deploy to staging succeeds
- [ ] Cleanup Lambda invocation works in staging

Closes #1127"
```

**Step 2: Wait for CI**

Run: `gh pr checks <pr-number> --watch`
Expected: All checks pass

---

## Task 5: Validate Staging Deployment

**Step 1: Merge PR to staging**

After reviewing and CI passes:

```bash
gh pr merge <pr-number> --squash --delete-branch
```

**Step 2: Watch deploy workflow**

```bash
gh run list --workflow Deploy --limit 1
gh run watch <run-id> --exit-status
```

Expected: Deploy succeeds, smoke tests pass

**Step 3: Test cleanup Lambda in staging**

Test the cleanup Lambda works:

```bash
bmx-api GET /admin/cleanup/status
```

Expected: Successful response showing cleanup status

---

## Task 6: Promote to Production

**Step 1: Create promotion PR**

```bash
gh pr create --base main --head staging --title "chore: Promote staging to production (cleanup-lambda S3 source)" --body "## Summary
Promotes cleanup-lambda S3 source refactor (#1127) to production.

## Changes
- cleanup-lambda module now uses S3 source for Lambda packages
- Prevents issues when running Terraform locally

## Validated
- [x] CI passed on staging PR
- [x] Deployed to staging successfully
- [x] Smoke tests passed
- [x] Cleanup Lambda works in staging"
```

**Step 2: Wait for CI and approval**

```bash
gh pr checks <pr-number> --watch
```

**Step 3: Merge to production**

After review approval:

```bash
gh pr merge <pr-number> --squash
```

**Step 4: Watch production deploy**

```bash
gh run list --workflow Deploy --limit 1
gh run watch <run-id> --exit-status
```

Expected: Deploy succeeds, smoke tests pass

---

## Verification Checklist

After production deployment:

- [ ] Cleanup Lambda invocation works in production
- [ ] Running `terraform plan` locally no longer requires lambda.zip
- [ ] No Terraform drift detected
