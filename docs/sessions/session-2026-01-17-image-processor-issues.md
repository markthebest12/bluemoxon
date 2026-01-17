# Session: Image Processor Issues - 2026-01-17

## Status: FIXES IMPLEMENTED - PENDING PR REVIEW

## Critical Rules for Continuation

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

## Background

The image processor Lambda (`backend/lambdas/image_processor/handler.py`) was deployed to staging. It uses rembg/u2net to remove backgrounds from book images and replace with white/black backgrounds based on subject brightness.

### What Works
- Lambda deploys and runs successfully
- SQS queue triggers Lambda correctly
- Background removal with rembg/u2net works
- Processed images upload to S3
- Database records created for processed images

### Issues Found

#### Issue 1: Missing Thumbnails (CRITICAL) - ✅ FIXED

**Symptom:** Processed images appear "broken" on the website because thumbnails don't exist.

**Root Cause:** The image processor Lambda uploads the processed PNG to S3 but does NOT generate a thumbnail.

**Fix Implemented:**
- Added `THUMBNAIL_MAX_SIZE = (300, 300)` and `THUMBNAIL_QUALITY = 85` constants
- Added `generate_thumbnail()` function matching API endpoint behavior
- Added thumbnail upload after processed image upload (JPEG format)
- Added 3 unit tests for thumbnail generation

**Commits:** `90f6491` - feat: Add thumbnail generation to image processor Lambda

#### Issue 2: Wrong Source Image Selection - ✅ FIXED

**Symptom:** Processor sometimes processes title pages instead of book cover/binding.

**Expected Behavior:** Should prioritize:
1. Title page image (if exists)
2. Binding/spine image (if no title page)

**Fix Implemented:**
- Added `IMAGE_TYPE_PRIORITY = ["title_page", "binding", "cover", "spine"]` constant
- Added `select_best_source_image()` function with priority-based selection
- Integrated into `process_image()` to select best source from all book images
- Added 6 unit tests for source selection
- Falls back to primary image, then passed image_id, then first unprocessed

**Commits:** `a6cd2c8` - feat: Add smart source image selection for image processor

#### Code Review Fixes - ✅ FIXED

**P0 Critical:**
- Added row-level locking (`SELECT FOR UPDATE`) to prevent race conditions on concurrent book processing
- Added idempotency check for job status before processing (SQS at-least-once delivery)

**P1 High:**
- Added null check for `select_best_source_image()` return value
- Reset DB engine when secret cache expires (handles RDS credential rotation)
- Optimized brightness calculation to use streaming iteration (O(1) memory instead of O(16M))

**P2 Medium:**
- Extracted `normalize_s3_key()` helper for consistent S3 prefix handling
- Fixed filter to exclude source_image instead of trigger image in renumbering
- Used pathlib for thumbnail filename manipulation

**Commits:** `0a62303` - fix: Address code review issues for image processor

## Files Modified This Session

- `infra/terraform/modules/github-oidc/main.tf` - Added `lambda:TagResource` permission
- `infra/terraform/main.tf` - Added image-processor ECR to github_oidc module
- `backend/lambdas/image_processor/handler.py` - Added thumbnail generation and smart source selection
- `backend/lambdas/image_processor/tests/test_handler.py` - Added 9 new tests (3 thumbnail, 6 source selection)

## PRs Created

- PR #1151 - Code review fixes (MERGED to staging)
- PR #1152 - TagResource permission fix (MERGED to staging)
- PR #1153 - Staging to main promotion (OPEN, needs review)
- PR #1154 - Thumbnail generation + smart source selection fixes (OPEN, needs review)

## Test Books

- **Book 635** (Ruskin - Unto This Last): Processed successfully, missing thumbnail
- **Book 626** (Charles O'Malley): Processed title page instead of cover, missing thumbnail

## Next Steps

1. ✅ ~~**Fix thumbnail generation** in image processor Lambda~~
   - DONE - Added `generate_thumbnail()` function and upload code

2. ✅ ~~**Investigate source image selection**~~
   - DONE - Added `select_best_source_image()` with type priority

3. ✅ ~~**Create PR for staging** with both fixes~~
   - DONE - PR #1154 created, pending user review before merge

4. **Apply terraform to production** before merging PR #1153
   - `lambda:TagResource` permission needed
   - ECR permissions for image-processor

5. **Merge PR #1153** to deploy to production

6. **Test in staging** after fixes are deployed
   - Reprocess book 635 and 626
   - Verify thumbnails appear
   - Verify correct source images are selected

## Commands for Testing

```bash
# Check processed images for a book
bmx-api GET /books/635/images

# Check SQS queue status
AWS_PROFILE=bmx-staging aws sqs get-queue-attributes --queue-url https://sqs.us-west-2.amazonaws.com/652617421195/bluemoxon-staging-image-processing --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible

# Check Lambda logs
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-image-processor --since 5m

# Upload primary image to trigger processing
curl -X POST "https://staging.api.bluemoxon.com/api/v1/books/BOOK_ID/images?is_primary=true" -H "X-API-Key: $(cat ~/.bmx/staging.key)" -F "file=@/path/to/image.jpg"
```

## Key Code Locations

- **Image processor Lambda:** `backend/lambdas/image_processor/handler.py`
- **Thumbnail generation reference:** `backend/app/api/v1/images.py:87` (`generate_thumbnail()`)
- **Image upload with processing trigger:** `backend/app/api/v1/images.py:482-487`
- **Queue image processing:** `backend/app/services/image_processing.py`
