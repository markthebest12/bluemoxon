# Operations Runbook

Operational procedures for BlueMoxon production and staging environments.

## Health Checks

### Quick Health Check

```bash
# Staging
curl -s https://staging.api.bluemoxon.com/api/v1/health/live | jq

# Production
curl -s https://api.bluemoxon.com/api/v1/health/live | jq
```

### Deep Health Check

Validates all dependencies (database, S3, Cognito):

```bash
# Staging
curl -s https://staging.api.bluemoxon.com/api/v1/health/deep | jq

# Production
curl -s https://api.bluemoxon.com/api/v1/health/deep | jq
```

**Expected response:**

```json
{
  "status": "healthy",
  "database": "ok",
  "s3": "ok",
  "cognito": "ok"
}
```

### Version Check

```bash
curl -s https://api.bluemoxon.com/api/v1/health/version | jq
```

### Health Endpoints Reference

| Endpoint | Purpose |
|----------|---------|
| `/health/live` | Liveness probe (Lambda running) |
| `/health/ready` | Readiness probe (dependencies accessible) |
| `/health/deep` | Full dependency check |
| `/health/info` | Build info (git SHA, deploy time) |
| `/health/version` | Version string only |

---

## Database Operations

### Run Migrations

Since Aurora is in a private VPC, run migrations via API:

```bash
# Staging (test first)
curl -X POST https://staging.api.bluemoxon.com/api/v1/health/migrate

# Production
curl -X POST https://api.bluemoxon.com/api/v1/health/migrate
```

**When to run:**

- After deploying code with new migrations
- If you see "duplicate key" errors
- After manual database operations

### Cleanup Orphan S3 Images

Remove orphaned images from S3 (images not associated with any book):

```bash
# Scan for orphans (dry run)
curl -X POST https://api.bluemoxon.com/api/v1/admin/maintenance/orphan-scan

# Delete orphans (with confirmation)
curl -X POST https://api.bluemoxon.com/api/v1/admin/maintenance/orphan-cleanup
```

**Features (v1.2):**

- **Size display** - Shows total size of orphaned files before deletion
- **Progress tracking** - Real-time progress updates during cleanup
- **Confirmation** - Requires explicit confirmation before deletion
- **Grouping** - Orphans grouped by book ID for easier review

### Cleanup Listings Directory

Remove orphaned listing images from S3 `listings/` prefix:

```bash
# Scan for orphan listings
curl -X POST https://api.bluemoxon.com/api/v1/admin/maintenance/listings-scan

# Delete orphan listings
curl -X POST https://api.bluemoxon.com/api/v1/admin/maintenance/listings-cleanup
```

**Note:** Listing images are temporary - they're copied to book images on acquisition. The `listings/` directory can be cleaned periodically.

### Prod → Staging Sync

Sync production data to staging for testing:

**Option 1: Lambda-based sync (recommended)**

```bash
aws lambda invoke --function-name bluemoxon-staging-db-sync --profile bmx-staging --payload '{}' .tmp/sync-response.json
cat .tmp/sync-response.json | jq
```

**Option 2: Script-based sync**

```bash
./scripts/sync-prod-to-staging.sh
```

Options:

- `--images-only` - Only sync S3 images
- `--db-only` - Only sync database
- `--dry-run` - Show what would be done

See [DATABASE_SYNC.md](DATABASE_SYNC.md) for full details.

---

## Lambda Operations

### View Lambda Logs

```bash
# Staging API logs (last 5 minutes)
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-api --since 5m

# Production API logs
AWS_PROFILE=bmx-prod aws logs tail /aws/lambda/bluemoxon-api --since 5m

# Follow logs in real-time
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-api --follow
```

### Check Lambda Configuration

```bash
AWS_PROFILE=bmx-staging aws lambda get-function-configuration --function-name bluemoxon-staging-api --query 'Environment'
```

### Lambda Functions Reference

| Function | Purpose | Timeout |
|----------|---------|---------|
| `bluemoxon-api` / `bluemoxon-staging-api` | Main API | 30s |
| `bluemoxon-analysis-worker` | Async Napoleon analysis | 600s |
| `bluemoxon-eval-runbook-worker` | Async eval runbook generation | 600s |
| `bluemoxon-profile-worker` | Entity profile generation (BMX 3.0) | 600s |
| `bluemoxon-image-processor` | AI background removal (container) | 300s |
| `bluemoxon-retry-queue-failed` | Retry failed image processing jobs | 60s |
| `bluemoxon-scraper` | eBay Playwright scraping | 120s |
| `bluemoxon-staging-db-sync` | Prod→Staging data sync | 300s |

---

## Async Job Monitoring

