# Session: Cleanup Lambda Implementation (Issues #189, #190, #191)

**Date**: 2025-12-29 (Updated 2025-12-30)
**Issues**: #189, #190, #191
**Branch**: `feat/cleanup-lambda`
**PR**: <https://github.com/markthebest12/bluemoxon/pull/682>

---

## CRITICAL RULES FOR CONTINUATION

### 1. ALWAYS Use Superpowers Skills

**Invoke relevant skills BEFORE any response or action.** Even 1% chance = invoke.

Required skills:

- `superpowers:using-superpowers` - **INVOKE FIRST** at session start
- `superpowers:systematic-debugging` - For any bugs/failures
- `superpowers:test-driven-development` - For ALL implementation
- `superpowers:verification-before-completion` - Before claiming done

**IF A SKILL APPLIES, YOU MUST USE IT. This is not optional.**

### 2. Bash Command Rules (NEVER VIOLATE)

**NEVER use (trigger permission prompts):**

```bash
# This is a comment - NEVER
command \
  --option  # NEVER - backslash continuation
result=$(command)  # NEVER - command substitution
cmd1 && cmd2  # NEVER - chaining
cmd1 || cmd2  # NEVER - chaining
echo 'Test1234!'  # NEVER - ! in quotes
```

**ALWAYS use:**

```bash
command --option value
```

Make SEPARATE Bash tool calls for each command - NOT chained with &&

For API calls use bmx-api (no permission prompts):

```bash
bmx-api GET /books
bmx-api --prod GET /books
```

### 3. Workflow Rules

- PRs reviewed before staging merge
- PRs reviewed before prod merge
- TDD for all implementation
- Staging-first workflow

---

## Current Status: LAMBDA LAYERS DESIGNED

### Decision Made (2025-12-30)

**Problem:** Lambda package too large for direct upload (72MB > 66MB limit).

**Solution:** Implement Lambda Layers to split dependencies from code:

- **Dependencies Layer (~50MB):** All Python packages, shared across Lambdas
- **Function Code (<1MB):** `app/` + `lambdas/` only

**Design Documents Created:**

- `docs/plans/2025-12-30-lambda-layers-design.md` - Full architecture design
- `docs/plans/2025-12-30-lambda-layers.md` - Step-by-step implementation plan

**Key Architectural Decisions:**

1. One layer per environment (staging/prod separate)
2. Layer cached by `poetry.lock` hash - only rebuilds when dependencies change
3. Layer stored in S3 with versioned naming: `layer-{hash}.zip`
4. CI/CD publishes new layer versions automatically

### What Happened This Session

| Task | Status |
|------|--------|
| Terraform init with staging backend | **DONE** |
| Terraform apply attempted | **PARTIAL** - IAM roles created, Lambda FAILED |
| DB password incident | **FIXED** - DUMMY_VALUE broke DB, reset via AWS CLI |
| Lambda zip size issue | **BLOCKED** - 70MB > 66MB limit for direct upload |
| Deploy workflow bug found | **FOUND** - doesn't copy `lambdas/` directory |

### The Problem Chain

1. **First attempt**: `terraform apply` with `db_password=DUMMY_VALUE`
   - Created IAM roles, log groups successfully
   - **BROKE STAGING DB** - terraform changed RDS password to DUMMY_VALUE
   - Fixed by resetting password via `aws rds modify-db-instance`

2. **Second attempt**: Used correct password from Secrets Manager
   - Lambda creation failed: `RequestEntityTooLargeException`
   - ZIP file was 72MB, limit is ~66MB for direct upload

3. **Root cause investigation**:
   - Deploy workflow only copies `app/` directory, not `lambdas/`
   - This is a **BUG** - cleanup handler at `lambdas/cleanup/handler.py` was never in Lambda package
   - Adding `lambdas/` to the existing 50MB package pushes it over the limit

### Infrastructure State

| Resource | Status |
|----------|--------|
| `aws_cloudwatch_log_group` `/aws/lambda/bluemoxon-staging-cleanup` | **CREATED** |
| `aws_iam_role` `bluemoxon-staging-cleanup-role` | **CREATED** |
| `aws_iam_role_policy` (s3, secrets) | **CREATED** |
| `aws_iam_role_policy_attachment` (basic, vpc, xray) | **CREATED** |
| `aws_lambda_function` `bluemoxon-staging-cleanup` | **NOT CREATED** - zip too large |

---

## NEXT STEPS (In Order)

