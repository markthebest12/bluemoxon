# Eval Runbook Scaling Roadmap

This document outlines the scaling path for the Eval Runbook generation system, from single-user to multi-tenant platform.

## Current Architecture (Phase 1 - Single User)

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  Lambda (API)                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │  POST /books/import-ebay                          │  │
│  │    1. Fetch eBay listing                          │  │
│  │    2. Download images                             │  │
│  │    3. Claude Vision analysis (single call)        │  │
│  │    4. FMV lookup (eBay + AbeBooks)                │  │
│  │    5. Generate scores                             │  │
│  │    6. Save Book + EvalRunbook                     │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Characteristics:**
- Synchronous, blocking request
- 30-60 second response time
- Simple to debug and maintain
- Adequate for single-user workflow

**Limitations:**
- No parallelism (FMV lookups are sequential)
- Single point of failure (if Claude API slow, whole request slow)
- No retry granularity (failure = retry everything)
- Doesn't scale for concurrent users

---

## Future Architecture (Phase 2 - Multi-Tenant Platform)

When scaling to multiple users, migrate to AWS Step Functions for orchestration:

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Lambda (Import Initiator)                  │
│  - Validate request                                     │
│  - Start Step Function execution                        │
│  - Return execution ARN immediately                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Step Functions Workflow                    │
│                                                         │
│  ┌─────────────────┐                                    │
│  │  Fetch Listing  │                                    │
│  │  (Lambda)       │                                    │
│  └────────┬────────┘                                    │
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                    │
│  │ Download Images │                                    │
│  │ (Lambda → S3)   │                                    │
│  └────────┬────────┘                                    │
│           │                                             │
│           ▼                                             │
│  ┌────────────────────────────────────────────┐         │
│  │            Parallel Analysis               │         │
│  │  ┌──────────────┐  ┌──────────┐  ┌───────┐│         │
│  │  │Claude Vision │  │eBay FMV  │  │AbeBooks││         │
│  │  │  (Lambda)    │  │(Lambda)  │  │(Lambda)││         │
│  │  └──────────────┘  └──────────┘  └───────┘│         │
│  └────────────────────────┬───────────────────┘         │
│                           │                             │
│                           ▼                             │
│  ┌─────────────────────────────────────────────┐        │
│  │         Assemble & Score (Lambda)           │        │
│  │  - Combine all analysis results             │        │
│  │  - Calculate scores                         │        │
│  │  - Generate recommendation                  │        │
│  │  - Save EvalRunbook                         │        │
│  └─────────────────────────────────────────────┘        │
│                           │                             │
│                           ▼                             │
│  ┌─────────────────────────────────────────────┐        │
│  │         Notify User (Lambda)                │        │
│  │  - WebSocket push / Email / In-app          │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

**Benefits:**
- True parallelism (Claude + eBay + AbeBooks run simultaneously)
- Granular retries (retry just the failed step)
- Better timeout handling (each step has own limit)
- Built-in execution history and debugging
- Scales to concurrent users without blocking

**Step Functions State Machine Definition:**

```json
{
  "Comment": "Eval Runbook Generation Workflow",
  "StartAt": "FetchListing",
  "States": {
    "FetchListing": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:bmx-fetch-listing",
      "Next": "DownloadImages",
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 2}]
    },
    "DownloadImages": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:bmx-download-images",
      "Next": "ParallelAnalysis"
    },
    "ParallelAnalysis": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "ClaudeVisionAnalysis",
          "States": {
            "ClaudeVisionAnalysis": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:bmx-claude-analysis",
              "End": true,
              "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 2}]
            }
          }
        },
        {
          "StartAt": "EbayFMVLookup",
          "States": {
            "EbayFMVLookup": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:bmx-ebay-fmv",
              "End": true,
              "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 3}]
            }
          }
        },
        {
          "StartAt": "AbebooksFMVLookup",
          "States": {
            "AbebooksFMVLookup": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:bmx-abebooks-fmv",
              "End": true,
              "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 3}]
            }
          }
        }
      ],
      "Next": "AssembleAndScore"
    },
    "AssembleAndScore": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:bmx-assemble-runbook",
      "Next": "NotifyUser"
    },
    "NotifyUser": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:bmx-notify-user",
      "End": true
    }
  }
}
```

---

## Migration Path

### When to Migrate

