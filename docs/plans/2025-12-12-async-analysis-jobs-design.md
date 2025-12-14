# Async Analysis Jobs Design

**Date:** 2025-12-12
**Status:** Implemented (2025-12-13)
**Implementation:** [2025-12-13-async-analysis-implementation.md](./2025-12-13-async-analysis-implementation.md)
**Problem:** API Gateway 29-second timeout causes 503 errors when Bedrock Sonnet 4.5 takes 5+ minutes

## Solution Overview

Replace synchronous analysis generation with async job queue pattern:
1. API creates job record, sends message to SQS, returns immediately
2. Worker Lambda processes job in background (up to 10 minutes)
3. Frontend polls for job status

## Database Schema

```sql
CREATE TABLE analysis_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
    model VARCHAR(50) NOT NULL DEFAULT 'sonnet',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- Prevent multiple active jobs for same book
    CONSTRAINT unique_active_job EXCLUDE USING btree (book_id WITH =)
        WHERE (status IN ('pending', 'running'))
);

CREATE INDEX idx_analysis_jobs_book_status ON analysis_jobs(book_id, status);
```

## API Endpoints

### POST /books/{id}/analysis/generate

Start async analysis generation.

**Request:**
```json
{ "model": "sonnet" }  // optional, defaults to sonnet
```

**Response (202 Accepted):**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "book_id": 123,
  "created_at": "2025-12-12T22:00:00Z"
}
```

**Errors:**
- 409 Conflict: Job already in progress for this book
- 404: Book not found

### GET /books/{id}/analysis/status

Get status of latest analysis job.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "running",
  "model": "sonnet",
  "created_at": "2025-12-12T22:00:00Z",
  "updated_at": "2025-12-12T22:02:15Z",
  "completed_at": null,
  "error_message": null
}
```

## AWS Infrastructure

### SQS Queue: bluemoxon-{env}-analysis-jobs

- Type: Standard (not FIFO)
- Visibility timeout: 600s (10 min)
- Message retention: 4 days
- Receive wait time: 20s (long polling)

### SQS Dead Letter Queue: bluemoxon-{env}-analysis-jobs-dlq

- maxReceiveCount: 2 (retry twice, then DLQ)

### Lambda: bluemoxon-{env}-analysis-worker

- Same deployment package as API Lambda
- Handler: `app.worker.handler`
- Timeout: 600s
- Memory: 256MB
- Triggered by SQS
- Reserved concurrency: 5 (limit parallel Bedrock calls)

### Message Format

```json
{
  "job_id": "uuid",
  "book_id": 123,
  "model": "sonnet"
}
```

## Worker Flow

1. Receive message from SQS
2. Update job status → `running`
3. Fetch book data and images (existing code)
4. Call Bedrock `invoke_bedrock()` (existing code)
5. Save analysis to DB (existing code)
6. Update job status → `completed` with `completed_at`
7. On error: Update job status → `failed` with `error_message`

## Frontend Changes

### State Management

```typescript
const analysisJob = ref<{
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  error_message?: string;
} | null>(null);
```

### UI States

| State | Button | Display |
|-------|--------|---------|
| No analysis, no job | "Generate Analysis" (enabled) | - |
| Job pending/running | "Generating..." (disabled, spinner) | "Started X ago..." |
| Job completed | "Regenerate" (enabled) | Show analysis |
| Job failed | "Retry Analysis" (enabled) | Show error |

### Polling

- Poll every 5 seconds while status is `pending` or `running`
- On page load, check for active job and resume polling
- Stop polling when status is `completed` or `failed`

## Reliability Features

- **Idempotent:** Check if analysis exists before saving (handles retries)
- **Duplicate prevention:** DB constraint prevents multiple active jobs per book
- **Automatic retries:** SQS retries failed jobs twice before DLQ
- **Visibility:** Failed jobs land in DLQ for investigation
- **Graceful degradation:** Frontend shows error and allows retry
<<<<<<< HEAD
- **Stale job detection:** Status endpoint auto-fails jobs stuck >15 minutes (handles Lambda crashes/timeouts)
=======
>>>>>>> 08cb3d3 (docs: Add async analysis jobs design for Bedrock timeout fix)

## Migration Path

1. Deploy new infrastructure (SQS, worker Lambda)
2. Deploy new API endpoints
3. Update frontend to use new endpoints
4. Old sync endpoint continues working (logs deprecation warning)
5. Remove old endpoint after confirming new flow works