### 1. Create Lambda Using S3-Based Deployment

The Lambda package is too large for direct upload. Must use S3:

**Option A: AWS CLI (Quick fix)**

```bash
# Download existing API Lambda package
AWS_PROFILE=bmx-staging aws lambda get-function --function-name bluemoxon-staging-api --query 'Code.Location' --output text > .tmp/lambda-url.txt
```

```bash
curl -s -o .tmp/base-lambda.zip "$(cat .tmp/lambda-url.txt)"
```

```bash
# Add lambdas directory (excluding .tmp)
cd /Users/mark/projects/bluemoxon/backend
zip -r .tmp/base-lambda.zip lambdas/__init__.py lambdas/cleanup/ -x "*.pyc" -x "*__pycache__*"
```

```bash
# Upload to S3
AWS_PROFILE=bmx-staging aws s3 cp .tmp/base-lambda.zip s3://bluemoxon-frontend-staging/lambda/cleanup.zip
```

```bash
# Create Lambda from S3
AWS_PROFILE=bmx-staging aws lambda create-function --function-name bluemoxon-staging-cleanup --runtime python3.12 --role arn:aws:iam::652617421195:role/bluemoxon-staging-cleanup-role --handler lambdas.cleanup.handler.handler --code S3Bucket=bluemoxon-frontend-staging,S3Key=lambda/cleanup.zip --timeout 300 --memory-size 256 --environment "Variables={DATABASE_SECRET_ARN=arn:aws:secretsmanager:us-west-2:652617421195:secret:bluemoxon-staging/database-ayNNLZ,ENVIRONMENT=staging,IMAGES_BUCKET=bluemoxon-images-staging}" --vpc-config SubnetIds=subnet-09eeb023cb49a83d5,subnet-0bfb299044084bad3,subnet-0ceb0276fa36428f2,SecurityGroupIds=sg-050fb5268bcd06443
```

**Option B: Fix Terraform module (Proper fix)**

- Modify `modules/cleanup-lambda/main.tf` to support S3 source
- Add `s3_bucket` and `s3_key` variables
- Update deploy workflow to upload Lambda package to S3

### 2. Fix Deploy Workflow Bug

The deploy workflow at `.github/workflows/deploy.yml` line 412 only copies `app/`:

```bash
cp -r /app/app /output/
```

**Must add:**

```bash
cp -r /app/lambdas /output/
```

### 3. Verify Cleanup Lambda Works

```bash
bmx-api POST /admin/cleanup '{"action":"all"}'
```

### 4. Promote to Production

After staging verified:

```bash
gh pr create --base main --head staging --title "chore: Promote staging to production - Cleanup Lambda"
```

---

## Key Files Summary

| File | Status |
|------|--------|
| `backend/lambdas/cleanup/handler.py` | **DONE** - P0-P5 fixes applied |
| `backend/tests/test_cleanup.py` | **DONE** - sync tests, 28 passing |
| `backend/app/api/v1/admin.py` | **DONE** - cleanup endpoint |
| `frontend/src/views/AdminConfigView.vue` | **DONE** - Maintenance tab |
| `infra/terraform/modules/cleanup-lambda/` | **DONE** - module exists |
| `.github/workflows/deploy.yml` | **BUG** - missing lambdas/ copy |
| **AWS Lambda** | **NOT CREATED** - needs S3-based deployment |

---

## Current Todo List

```
1. [completed] Fix P0-P5 in handler.py
2. [completed] Update handler tests to sync pattern
3. [completed] PR #682 merged to staging
4. [completed] CI passing, deploy ran
5. [completed] FIX URGENT: Reset staging DB password after DUMMY_VALUE broke it
6. [in_progress] Create Lambda via S3-based deployment (zip too large for direct)
7. [pending] Fix deploy workflow to include lambdas/ directory
8. [pending] Test cleanup endpoint in staging
9. [pending] Promote staging to production
```

---

## Lessons Learned

1. **NEVER use `db_password=DUMMY_VALUE`** - Terraform will apply it to RDS even with -target
2. **Get real password from Secrets Manager first**:

   ```bash
   AWS_PROFILE=bmx-staging aws secretsmanager get-secret-value --secret-id bluemoxon-staging/database --query 'SecretString' --output text
   ```

3. **Lambda direct upload limit is ~66MB** - Use S3 for larger packages
4. **Deploy workflow bug** - Must copy ALL code directories, not just `app/`
