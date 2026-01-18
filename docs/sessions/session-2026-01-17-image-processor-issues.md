# Session: Image Processor Issues - 2026-01-17

## Status: BUG FIX READY FOR DEPLOYMENT

PR #1156 created - removes validation thresholds that were rejecting valid images.

---

## CRITICAL RULES FOR ALL SESSIONS

### 1. ALWAYS Use Superpowers Skills

**Invoke relevant skills BEFORE any response or action.** Even 1% chance = invoke the skill.

Key skills for this work:
- `superpowers:systematic-debugging` - For ANY bug investigation
- `superpowers:verification-before-completion` - Before claiming ANYTHING works
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

---

## Next Steps

1. **Merge PR #1156** to staging
2. **Watch CI**: `gh pr checks 1156 --watch`
3. **After staging deploy, test book 635**:
   - Trigger reprocess: `bmx-api PUT /books/635/images/reorder '[5720, 5721, ...]'`
   - Check Lambda logs: `AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-image-processor --since 5m`
   - Verify processed image created
4. **Promote to production** when staging verified
5. **Reprocess any affected books** in production

---

## Bug Found: Validation Thresholds Rejecting Valid Images

**Symptom:** Book 635 (created via eBay import) had no processed image despite Lambda running successfully.

**Investigation Path (Systematic Debugging):**
1. API logs showed: `Image processing job sent, MessageId: 8289b821-...` ✓
2. Lambda logs showed: `Processing job 88ce0edf-... for book 635, image 5720` ✓
3. Lambda logs showed: `Attempt 1 failed validation: area_too_small`
4. Lambda logs showed: `Attempt 2 failed validation: area_too_small`
5. Lambda logs showed: `Attempt 3 failed validation: aspect_ratio_mismatch`
6. Lambda logs showed: `Job 88ce0edf-...: all attempts failed, keeping original as primary`

**Root Cause:** Lambda had validation thresholds that didn't exist in the original working script:
- `MIN_AREA_RATIO = 0.5` - Rejected if subject area <50% of original
- `MAX_ASPECT_DIFF = 0.2` - Rejected if aspect ratio changed >20%

**Original Script Behavior:** `scripts/process-book-images.sh` (lines 118-149) had NO validation:
```bash
docker run ... danielgatis/rembg i -a "$ORIG_FILE" "$NOBG_FILE"
BRIGHTNESS=$(magick "$NOBG_FILE" -colorspace Gray -format "%[fx:mean*255]" info:)
magick "$NOBG_FILE" -background "$BG_COLOR" -flatten "$FINAL_FILE"
```
This processed 100+ books flawlessly - no area ratio check, no aspect ratio check.

**Fix Applied:** Removed `validate_image_quality()` function and all validation calls from `handler.py`. Lambda now uses whatever rembg returns without quality gates.

### Files Changed in Fix
- `backend/lambdas/image_processor/handler.py` - Removed validation function and thresholds
- `backend/lambdas/image_processor/tests/test_handler.py` - Removed 3 validation tests

### PR Created
- **PR #1156** - `fix: Remove validation thresholds from image processor`

---

## Previous Status: PRODUCTION DEPLOYMENT SUCCESSFUL

The image processor Lambda was deployed and operational in production.

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

### Production Validation (Book 634) - PASSED
Full end-to-end test via acquisition flow on 2026-01-18:
- Created test book via `bmx-api --prod POST /books`
- Uploaded binding image (5716) and title_page image (5717)
- Triggered processing via image reorder
- Lambda logs confirmed:
  - `Selected source image 5717 (type=title_page, requested=5716)` - Smart selection ✓
  - `Attempt 1 succeeded with model u2net-alpha` - Background removal ✓
  - `Subject brightness: 183, selected background: white` - Brightness detection ✓
  - `Uploading thumbnail to s3://...thumb_634_processed_...jpg` - Thumbnail ✓
  - `Job completed successfully, new image id: 5718` - Success ✓
- Processed image accessible via CDN: HTTP 200, 1.6MB PNG
- Thumbnail accessible via CDN: HTTP 200, 8.8KB JPEG
- Test book cleaned up after validation

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
