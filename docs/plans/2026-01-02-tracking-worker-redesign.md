# Tracking Worker Redesign

**Date**: 2026-01-02
**Issue**: Code review feedback on #516
**Status**: Approved

## Problem

The carrier API tracking implementation has architectural issues:

1. **Lambda doing too much** - HTTP API and EventBridge polling in same Lambda
2. **Polling timeout risk** - 50 books × 15s = 750s, Lambda max is 900s
3. **Phone validation API-only** - Direct DB inserts bypass validation
4. **Carrier detection non-deterministic** - Overlapping patterns, dict order dependency
5. **No circuit breaker** - Hammers failing carrier APIs

## Solution

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌────────────┐
│ EventBridge │────▶│ Dispatcher  │────▶│ SQS Queue   │────▶│ Worker     │
│ (hourly)    │     │ Lambda      │     │ + DLQ       │     │ Lambda     │
└─────────────┘     └─────────────┘     └─────────────┘     └────────────┘
```

- **Dispatcher Lambda**: Queries active books, sends IDs to SQS
- **SQS Queue**: Buffers book IDs, DLQ after 3 retries
- **Worker Lambda**: Processes one book, fetches carrier API, updates DB
- **API Lambda**: HTTP only, no EventBridge routing

### Database Changes

**1. Phone number CHECK constraint:**

```sql
ALTER TABLE users
ADD CONSTRAINT users_phone_number_e164
CHECK (phone_number IS NULL OR phone_number ~ '^\+[1-9]\d{1,14}$');
```

**2. Circuit breaker table:**

```sql
CREATE TABLE carrier_circuit_state (
    carrier_name VARCHAR(50) PRIMARY KEY,
    failure_count INTEGER NOT NULL DEFAULT 0,
    last_failure_at TIMESTAMP WITH TIME ZONE,
    circuit_open_until TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Code Changes

**Remove from `main.py`:**

- Delete EventBridge routing (lines 125-144)

**New files:**

- `backend/app/workers/tracking_dispatcher.py` - EventBridge handler
- `backend/app/workers/tracking_worker.py` - SQS handler
- `backend/app/models/carrier_circuit.py` - Circuit state model
- `backend/app/services/circuit_breaker.py` - Circuit breaker logic

**Remove:**

- `detect_and_get_carrier()` from `carriers/__init__.py` - require explicit carrier

### Terraform

New module: `infra/terraform/modules/tracking-worker/`

| Resource | Purpose |
|----------|---------|
| `aws_sqs_queue.jobs` | Tracking job queue |
| `aws_sqs_queue.dlq` | Dead letter queue |
| `aws_lambda_function.dispatcher` | EventBridge → SQS |
| `aws_lambda_function.worker` | SQS → carrier API |
| `aws_cloudwatch_event_rule.hourly` | Hourly trigger |

**Key settings:**

- Worker timeout: 60s
- Worker concurrency: 10 (limit parallel carrier calls)
- SQS visibility timeout: 120s
- DLQ max receive count: 3

### Circuit Breaker Logic

- On success: reset `failure_count` to 0
- On failure: increment `failure_count`, set `last_failure_at`
- If `failure_count >= 3`: set `circuit_open_until` to NOW + 30 minutes
- Before calling carrier: skip if `circuit_open_until > NOW`

## Files to Create/Modify

### Create

- `backend/app/workers/tracking_dispatcher.py`
- `backend/app/workers/tracking_worker.py`
- `backend/app/models/carrier_circuit.py`
- `backend/app/services/circuit_breaker.py`
- `backend/alembic/versions/x_add_circuit_breaker.py`
- `backend/tests/workers/test_tracking_dispatcher.py`
- `backend/tests/workers/test_tracking_worker.py`
- `backend/tests/services/test_circuit_breaker.py`
- `infra/terraform/modules/tracking-worker/main.tf`
- `infra/terraform/modules/tracking-worker/variables.tf`
- `infra/terraform/modules/tracking-worker/outputs.tf`

### Modify

- `backend/app/main.py` - Remove EventBridge routing
- `backend/app/services/carriers/__init__.py` - Remove `detect_and_get_carrier()`
- `backend/app/services/tracking_poller.py` - Refactor into worker
- `infra/terraform/envs/staging.tfvars` - Add tracking-worker module
- `infra/terraform/envs/production.tfvars` - Add tracking-worker module
- `.github/workflows/deploy.yml` - Deploy new Lambdas

## Testing

- `test_dispatcher_sends_all_active_books_to_sqs`
- `test_worker_updates_book_on_success`
- `test_worker_raises_on_circuit_open`
- `test_circuit_opens_after_3_failures`
- `test_circuit_resets_on_success`
- `test_phone_validation_rejects_invalid_format`