### Analysis Jobs

Analysis jobs run in SQS-triggered Lambda to bypass API Gateway's 29s timeout.

**Check job status:**

```bash
bmx-api GET /books/{book_id}
# Look for analysis_job_status: "running" | "completed" | "failed"
```

**View worker logs:**

```bash
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-analysis-worker --since 10m
```

### Eval Runbook Jobs

```bash
bmx-api GET /books/{book_id}
# Look for eval_runbook_job_status: "running" | "completed" | "failed"
```

**View worker logs:**

```bash
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-eval-runbook-worker --since 10m
```

### Image Processing Jobs

Image processing (background removal, thumbnails) runs via container-based Lambda:

**Check queue depth:**

```bash
AWS_PROFILE=bmx-staging aws sqs get-queue-attributes \
  --queue-url https://sqs.us-west-2.amazonaws.com/ACCOUNT/bluemoxon-staging-image-processor \
  --attribute-names ApproximateNumberOfMessages
```

**View processor logs:**

```bash
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-image-processor --since 10m
```

**Retry failed jobs:**

Failed image processing jobs can be retried via the retry-queue-failed Lambda:

```bash
# Invoke retry Lambda (moves DLQ messages back to main queue)
AWS_PROFILE=bmx-staging aws lambda invoke \
  --function-name bluemoxon-staging-retry-queue-failed \
  --payload '{}' \
  .tmp/retry-response.json
```

### Profile Generation Jobs (BMX 3.0)

Entity profile generation runs via SQS-triggered profile worker Lambda.

**Trigger batch generation:**

```bash
bmx-api POST /entity/profiles/generate-all
# Returns: {"job_id": 42, "total_entities": 264, "status": "in_progress"}
```

**Check job progress:**

```bash
bmx-api GET /entity/profiles/generate-all/status/42
# Returns: {"job_id": 42, "status": "in_progress", "succeeded": 180, "failed": 2, ...}
```

**Cancel a stuck job:**

```bash
bmx-api POST /entity/profiles/generate-all/42/cancel
```

**View profile worker logs:**

```bash
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-profile-worker --since 10m
```

**Check profile generation queue depth:**

```bash
AWS_PROFILE=bmx-staging aws sqs get-queue-attributes \
  --queue-url https://sqs.us-west-2.amazonaws.com/ACCOUNT/bluemoxon-staging-profile-generation \
  --attribute-names ApproximateNumberOfMessages
```

### Portrait Sync (BMX 3.0)

Portrait sync fetches entity portraits from Wikidata/Wikimedia Commons, resizes to 400x400 JPEG, uploads to S3, and updates entity `image_url`.

**Trigger portrait sync for all entities:**

```bash
bmx-api POST /admin/portrait-sync
```

**Sync a single entity:**

```bash
bmx-api POST /admin/portrait-sync/author/5
```

**Troubleshooting portrait sync:**

- **Wikidata throttling (429/503):** The sync service has built-in rate limiting (1.5s between requests). If throttled, wait and retry.
- **Wrong portrait matched:** Portraits are matched using Wikidata SPARQL queries with name similarity scoring. Manual portrait upload via `PUT /entity/{type}/{id}/portrait` overrides automatic matching.
- **Portrait not found:** Not all entities have Wikidata entries. Use manual upload for missing portraits.

### Entity Enrichment Worker (BMX 3.0)

The enrichment worker populates entity metadata (birth/death years, founded/closed years, era) via Bedrock Haiku. Only updates NULL fields to avoid overwriting user-provided data. Enrichment runs inline within the API Lambda (triggered by SQS message to the main API), not as a standalone Lambda.

**View enrichment logs** (in the main API Lambda logs):

```bash
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-api --since 10m --filter-pattern "enrichment"
```

**Enrichment is triggered automatically** when new entities are created. It enriches:

- **Authors:** birth_year, death_year, era
- **Publishers:** founded_year, description
- **Binders:** founded_year, closed_year, full_name

### Social Circles Health Check (BMX 3.0)

The social circles feature has a dedicated health endpoint:

```bash
bmx-api GET /social-circles/health
```

Response includes node counts, edge counts, and query performance metrics. The graph build should complete in under 500ms; longer times indicate `degraded` status.

### Dead Letter Queue (DLQ)

Failed jobs go to DLQ for investigation:

```bash
# Check DLQ message count
AWS_PROFILE=bmx-staging aws sqs get-queue-attributes \
  --queue-url https://sqs.us-west-2.amazonaws.com/ACCOUNT/bluemoxon-staging-analysis-dlq \
  --attribute-names ApproximateNumberOfMessages
```

---

## Troubleshooting

