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

### Fix Required

1. **Immediate:** Reset RDS password to match Secrets Manager value
2. **Prevention:** Add `password` to RDS module's `lifecycle { ignore_changes }` block

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

1. [ ] Fix RDS password (reset to Secrets Manager value)
2. [ ] Add `password` to RDS module `ignore_changes`
3. [ ] Add SQS health check permissions to all worker modules
4. [ ] Deploy image processor Lambda code (needs container-based Lambda or Layer with rembg)
5. [ ] Test end-to-end image processing flow

---

## Lessons Learned

1. **Never use `-var="db_password=not-used"` with terraform apply** - Terraform may still apply the value even with `-target` flags
2. **Use `terraform plan` first** - Always review what will change before applying
3. **Add sensitive resources to `ignore_changes`** - Protect critical infrastructure from accidental modifications
4. **Health check permissions are separate** - Just because Lambda can send to a queue doesn't mean it can inspect the queue
