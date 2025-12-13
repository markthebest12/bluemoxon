# Async Analysis Infrastructure Implementation

**Date:** 2025-12-13
**Status:** Completed
**Design Doc:** [2025-12-12-async-analysis-jobs-design.md](./2025-12-12-async-analysis-jobs-design.md)

## Summary

Implemented SQS-based async analysis infrastructure to handle 5+ minute Bedrock calls that exceed API Gateway's 29-second timeout.

## What Was Implemented

### Infrastructure (Terraform)

1. **SQS Queue:** `bluemoxon-{env}-analysis-jobs`
   - Standard queue with 660s visibility timeout
   - Long polling (20s receive wait)
   - 4-day message retention

2. **Dead Letter Queue:** `bluemoxon-{env}-analysis-jobs-dlq`
   - maxReceiveCount: 2 (retry twice before DLQ)
   - 14-day retention for investigation

3. **Worker Lambda:** `bluemoxon-{env}-analysis-worker`
   - Handler: `app.worker.handler`
   - Timeout: 600s (10 minutes)
   - Memory: 256MB
   - Triggered by SQS event source
   - Same deployment package as API Lambda

### API Endpoints

- `POST /books/{id}/analysis/generate-async` - Start async job (returns 202)
- `GET /books/{id}/analysis/status` - Poll job status (with stale detection)

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/worker.py` | Worker Lambda handler |
| `backend/app/services/sqs.py` | SQS message sending |
| `backend/app/models/analysis_job.py` | AnalysisJob model |
| `backend/app/schemas/analysis_job.py` | Pydantic schema |
| `infra/terraform/modules/analysis-worker/` | Terraform module |
| `infra/terraform/main.tf` | Module instantiation |
| `frontend/src/views/AcquisitionsView.vue` | Async UI with polling |

## Fixes Applied During Implementation

### 1. Import Path Fix (worker.py:12)

**Problem:** `No module named 'app.database'`

**Fix:**
```python
# Before
from app.database import SessionLocal

# After
from app.db import SessionLocal
```

### 2. Bedrock Model ID Fix (main.tf)

**Problem:** `AccessDeniedException` - IAM policy had wrong model IDs

**Root Cause:** Bedrock has two ID formats:
- Foundation models: `anthropic.claude-sonnet-4-5-20250514`
- Cross-region profiles: `us.anthropic.claude-sonnet-4-5-20250514-v1:0`

**Fix:** Use wildcards to cover all versions:
```hcl
bedrock_model_ids = [
  "anthropic.claude-sonnet-4-5-*",
  "anthropic.claude-opus-4-5-*"
]
```

### 3. FMV Extraction Fix (worker.py:147-158)

**Problem:** `AttributeError: 'ParsedAnalysis' object has no attribute 'fair_market_value_low'`

**Root Cause:** FMV data is nested in `market_analysis.valuation`, not top-level attributes

**Fix:**
```python
# Before (wrong)
if parsed.fair_market_value_low is not None:
    book.fair_market_value = parsed.fair_market_value_low

# After (correct)
valuation = (parsed.market_analysis or {}).get("valuation", {})
fmv_low = valuation.get("low")
if fmv_low is not None:
    book.fair_market_value = Decimal(str(fmv_low))
```

### 4. Stale Job Detection (books.py:1329-1381)

**Problem:** Jobs stuck in "running" forever if Lambda crashes/times out

**Root Cause:** Lambda hard-crashes (timeout, OOM) can't execute cleanup code

**Fix:** API-side detection in status endpoint:
```python
STALE_JOB_THRESHOLD_MINUTES = 15

if job.status == "running":
    stale_threshold = datetime.now(UTC) - timedelta(minutes=STALE_JOB_THRESHOLD_MINUTES)
    if job.updated_at < stale_threshold:
        job.status = "failed"
        job.error_message = "Job timed out after 15 minutes (worker likely crashed)"
        db.commit()
```

## Lessons Learned

### 1. Lambda Code Caching

**Issue:** Multiple Lambda execution environments can run different code versions during deployment.

**Mitigation:** Force Lambda configuration update to refresh environments:
```bash
aws lambda update-function-configuration --function-name X --description "Force refresh"
```

### 2. CloudWatch Log Delivery Lag

**Issue:** Logs can take several minutes to appear in CloudWatch, making debugging confusing.

**Mitigation:** Don't assume a job failed just because logs haven't appeared. Check job status via API.

### 3. Async Job Recovery

**Pattern:** Jobs can get stuck in "running" if:
- Lambda times out during Bedrock call
- Lambda OOMs
- Unhandled exception before status update

**Solutions implemented:**
1. Stale job detection in status endpoint (done)
2. SQS DLQ captures repeated failures

**Future considerations:**
- Worker heartbeat updates during long operations
- Idempotent re-processing for duplicate messages

## Testing Verification

Verified end-to-end:
- Book 2: Job `d6642edd` completed successfully, FMV updated to $175.00
- Book 3: Job `acdcf964` completed successfully, FMV updated to $50.00

## Deployment

Changes deployed to staging via GitHub Actions workflow triggered by push to `staging` branch.

### Config Updates Required

Added to `infra/config/staging.json` and `production.json`:
```json
{
  "lambda": {
    "worker_function_name": "bluemoxon-{env}-analysis-worker"
  }
}
```

### Deploy Workflow Updates

Added worker Lambda deployment to `.github/workflows/deploy.yml`:
```yaml
- name: Deploy Worker Lambda
  run: |
    aws lambda update-function-code \
      --function-name ${{ env.WORKER_FUNCTION_NAME }} \
      --zip-file fileb://lambda.zip
```