### "Service Unavailable" (503) with Timeout

**Symptom:** Deep health times out, returns 503

**Root Cause:** Lambda cannot reach AWS services (VPC endpoint issue)

**Diagnosis:**

```bash
# If this works but deep health fails, it's VPC networking
bmx-api GET /books?limit=1
```

**Fix:** Check VPC endpoints exist:

- `com.amazonaws.us-west-2.secretsmanager` (Interface)
- `com.amazonaws.us-west-2.s3` (Gateway)
- `com.amazonaws.us-west-2.cognito-idp` (Interface)

### S3 Bucket Missing

**Symptom:** Deep health hangs on S3 check

**Diagnosis:**

```bash
AWS_PROFILE=bmx-staging aws s3 ls s3://bluemoxon-staging-images
```

**Fix:**

```bash
AWS_PROFILE=bmx-staging aws s3 mb s3://bluemoxon-staging-images --region us-west-2
```

### Cognito Login Issues

**"Invalid email or password"**

- Clear browser localStorage
- Retry with fresh session

**"Invalid code received for user" (MFA)**

- MFA token stale after pool recreation
- Reset MFA:

```bash
cd infra/terraform
POOL_ID=$(AWS_PROFILE=bmx-staging terraform output -raw cognito_user_pool_id)
AWS_PROFILE=bmx-staging aws cognito-idp admin-set-user-mfa-preference \
  --user-pool-id $POOL_ID \
  --username <USER_SUB> \
  --software-token-mfa-settings Enabled=false,PreferredMfa=false
```

**User not appearing**

- Run Cognito sync:

```bash
AWS_PROFILE=bmx-staging aws lambda invoke \
  --function-name bluemoxon-staging-db-sync \
  --payload '{"cognito_only": true}' \
  --cli-binary-format raw-in-base64-out \
  .tmp/sync.json
```

### Cold Start Authentication Failures

**Symptom:** Login fails on first attempt after Lambda cold start, succeeds on retry

**Root Cause:** Lambda cold start delays can cause auth token validation to timeout

**Built-in Mitigations:**

- **Frontend Auth Retry** - Automatically retries failed auth requests up to 3 times with exponential backoff
- **Cold Start Loading UX** - Shows loading spinner during initial app bootstrap
- **Preflight Validation** - API validates config on startup, fails fast if misconfigured

**User Experience:**

- Users see a loading screen during cold start (2-5 seconds)
- If auth fails, the app automatically retries before showing an error
- Most cold start delays are transparent to users

**Troubleshooting:**

```bash
# Check for auth-related errors in API logs
AWS_PROFILE=bmx-staging aws logs filter-log-events \
  --log-group-name /aws/lambda/bluemoxon-staging-api \
  --filter-pattern "AuthError"
```

### Bedrock Rate Limiting

**Symptom:** Analysis jobs fail with throttling errors

**Diagnosis:**

```bash
AWS_PROFILE=bmx-staging aws logs filter-log-events \
  --log-group-name /aws/lambda/bluemoxon-staging-analysis-worker \
  --filter-pattern "ThrottlingException"
```

**Mitigation:**

- Workers use exponential backoff with jitter
- Max 3 retries, base delay 5s
- Consider reducing concurrent analysis requests

### Scraper Rate Limiting

**Symptom:** eBay returns 429 or blocked page

**Diagnosis:** Check scraper logs for rate limiting patterns:

```bash
AWS_PROFILE=bmx-staging aws logs filter-log-events \
  --log-group-name /aws/lambda/bluemoxon-staging-scraper \
  --filter-pattern "Rate limited"
```

**Mitigation:**

- Wait before retrying (eBay blocks are temporary)
- Reduce concurrent scraper invocations
- Warmup keeps container hot to reduce cold starts

---

## Monitoring

### CloudWatch Dashboard

Dashboard: `bluemoxon-monitoring`

Key metrics:

- Lambda invocations and errors
- API Gateway latency and 4xx/5xx rates
- RDS connections and CPU
- SQS queue depth

### Alarms

| Alarm | Threshold | Action |
|-------|-----------|--------|
| API Errors | >10 in 5min | Investigate Lambda logs |
| Lambda Duration | >25s p95 | Check cold starts, dependencies |
| RDS Connections | >80% | Scale Aurora capacity |
| DLQ Messages | >0 | Investigate failed jobs |

---

## Emergency Procedures

### Rollback Lambda

See [ROLLBACK.md](ROLLBACK.md) for full procedures.

Quick rollback:

```bash
# List versions
AWS_PROFILE=bmx-prod aws lambda list-versions-by-function --function-name bluemoxon-api

# Rollback to previous version
AWS_PROFILE=bmx-prod aws lambda update-alias --function-name bluemoxon-api --name live --function-version <VERSION>
```

