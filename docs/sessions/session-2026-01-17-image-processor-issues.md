# Session: Image Processor Issues - 2026-01-17

## Status: COMPLETE - PRODUCTION DEPLOYMENT SUCCESSFUL

The image processor Lambda is now fully deployed and operational in production.

### Production Verification
- **Lambda:** `bluemoxon-prod-image-processor` - Active, 7168MB memory, 300s timeout
- **Last Updated:** 2026-01-17T23:27:44Z
- **SQS Queue:** `bluemoxon-prod-image-processing` - Connected and ready
- **GitHub Actions:** Run #21101453048 completed successfully

## Critical Rules for Future Sessions

### 1. ALWAYS Use Superpowers Skills

**Invoke relevant skills BEFORE any response or action.** Even 1% chance = invoke the skill.

Key skills for this work:
- `superpowers:systematic-debugging` - For any bug investigation
- `superpowers:verification-before-completion` - Before claiming anything works
- `superpowers:test-driven-development` - Before implementing fixes

### 2. Bash Command Rules

**NEVER use these** (trigger permission prompts):
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

## Deployment History

### Issue: Production Lambda Did Not Exist

**What Happened:**
1. PR #1155 (staging to main) was merged successfully
2. GitHub Actions deploy workflow ran
3. "Build Image Processor" step succeeded (ECR push now works after terraform fix)
4. "Deploy Image Processor Lambda" step FAILED - Lambda didn't exist

**Root Cause:**
The image processor Lambda function was never created in production via terraform. GitHub Actions tries to UPDATE Lambda code, but the Lambda didn't exist yet.

**Resolution:**
1. Applied terraform for `module.github_oidc` - Added ECR push permissions
2. Tagged ECR image as `v2` for terraform bootstrap
3. Applied terraform for `module.image_processor` - Created Lambda
4. Re-ran GitHub Actions workflow #21101453048 - Deployed latest code

## Background

The image processor Lambda (`backend/lambdas/image_processor/handler.py`) was deployed to staging. It uses rembg/u2net to remove backgrounds from book images and replace with white/black backgrounds based on subject brightness.

### What Works
- Lambda deploys and runs successfully in STAGING
- SQS queue triggers Lambda correctly
- Background removal with rembg/u2net works
- Processed images upload to S3
- Database records created for processed images

### Issues Found and Fixed

#### Issue 1: Missing Thumbnails (CRITICAL) - FIXED
- Added `generate_thumbnail()` function and thumbnail upload after processed image upload

#### Issue 2: Wrong Source Image Selection - FIXED
- Added `select_best_source_image()` with type priority: title_page > binding > cover > spine

#### Code Review Fixes - FIXED
- P0: Row-level locking, idempotency check
- P1: Null check, credential rotation handling, memory optimization
- P2: S3 key normalization, filter fix, pathlib usage

## Files Modified This Session

- `infra/terraform/modules/github-oidc/main.tf` - Added `lambda:TagResource` permission
- `infra/terraform/main.tf` - Added image-processor ECR to github_oidc module
- `infra/terraform/envs/prod.tfvars` - Added image processor comment
- `backend/lambdas/image_processor/handler.py` - Added thumbnail generation and smart source selection
- `backend/lambdas/image_processor/tests/test_handler.py` - Added 9 new tests

## PRs Created

- PR #1151 - Code review fixes (MERGED to staging)
- PR #1152 - TagResource permission fix (MERGED to staging)
- PR #1153 - Staging to main promotion (CLOSED - had merge conflicts)
- PR #1154 - Thumbnail generation + smart source selection fixes (MERGED to staging)
- PR #1155 - Staging to production promotion (MERGED to main)

## Validation Results

### Staging Validation (Book 636) - PASSED
- Source selection: `Selected source image 5528 (type=title_page)`
- Thumbnail generation: `Uploading thumbnail to s3://...thumb_636_processed_...jpg`
- Thumbnail in S3: 6084 bytes
- Thumbnail via CDN: HTTP 200

## Commands for Testing

```bash
# Check processed images for a book
bmx-api GET /books/635/images

# Check SQS queue status (use separate commands, no chaining)
AWS_PROFILE=bmx-staging aws sqs get-queue-attributes --queue-url https://sqs.us-west-2.amazonaws.com/652617421195/bluemoxon-staging-image-processing --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible

# Check Lambda logs
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-image-processor --since 5m
```

## Key Code Locations

- **Image processor Lambda:** `backend/lambdas/image_processor/handler.py`
- **Thumbnail generation reference:** `backend/app/api/v1/images.py:87`
- **Image upload with processing trigger:** `backend/app/api/v1/images.py:482-487`
- **Queue image processing:** `backend/app/services/image_processing.py`
