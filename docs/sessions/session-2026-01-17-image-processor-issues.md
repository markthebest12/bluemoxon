# Session: Image Processor Issues - 2026-01-17

## Status: IN PROGRESS

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

#### Issue 1: Missing Thumbnails (CRITICAL)

**Symptom:** Processed images appear "broken" on the website because thumbnails don't exist.

**Root Cause:** The image processor Lambda uploads the processed PNG to S3 but does NOT generate a thumbnail.

**Location:** `backend/lambdas/image_processor/handler.py` - search for "Uploading processed image"

**Fix Required:** After uploading the processed image, generate and upload a thumbnail:
1. Create thumbnail (300x300 max, JPEG quality 85)
2. Upload to S3 with `thumb_` prefix
3. Reference: See `generate_thumbnail()` in `backend/app/api/v1/images.py:87`

#### Issue 2: Wrong Source Image Selection

**Symptom:** Processor sometimes processes title pages instead of book cover/binding.

**Expected Behavior:** Should prioritize:
1. Title page image (if exists)
2. Binding/spine image (if no title page)

**Current Behavior:** Processes whatever image is marked as primary, which may be uploaded in wrong order.

**Investigation Needed:**
- Check how primary image selection works during book import
- Check if there's image_type classification logic
- May need to add logic to select best source image for processing

## Files Modified This Session

- `infra/terraform/modules/github-oidc/main.tf` - Added `lambda:TagResource` permission
- `infra/terraform/main.tf` - Added image-processor ECR to github_oidc module

## PRs Created

- PR #1151 - Code review fixes (MERGED to staging)
- PR #1152 - TagResource permission fix (MERGED to staging)
- PR #1153 - Staging to main promotion (OPEN, needs review)

## Test Books

- **Book 635** (Ruskin - Unto This Last): Processed successfully, missing thumbnail
- **Book 626** (Charles O'Malley): Processed title page instead of cover, missing thumbnail

## Next Steps

1. **Fix thumbnail generation** in image processor Lambda
   - Add thumbnail generation after processed image upload
   - Test with book 635 or 626

2. **Investigate source image selection**
   - Understand current primary image selection logic
   - Determine if image_type field is being used
   - May need to add smart source selection

3. **Apply terraform to production** before merging PR #1153
   - `lambda:TagResource` permission needed
   - ECR permissions for image-processor

4. **Merge PR #1153** to deploy to production

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