Consider migrating to Phase 2 when:
- Multiple users are importing books concurrently
- Import times become unacceptable (>90 seconds)
- Need for better observability into each step
- Retry logic becomes complex in monolithic Lambda
- Cost optimization needed (parallel = faster = less Lambda time)

### Migration Steps

1. **Extract Lambdas** (Low risk)
   - Move each logical step to its own Lambda function
   - Keep Phase 1 architecture working while building
   - Test each Lambda independently

2. **Create Step Function** (Medium risk)
   - Define state machine in Terraform
   - Wire up Lambda functions
   - Test end-to-end in staging

3. **Update API** (Low risk)
   - Change import endpoint to start Step Function
   - Return execution ARN for status polling
   - Add `/import/{executionId}/status` endpoint

4. **Add Real-time Updates** (Optional)
   - WebSocket API for progress updates
   - Or polling endpoint for status

5. **Deprecate Monolithic Path**
   - Remove old synchronous code
   - Update documentation

### Terraform Modules Needed

```hcl
# New modules for Phase 2
module "step_functions" {
  source = "./modules/step-functions"

  workflow_name = "eval-runbook-generation"
  lambdas = {
    fetch_listing    = module.lambda_fetch_listing.arn
    download_images  = module.lambda_download_images.arn
    claude_analysis  = module.lambda_claude_analysis.arn
    ebay_fmv        = module.lambda_ebay_fmv.arn
    abebooks_fmv    = module.lambda_abebooks_fmv.arn
    assemble        = module.lambda_assemble.arn
    notify          = module.lambda_notify.arn
  }
}

# Individual Lambda modules
module "lambda_fetch_listing" {
  source        = "./modules/lambda"
  function_name = "${var.environment}-fetch-listing"
  handler       = "app.workers.fetch_listing.handler"
  timeout       = 30
}

# ... similar for other Lambdas
```

---

## Cost Comparison

### Phase 1 (Current)
- Single Lambda execution: ~60 seconds
- Cost per import: ~$0.001 (Lambda) + ~$0.03 (Claude) + ~$0.01 (eBay API)
- **Total: ~$0.04 per import**

### Phase 2 (Step Functions)
- Multiple shorter Lambda executions: ~30 seconds total (parallel)
- Step Functions: $0.025 per 1000 state transitions (~6 transitions = $0.00015)
- Cost per import: ~$0.0008 (Lambda) + ~$0.03 (Claude) + ~$0.01 (eBay API) + $0.00015 (SF)
- **Total: ~$0.04 per import** (similar, but faster)

Step Functions adds minimal cost but provides significant operational benefits.

---

## API Changes for Phase 2

### Current (Phase 1)
```
POST /books/import-ebay
Request: { "url": "https://ebay.com/..." }
Response: { "book": {...}, "eval_runbook": {...} }
Time: 30-60 seconds (blocking)
```

### Future (Phase 2)
```
POST /books/import-ebay
Request: { "url": "https://ebay.com/..." }
Response: { "execution_id": "abc-123", "status": "RUNNING" }
Time: <1 second

GET /books/import/{execution_id}/status
Response: {
  "status": "RUNNING|SUCCEEDED|FAILED",
  "progress": {
    "fetch_listing": "COMPLETED",
    "download_images": "COMPLETED",
    "claude_analysis": "RUNNING",
    "ebay_fmv": "COMPLETED",
    "abebooks_fmv": "RUNNING",
    "assemble": "PENDING"
  },
  "book_id": null,  // populated when complete
  "error": null
}
```

### WebSocket Alternative (Real-time)
```
WS /ws/import/{execution_id}
Messages:
  { "step": "fetch_listing", "status": "completed" }
  { "step": "claude_analysis", "status": "running", "progress": "3/19 images" }
  { "step": "complete", "book_id": 123 }
```

---

## Summary

| Aspect | Phase 1 (Current) | Phase 2 (Future) |
|--------|-------------------|------------------|
| Architecture | Single Lambda | Step Functions |
| Parallelism | None | Full |
| Response time | 30-60s blocking | <1s + async |
| Retry granularity | All or nothing | Per-step |
| Debugging | CloudWatch logs | Step Functions console |
| Scaling | Limited | Excellent |
| Complexity | Low | Medium |
| When to use | Single user | Multi-tenant |

**Recommendation:** Stay on Phase 1 until user growth demands scaling. The migration path is well-defined and can be executed incrementally.
