# Session: Auto-Process Images Infrastructure

**Date:** 2026-01-16/17
**Branch:** staging
**Issue:** #1136
**PR:** #1139 (merged)

## Summary

Deployed infrastructure for automatic image processing during book eval import. Images are queued to SQS and processed by a Lambda worker that removes backgrounds and uploads to S3.

---

## Part 1: Terraform Infrastructure

### Changes Made

1. **Created image-processor module** (`modules/image-processor/`)
   - SQS queue: `bluemoxon-staging-image-processing`
   - Dead letter queue for failed jobs
   - Lambda function (placeholder - needs deployment package)
   - IAM roles for SQS, S3, Secrets Manager access

2. **Wired up main.tf**
   - Added `BMX_IMAGE_PROCESSING_QUEUE_NAME` env var to API Lambda
   - Added `api_lambda_role_name` to image-processor module for IAM permissions
   - API Lambda can send messages to image processing queue

3. **Added health checks**
   - `health.py`: Added `check_sqs()` function to verify all SQS queues
   - `admin.py`: Added `image_processing_queue` to InfrastructureConfig
   - Frontend: Updated AdminConfigView.vue to show SQS health status

### Files Modified

| File | Change |
|------|--------|
| `infra/terraform/main.tf` | Added queue env var + api_lambda_role_name |
| `infra/terraform/modules/image-processor/main.tf` | Added api_sqs_send IAM policy |
| `infra/terraform/modules/image-processor/variables.tf` | Added api_lambda_role_name var |
| `backend/app/api/v1/health.py` | Added check_sqs() for all SQS queues |
| `backend/app/api/v1/admin.py` | Added image_processing_queue to InfrastructureConfig |
| `frontend/src/types/admin.ts` | Added SqsHealthCheck types |
| `frontend/src/views/AdminConfigView.vue` | Added SQS health display section |

---

## Part 2: Critical Issue - Database Password Changed

### What Happened

Ran terraform apply with `-target` flags to deploy only the image processor:

```bash
terraform apply -var="db_password=not-used" \
  -target=module.image_processor \
  -target=module.lambda
```

**Problem:** Terraform still modified the RDS master password to "not-used" even though the database module wasn't targeted.

### Root Cause

The `-target` flag limits which resources terraform plans to modify, but Terraform still evaluates all resources and may apply changes to dependencies or resources with changed input values.

The `db_password` variable is passed to the RDS module, and even with `-target` excluding the database, Terraform detected the variable value changed and applied it.

### Impact

- Staging database authentication broken
- Health check shows `password authentication failed for user "bluemoxon"`

### Fixes Applied

1. **Immediate:** Reset RDS password via AWS CLI - **DONE**
2. **Prevention:** Added `password` to RDS module's `lifecycle { ignore_changes }` - **DONE**
3. **Permanent fix:** Replaced `db_password` variable with `random_password` resource - **DONE**

The `random_password` resource generates the password once and never changes it (`ignore_changes = all`). This eliminates the entire class of "accidentally passed wrong password" bugs.

---

## Part 3: SQS Health Check Permissions

### Issue

Health check returns `NonExistentQueue` error even though queues exist:

```json
{
  "sqs": {
    "status": "unhealthy",
    "queues": {
      "image_processing": {
        "status": "unhealthy",
        "queue_name": "bluemoxon-staging-image-processing",
        "error": "AWS.SimpleQueueService.NonExistentQueue"
      }
    }
  }
}
```

### Root Cause

The error is misleading - it's actually an IAM permissions issue. The API Lambda has `sqs:SendMessage` permission but NOT `sqs:GetQueueUrl` or `sqs:GetQueueAttributes` needed for health checks.

### Fix Required

Add health check permissions to each worker module's `api_sqs_send` IAM policy:

```hcl
Action = [
  "sqs:SendMessage",
  "sqs:GetQueueUrl",
  "sqs:GetQueueAttributes"
]
```

---

## Created Resources

### GitHub Issue #1140

Created checklist for adding new async worker flows:

1. Create Terraform module with SQS queue + Lambda
2. Add IAM policies for API Lambda to send messages
3. Add queue name to API Lambda environment variables
4. Update health.py to check new queue
5. Update admin.py InfrastructureConfig
6. Update AdminConfigView.vue to display new queue status
7. Update frontend types (admin.ts)

---

## Next Steps

1. [x] Fix RDS password (reset to Secrets Manager value)
2. [x] Add `password` to RDS module `ignore_changes`
3. [x] Add SQS health check permissions to all worker modules
4. [x] Replace `db_password` variable with `random_password` resource
5. [ ] Merge PR #1141 and run `terraform apply`
6. [ ] Import existing password into terraform state (for existing databases)
7. [ ] Deploy image processor Lambda code (needs container-based Lambda or Layer with rembg)
8. [ ] Test end-to-end image processing flow

---

## Part 4: Permanent Fix - Safe Database Password Handling

### Problem

The initial `random_password` approach had a critical flaw:

| Step | What Happens |
|------|--------------|
| 1 | `random_password` is NEW (not in state) |
| 2 | Terraform generates a new random password |
| 3 | RDS: `ignore_changes = [password]` → no change |
| 4 | **Secrets Manager: UPDATES to new password** |
| 5 | **BREAKAGE**: App reads new password, RDS has old |

### Solution

Added `use_existing_database_credentials` variable:

```hcl
# For EXISTING environments: Read from Secrets Manager (source of truth)
data "aws_secretsmanager_secret_version" "existing_database" {
  count     = var.enable_database && var.use_existing_database_credentials ? 1 : 0
  secret_id = "${local.name_prefix}/database"
}

# For NEW environments: Generate random password
resource "random_password" "database" {
  count = var.enable_database && !var.use_existing_database_credentials ? 1 : 0
  ...
}

# Password source depends on environment type
locals {
  db_password = var.use_existing_database_credentials
    ? jsondecode(data.aws_secretsmanager_secret_version.existing_database[0].secret_string).password
    : random_password.database[0].result
}
```

### Usage

| Environment | Setting | Behavior |
|-------------|---------|----------|
| Existing (staging) | `use_existing_database_credentials = true` | Reads from Secrets Manager |
| New environment | `use_existing_database_credentials = false` | Uses random_password |

### Verification

```bash
# This should show NO CHANGES to database resources
AWS_PROFILE=bmx-staging terraform plan -var-file=envs/staging.tfvars
```

---

## Part 5: Admin Config SQS Display Fix

### Issue

After terraform apply, the `/admin/system-info` endpoint returned SQS health data in `/health/deep`, but the Admin Config page's System Status tab only showed Database, S3 Images, and Cognito - no SQS.

### Root Cause

The `admin.py` `/admin/system-info` endpoint wasn't calling `check_sqs()` or including SQS in the `HealthChecks` response model.

### Fix (PR #1142)

Added SQS health check to admin.py:

1. Added `check_sqs` to imports from health.py
2. Created Pydantic models: `SqsQueueHealth`, `SqsHealthCheck`
3. Added `sqs` field to `HealthChecks` model
4. Called `check_sqs()` in system-info endpoint
5. Updated overall health calculation to include SQS status

### Verification

Admin Config page now shows "SQS Queues - 112ms" in Health Checks section with checkmark.

---

## Part 6: Deployment and Testing

### Completed

1. **Merged PR #1141** - Database password protection and SQS health permissions
2. **Ran terraform apply** - All SQS queues now healthy:
   - bluemoxon-staging-eval-runbook
   - bluemoxon-staging-image-processing
   - bluemoxon-staging-tracking-worker
3. **Merged PR #1142** - SQS display in admin config page
4. **Verified health endpoint** - All queues showing healthy status
5. **Tested eBay import** - Successfully imported listing 235937594146 (book ID 634)

### Health Check Results

```json
{
  "sqs": {
    "status": "healthy",
    "latency_ms": 112.17,
    "queues": {
      "eval_runbook": { "status": "healthy", "messages": 0 },
      "image_processing": { "status": "healthy", "messages": 0 },
      "tracking_worker": { "status": "healthy", "messages": 0 }
    }
  }
}
```

---

## Part 7: Phased Implementation Status

This feature is being implemented in phases:

### Phase 1: Infrastructure (COMPLETE)

| Component | Status | Notes |
|-----------|--------|-------|
| SQS queue | ✅ | `bluemoxon-staging-image-processing` |
| Dead letter queue | ✅ | For failed jobs |
| Lambda resource | ✅ | Created in Terraform (placeholder code) |
| IAM permissions | ✅ | SQS, S3, Secrets Manager |
| Health checks | ✅ | All queues reporting healthy |
| Admin UI | ✅ | SQS status visible in config page |

### Phase 2: Lambda Code Deployment (NOT STARTED)

| Component | Status | Notes |
|-----------|--------|-------|
| Handler code | ❌ | `backend/lambdas/image_processor/handler.py` exists but not deployed |
| rembg dependency | ❌ | Requires container-based Lambda or Layer |
| Deployment script | ❌ | Need to build and deploy container image |

**Blocker:** rembg has native dependencies (onnxruntime) that require either:
- Container-based Lambda (ECR image)
- Lambda Layer with pre-compiled binaries

### Phase 3: API Integration (ROOT CAUSE FOUND)

| Component | Status | Notes |
|-----------|--------|-------|
| `queue_image_processing()` service | ✅ | Exists in `image_processing.py` |
| Called on manual image upload | ⚠️ | Only for **primary image** (`is_primary=True`) |
| Called during eBay import | ❌ | **NOT CALLED** - root cause identified |
| ImageProcessingJob model | ✅ | Database model exists |

**Root Cause Investigation (2026-01-17):**

CloudWatch logs showed:
```
Copied listings/235937594146/image_00.webp -> books/634/image_00.webp
Copied 5 images for book 634
```

But NO logs about queueing image processing. Traced to `books.py:320-365`:

1. Images copied from listings/ to books/ ✓
2. Thumbnails generated ✓
3. BookImage records created ✓
4. **`queue_image_processing()` NOT called** ❌

The import flow in `books.py` directly copies images without going through the upload endpoint (`images.py`), which is where `queue_image_processing()` is wired.

**Fix Required:** Add `queue_image_processing()` call to `books.py` after image copy, around line 365.

### Next Steps

1. [ ] Add `queue_image_processing()` to import flow in `books.py`
2. [ ] Deploy image processor Lambda (Phase 2)
   - Build container image with rembg
   - Push to ECR
   - Update Lambda to use container
3. [ ] Test end-to-end processing
4. [ ] Consider processing ALL images, not just primary

---

## Lessons Learned

1. **Never use `-var="db_password=not-used"` with terraform apply** - Terraform may still apply the value even with `-target` flags
2. **Use `terraform plan` first** - Always review what will change before applying
3. **Add sensitive resources to `ignore_changes`** - Protect critical infrastructure from accidental modifications
4. **Health check permissions are separate** - Just because Lambda can send to a queue doesn't mean it can inspect the queue
5. **Use `random_password` for database credentials** - Eliminates the entire class of "wrong password" accidents
6. **Admin endpoints need explicit health calls** - The system-info endpoint required explicit `check_sqs()` call to include SQS in the response
