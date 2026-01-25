# Session: Integration Tests Fix (2026-01-25)

## Current Status

| Test | Status | Notes |
|------|--------|-------|
| S3 Cleanup Tests | 3/3 PASS | All fixed |
| test_garbage_detection_with_title_only | 1/1 PASS | Bedrock permission fixed |
| test_garbage_detection_identifies_known_garbage | 0/1 FAIL | AI flagged 20/24 images |
| test_images_deleted_after_detection | 0/1 FAIL | s3:DeleteObject denied + AI over-flagging |

**Summary:** 4/6 tests passing. Bedrock InvokeModel permission is now working. Two remaining issues need fixing.

## Issues Addressed

### Issue #1295 - OIDC Authentication Failure (FIXED)
**Root Cause:** Hardcoded wrong AWS account ID in `.github/workflows/integration-tests.yml`
**Fix:** Changed to use `secrets.AWS_STAGING_ROLE_ARN`
**Status:** FIXED - Merged via PR #1297 → staging, PR #1298 → main

### Issue #1299 - S3 Bucket Not Found (FIXED)
**Root Cause:** Wrong S3 bucket naming pattern in tests
- Tests expected: `bluemoxon-staging-images`
- Actual bucket: `bluemoxon-images-staging`
- Pattern is `{app}-images-{env}`, not `{app}-{env}-images`

**Fix:** PR #1300 corrected bucket name, PR #1301 promoted to main
**Status:** FIXED

### Issue - S3 Key Path Mismatch (FIXED)
**Root Cause:** `bedrock.py` prepends `books/` to all `BookImage.s3_key` values
- Test created keys: `listings/397448193086/image_00.webp`
- bedrock.py looked for: `books/listings/397448193086/image_00.webp`
- Actual files were at: `listings/397448193086/image_00.webp`

**Fix:**
1. Copied test images to `books/test-garbage-397448193086/` in S3
2. Updated test to use s3_keys relative to `books/` prefix
3. The `test-garbage-` prefix ensures cleanup Lambda won't delete test data

**PRs:** #1303, #1305, #1306 (all merged to main)
**Status:** FIXED

### Issue - S3 Validation Flagging Test Data (FIXED)
**Root Cause:** `test_all_book_keys_parseable_by_cleanup_lambda` was flagging our intentionally unparseable test data at `books/test-garbage-*`

**Fix:** Added exclusion for `test-*` prefix paths in S3 validation test
- Added `TEST_DATA_PREFIX = "test-"` constant
- Skip keys matching `test-*` in validation loop
- Report excluded test data count in summary

**PRs:** #1307 → staging, #1308 → main
**Status:** FIXED

### Issue - Bedrock InvokeModel Access Denied (FIXED)
**Root Cause:** GitHub Actions OIDC role lacked `bedrock:InvokeModel` permission for foundation models

