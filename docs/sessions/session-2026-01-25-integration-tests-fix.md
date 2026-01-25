# Session: Integration Tests Fix (2026-01-25)

## Current Status

**S3 Cleanup Tests:** 3/3 PASSING
**Garbage Detection Tests:** 0/3 - Waiting for Terraform to apply Bedrock IAM permissions

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

### Issue - Bedrock Access Denied (IN PROGRESS)
**Root Cause:** GitHub Actions OIDC role lacks `bedrock:InvokeModel` permission
```
AccessDeniedException: User github-actions-deploy/GitHubActions is not authorized
to perform: bedrock:InvokeModel on resource: inference-profile/...
```

**Fix:** Added Bedrock permission to GitHub OIDC module
- New variable `enable_bedrock_integration_tests` in github-oidc module
- New variable `enable_github_oidc_bedrock_tests` in root module
- Enabled in staging.tfvars

**PRs:**
- #1309 → staging (MERGED)
- #1310 → main (CI RUNNING - needs merge then Terraform apply)

**Status:** IN PROGRESS - Terraform must be applied after PR #1310 merges

## Next Steps

1. Merge PR #1310 to main: `gh pr merge 1310 --repo markthebest12/bluemoxon --merge --admin`
2. Apply Terraform to staging:
   ```bash
   cd infra/terraform
   AWS_PROFILE=bmx-staging terraform apply -var-file=envs/staging.tfvars
   ```
3. Trigger integration tests: `gh workflow run integration-tests.yml --repo markthebest12/bluemoxon`
4. Verify all 6 tests pass (3 S3 cleanup + 3 garbage detection)
5. Close GitHub issue #1299 when all tests pass

## S3 Test Data Location
- **Bucket:** `bluemoxon-images-staging`
- **Path:** `books/test-garbage-397448193086/`
- **Files:** `image_00.webp` through `image_18.webp`, `image_19.jpg` through `image_23.jpg`
- **Protection:** `test-garbage-` prefix makes it unparseable by cleanup Lambda (manually triggered only)

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

### GitHub OIDC Bedrock Permission
Added to `infra/terraform/modules/github-oidc/main.tf`:
```hcl
var.enable_bedrock_integration_tests ? [
  {
    Sid    = "BedrockIntegrationTests"
    Effect = "Allow"
    Action = ["bedrock:InvokeModel"]
    Resource = ["arn:aws:bedrock:${region}:${account_id}:inference-profile/*"]
  }
] : []
```

### Environment Variables
- `BMX_IMAGES_BUCKET` - S3 bucket for images (set in workflow)
- `RUN_INTEGRATION_TESTS=1` - Required to run integration tests
- `AWS_STAGING_ROLE_ARN` - GitHub secret for OIDC auth