### Disable Feature

To disable a failing feature without rollback:

1. Add feature flag to environment
2. Update Lambda configuration:

```bash
AWS_PROFILE=bmx-prod aws lambda update-function-configuration \
  --function-name bluemoxon-api \
  --environment "Variables={DISABLE_FEATURE=true,...}"
```

### Database Recovery

See [ROLLBACK.md](ROLLBACK.md) for database recovery procedures.

---

## Analysis Troubleshooting

### Image Size Issues

When analysis jobs fail with "Input is too long" errors, the total base64 payload size exceeds Bedrock's input limit. This is caused by:

- Too many images
- Large image file sizes (high-quality JPEGs)

**Confirmed Working Thresholds:**

| Max Dimension | Max Images | Notes |
|---------------|------------|-------|
| 1600px | 12 | Works for low-quality JPEGs |
| 1200px | 16-18 | Works for moderate-quality JPEGs |
| 800px | 18-20 | **Reliable floor** - works regardless of JPEG quality |

**Root cause:** Base64 payload size matters more than pixel count. High-quality JPEGs (675KB-1.8MB per image) fail even at 1200px dimensions.

**Resolution workflow:**

1. Check image count: `bmx-api --prod GET "/books/{BOOK_ID}/images" | jq 'length'`

2. If > 12 images, resize to 800px:

Create temp directory:

```bash
mkdir -p .tmp/book{BOOK_ID}
```

Download images from S3:

```bash
AWS_PROFILE=bmx-prod aws s3 cp s3://bluemoxon-images/books/ .tmp/book{BOOK_ID}/ --recursive --exclude "*" --include "{BOOK_ID}_*.jpeg"
```

Resize to 800px max dimension:

```bash
sips --resampleHeightWidthMax 800 .tmp/book{BOOK_ID}/*.jpeg
```

Upload back to S3:

```bash
AWS_PROFILE=bmx-prod aws s3 cp .tmp/book{BOOK_ID}/ s3://bluemoxon-images/books/ --recursive --exclude "*" --include "{BOOK_ID}_*.jpeg"
```

1. Re-trigger analysis: `bmx-api --prod POST "/books/{BOOK_ID}/analysis/generate-async" '{"model": "opus"}'`

2. Verify success: `bmx-api --prod GET "/books/{BOOK_ID}" | jq '{id, analysis_issues}'`

### Stale Analysis Jobs

Jobs that show as "running" for more than 15 minutes are automatically marked as failed:

- On `GET /analysis/status` call
- On `POST /analysis/generate-async` re-trigger (allows immediate retry)

To check for stale jobs:

```bash
bmx-api --prod GET "/books/{BOOK_ID}/analysis/status"
```

---

## Staging Environment

### URLs

| Service | URL |
|---------|-----|
| Frontend | <https://staging.app.bluemoxon.com> |
| API | <https://staging.api.bluemoxon.com> |
| Health | <https://staging.api.bluemoxon.com/api/v1/health/deep> |

### AWS Profile

Always use `AWS_PROFILE=bmx-staging` for staging operations.

### E2E Browser Login Accounts

Three test accounts exist for browser access (Cognito users). Passwords stored in AWS Secrets Manager:

| Role | Email | Secret Name |
|------|-------|-------------|
| Admin | `e2e-test-admin@bluemoxon.com` | `bluemoxon-{env}/e2e-admin-password` |
| Editor | `e2e-test-editor@bluemoxon.com` | `bluemoxon-{env}/e2e-editor-password` |
| Viewer | `e2e-test-viewer@bluemoxon.com` | `bluemoxon-{env}/e2e-viewer-password` |

Fetch password:

```bash
AWS_PROFILE=bmx-staging aws secretsmanager get-secret-value \
  --secret-id bluemoxon-staging/e2e-admin-password \
  --query SecretString --output text
```

Defined in `frontend/e2e/global-setup.ts` (lines 38-52).

### Create/Reset Staging User

```bash
cd infra/terraform
POOL_ID=$(AWS_PROFILE=bmx-staging terraform output -raw cognito_user_pool_id)

# Create user
AWS_PROFILE=bmx-staging aws cognito-idp admin-create-user \
  --user-pool-id $POOL_ID \
  --username user@example.com \
  --user-attributes Name=email,Value=user@example.com Name=email_verified,Value=true

# Set password
AWS_PROFILE=bmx-staging aws cognito-idp admin-set-user-password \
  --user-pool-id $POOL_ID \
  --username user@example.com \
  --password 'YourPassword123@' \
  --permanent
```