**Initial Fix (PR #1309, #1310):** Added inference-profile permission
**Problem:** Code uses foundation-model, not inference-profile, and in us-east-1 not us-west-2

**Final Fix (PR #1312, #1313):** Extended permission to include:
```hcl
Resource = [
  "arn:aws:bedrock:*:${account_id}:inference-profile/*",
  "arn:aws:bedrock:*::foundation-model/*"
]
```

**Status:** FIXED - Terraform applied, Bedrock calls now succeed

### Issue - AI Over-Flagging Images (NEW - IN PROGRESS)
**Symptom:** Claude flagged 20/24 images as garbage (expected ~5)
```
AssertionError: Too many images flagged as garbage: [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 17, 18, 19, 20, 21, 22, 23]. Expected around 5.
```

**Root Cause:** Unclear - may be prompt issue, image quality issue, or Claude model variability

**Status:** NEEDS INVESTIGATION

### Issue - S3 DeleteObject Access Denied (NEW - IN PROGRESS)
**Symptom:**
```
AccessDenied: s3:DeleteObject on resource "arn:aws:s3:::bluemoxon-images-staging/books/test-garbage-397448193086/image_00.webp"
```

**Root Cause:** GitHub OIDC images bucket policy only grants GetObject, PutObject, ListBucket - not DeleteObject

**Location:** `infra/terraform/modules/github-oidc/main.tf` lines 117-132

**Current Policy:**
```hcl
Action = [
  "s3:GetObject",
  "s3:PutObject",
  "s3:ListBucket"
]
```

**Fix Needed:** Add `s3:DeleteObject` to the images bucket policy

**Status:** NEEDS FIX

## Code Review Feedback Applied

PR #1311 applied minor documentation improvements from code review:
- Added restore instructions to test docstring
- Added explicit `enable_github_oidc_bedrock_tests = false` in prod.tfvars
- Skipped other findings (YAGNI, pragmatic for AI variability)

## Next Steps

1. **Add s3:DeleteObject permission** to GitHub OIDC images bucket policy
2. **Investigate AI over-flagging** - Why is Claude flagging 20/24 images as garbage?
   - Check prompt in `eval_generation.py`
   - Review image quality
   - Consider Claude model variability
3. **Re-run integration tests** after fix
4. **Close GitHub issue #1299** when all 6 tests pass

## S3 Test Data Location
- **Bucket:** `bluemoxon-images-staging`
- **Path:** `books/test-garbage-397448193086/`
- **Files:** `image_00.webp` through `image_18.webp`, `image_19.jpg` through `image_23.jpg`
- **Protection:** `test-garbage-` prefix makes it unparseable by cleanup Lambda

To restore if deleted:
```bash
AWS_PROFILE=bmx-staging aws s3 cp s3://bluemoxon-images-staging/listings/397448193086/ s3://bluemoxon-images-staging/books/test-garbage-397448193086/ --recursive
```

## CRITICAL WORKFLOW REMINDERS

### Superpowers Skills - ALWAYS USE
- `superpowers:brainstorming` - Before any creative/feature work
- `superpowers:test-driven-development` - Before writing code
- `superpowers:systematic-debugging` - Before fixing bugs
- `superpowers:receiving-code-review` - When getting feedback
- `superpowers:using-git-worktrees` - For isolated workspaces
- `superpowers:verification-before-completion` - Before claiming done
- `superpowers:using-superpowers` - Check skills BEFORE any action
- `mcp__sequential-thinking__sequentialthinking` - For complex multi-step analysis

**IF A SKILL APPLIES, YOU MUST USE IT. NO EXCEPTIONS.**

### Bash Commands - FORBIDDEN PATTERNS
**NEVER use these (they trigger permission prompts):**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

### Git Workflow
1. Create branch from staging: `git checkout -b type/description`
2. Make changes, validate with ruff/prettier
3. Commit with descriptive message
4. PR to staging with squash merge
5. Validate in staging
6. Promote staging → main with merge commit (NOT squash)
7. Watch deploy: `gh run watch <id> --exit-status`

## Key Technical Details

### bedrock.py S3 Key Handling (line 315)
```python
s3_key = f"books/{img.s3_key}"  # Prepends "books/" to all keys
```
BookImage.s3_key must be RELATIVE to `books/` prefix.

### Cleanup Lambda
- **Trigger:** Manual only via admin UI (no scheduled execution)
- **Parsing:** Only parses numeric book IDs from path
- **Test Data Safety:** Keys with non-numeric prefixes like `test-garbage-` are silently skipped

### GitHub OIDC Bedrock Permission (UPDATED)
`infra/terraform/modules/github-oidc/main.tf`:
```hcl
var.enable_bedrock_integration_tests ? [
  {
    Sid    = "BedrockIntegrationTests"
    Effect = "Allow"
    Action = ["bedrock:InvokeModel"]
    Resource = [
      "arn:aws:bedrock:*:${account_id}:inference-profile/*",
      "arn:aws:bedrock:*::foundation-model/*"
    ]
  }
] : []
```

### GitHub OIDC Images Bucket Permission (NEEDS UPDATE)
`infra/terraform/modules/github-oidc/main.tf` lines 117-132:
```hcl
# S3 Images access permissions
length(var.images_bucket_arns) > 0 ? [
  {
    Sid    = "S3ImagesAccess"
    Effect = "Allow"
    Action = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
      # TODO: Add "s3:DeleteObject" for integration tests
    ]
    Resource = concat(
      var.images_bucket_arns,
      [for arn in var.images_bucket_arns : "${arn}/*"]
    )
  }
] : [],
```

### Environment Variables
- `BMX_IMAGES_BUCKET` - S3 bucket for images (set in workflow)
- `RUN_INTEGRATION_TESTS=1` - Required to run integration tests
- `AWS_STAGING_ROLE_ARN` - GitHub secret for OIDC auth

## PRs This Session
- PR #1311 - Review feedback (merged)
- PR #1312 → staging (merged) - Bedrock foundation-model permission
- PR #1313 → main (merged) - Promote staging
