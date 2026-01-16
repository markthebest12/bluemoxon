# Session: Napoleon Garbage Detection Production Deploy

**Date:** 2026-01-02
**Issue:** #748 (Garbage detection), PR #749, #750, #751
**Branch:** staging (merging to main)

## Background

Deploying Napoleon Analysis Improvements to production:

1. **Garbage detection** - Automatically identifies and removes non-book images (seller logos, shipping labels, eBay watermarks) before eval runbook generation
2. **P0 bug fix** - Validates image indices against `len(image_blocks)` (what Claude sees) not `len(images)` (original count)
3. **IAM fix** - Added `s3:DeleteObject` permission to eval-runbook-worker

## What Was Done

### Staging Validation ✓

- PR #749 merged to staging (garbage detection feature)
- Tested on book 537: Detected 2 garbage images, P0 fix filtered invalid index 20
- Discovered IAM permission issue - eval worker couldn't delete S3 objects

### IAM Fix ✓

- Added `s3:DeleteObject` to `infra/terraform/modules/eval-runbook-worker/main.tf`
- Applied to staging via Terraform
- PR #750 merged to staging
- Re-tested on book 536: 6 garbage images successfully removed from DB and S3

### Production Deploy (IN PROGRESS)

- Created PR #751 (staging → main)
- CI passed
- **MERGE CONFLICT during merge** - resolving now

## Current State

Resolving merge conflicts in PR #751:

1. `backend/app/worker.py` - ✓ Resolved (keep BookImage import)
2. `backend/tests/test_books.py` - ✓ Resolved (keep staging tests)
3. `frontend/src/components/AnalysisIssuesWarning.vue` - ✓ Resolved (keep BaseTooltip version)

**Next step:** Commit merge resolution, push, and complete merge to main.

## Next Steps

1. Verify no conflict markers remain:

   ```bash
   grep -r "<<<<<<" backend/ frontend/
   ```

2. Stage and commit the merge:

   ```bash
   git add -A
   git commit -m "Merge origin/main into staging - resolve conflicts"
   ```

3. Push to staging:

   ```bash
   git push origin staging
   ```

4. Merge PR #751 to main:

   ```bash
   gh pr merge 751 --squash --delete-branch --admin
   ```

5. Watch deploy workflow:

   ```bash
   gh run list --workflow Deploy --limit 1
   gh run watch <run-id> --exit-status
   ```

6. Apply Terraform IAM change to production:

   ```bash
   cd /Users/mark/projects/bluemoxon/infra/terraform
   AWS_PROFILE=bmx-prod terraform init -backend-config=backends/prod.hcl -reconfigure
   AWS_PROFILE=bmx-prod terraform plan -var-file=envs/prod.tfvars -var="db_password=dummy" -target=module.eval_runbook_worker.aws_iam_role_policy.s3_access
   AWS_PROFILE=bmx-prod terraform apply -var-file=envs/prod.tfvars -var="db_password=dummy" -target=module.eval_runbook_worker.aws_iam_role_policy.s3_access -auto-approve
   ```

7. Verify production health:

   ```bash
   curl -s https://api.bluemoxon.com/api/v1/health/deep | jq
   ```

## CRITICAL REMINDERS

### 1. ALWAYS Use Superpowers Skills

**MANDATORY at all stages:**

- `superpowers:brainstorming` - Before any creative/feature work
- `superpowers:systematic-debugging` - Before proposing ANY fix
- `superpowers:test-driven-development` - Before implementation
- `superpowers:verification-before-completion` - Before claiming done
- `superpowers:finishing-a-development-branch` - After completing work

If there's even a 1% chance a skill applies, INVOKE IT.

### 2. NEVER Use These (Trigger Permission Prompts)

```bash
# BAD - ALL OF THESE TRIGGER PERMISSION PROMPTS:
# This is a comment before command
curl https://example.com

command1 && command2        # Chaining with &&
command1 || command2        # Chaining with ||

aws s3 ls \
  --recursive               # Backslash continuations

echo $(date +%s)           # Command substitution $(...)
echo $((1+1))              # Arithmetic substitution

--password 'Test1234!'     # ! in quoted strings gets expanded
```

### 3. ALWAYS Use These Patterns

```bash
# GOOD - Simple single-line commands:
curl -s https://api.bluemoxon.com/api/v1/health/deep | jq

# GOOD - Separate Bash tool calls instead of &&:
# First call:
git add -A
# Second call (separate):
git commit -m "message"
# Third call (separate):
git push

# GOOD - Use bmx-api for all BlueMoxon API calls:
bmx-api GET /books/537
bmx-api --prod GET /books/537
bmx-api POST /books/537/eval-runbook/generate '{"model": "opus"}'

# GOOD - Use @ or # instead of ! in passwords:
--password 'Test@1234'
```

## Files Changed

### Terraform (IAM fix)

- `infra/terraform/modules/eval-runbook-worker/main.tf` - Added s3:DeleteObject

### Merge Conflict Resolutions

- `backend/app/worker.py` - Keep BookImage import for garbage detection
- `backend/tests/test_books.py` - Keep TestGenerateAnalysisDefaults and TestStaleJobAutoCleanup
- `frontend/src/components/AnalysisIssuesWarning.vue` - Keep BaseTooltip version

## Related Issues/PRs

- Issue #748 - Garbage detection feature
- PR #749 - Garbage detection merged to staging
- PR #750 - IAM fix merged to staging
- PR #751 - Staging → main (IN PROGRESS - resolving conflicts)
