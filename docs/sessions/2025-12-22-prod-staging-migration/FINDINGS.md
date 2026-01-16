# Prod-to-Staging Migration Review

**Date:** 2025-12-22
**Issue:** #568
**Script:** `scripts/sync-prod-to-staging.sh`

## Critical Issues Found

### 1. AWS Profile Mismatch (MUST FIX)

The script uses incorrect AWS profile names:

| Setting | Script Value | Actual Value |
|---------|--------------|--------------|
| `PROD_PROFILE` | `""` (default) | `bmx-prod` |
| `STAGING_PROFILE` | `"staging"` | `bmx-staging` |

**Fix Required:**

```bash
PROD_PROFILE="bmx-prod"
STAGING_PROFILE="bmx-staging"
```

### 2. S3 Bucket Names - CORRECT

| Bucket | Script | Actual |
|--------|--------|--------|
| Prod Images | `bluemoxon-images` | `bluemoxon-images` |
| Staging Images | `bluemoxon-images-staging` | `bluemoxon-images-staging` |

### 3. Secret Names - CORRECT

| Secret | Script | Actual |
|--------|--------|--------|
| Prod DB | `bluemoxon/db-credentials` | `bluemoxon/db-credentials` |
| Staging DB | `bluemoxon-staging/database` | `bluemoxon-staging/database` |

## Schema Changes Since Last Sync

20+ Alembic migrations created since Nov 1, including:

| Migration | Description | Date |
|-----------|-------------|------|
| `s2345678klmn` | Add author tier | Dec 21 |
| `r1234567ghij` | Add extraction status | Dec 19 |
| `q0123456cdef` | Add provenance, first edition | Dec 19 |
| `p8901234yzab` | Add tracking status fields | Dec 18 |
| `o7890123wxyz` | Add FMV notes and confidence | Dec 17 |
| `n6789012uvwx` | Add eval runbook jobs | Dec 17 |
| `m5678901qrst` | Add eval runbook | Dec 17 |
| ... | (15+ more) | ... |

**Post-sync action required:** Run migrations on staging via API.

## Alternative Sync Methods

### Option A: Script-based (local)

```bash
./scripts/sync-prod-to-staging.sh
```

- Requires network access to both RDS instances
- Downloads/uploads S3 via local machine
- More control over process

### Option B: Lambda-based (recommended for DB)

```bash
AWS_PROFILE=bmx-staging aws lambda invoke \
  --function-name bluemoxon-staging-db-sync \
  --payload '{}' \
  .tmp/sync-response.json
```

- Already deployed: `bluemoxon-staging-db-sync`
- Runs in VPC with database access
- 300s timeout

## Recommended Approach

1. **Fix script AWS profiles** (required for script-based sync)
2. **Sync S3 images** via script (cross-account, works fine)
3. **Sync database** via Lambda (avoids VPC connectivity issues)
4. **Run migrations** on staging after sync
5. **Verify** staging health

## Dry Run Results (2025-12-22)

After fixing AWS profiles, dry run succeeded:

```
S3 Images:
  Production:  1.7 GB, 4709 objects
  Staging:     1.6 GB (needs sync)

Database:
  Prod host:    bluemoxon-cluster.cluster-cp4c0cuuyq2m.us-west-2.rds.amazonaws.com
  Staging host: bluemoxon-staging-db.cjoqsygykc5c.us-west-2.rds.amazonaws.com
```

**Script is ready to run.**

## Sync Results (2025-12-22)

### S3 Images

- 4,709 objects synced successfully
- Prod: 1.7 GB → Staging: synced

### Database

| Status | Tables |
|--------|--------|
| Synced (12) | alembic_version, analysis_jobs, api_keys, authors, binders, book_analyses, book_images, books, eval_price_history, eval_runbook_jobs, publishers, users |
| Failed (2) | admin_config (seeded by migration), eval_runbooks (JSONB type mismatch) |

**Total rows synced:** 2,452

### Known Issues

1. **Lambda JSONB bug**: `backend/lambdas/db_sync/handler.py` doesn't properly cast JSONB columns when copying from prod. Affects:
   - `admin_config.value` (numeric → jsonb)
   - `eval_runbooks.condition_positives` (text[] → jsonb)

2. **Workaround**: admin_config is seeded by migrations. eval_runbooks can be regenerated or manually synced.

3. **Lambda prod connection issue**: The db-sync Lambda's `raw_sql` queries to prod return empty for `eval_runbooks` table, even though prod API confirms data exists (e.g., id=181 for book 533). The Lambda connects to the correct host/db but queries return 0 rows. May be a VPC routing or credentials issue introduced when we switched from PROD_SECRET_ARN to direct credentials.

### Version Mismatch (Expected)

Staging (6575f61) is ahead of prod (a9fd309) with dependency updates and fixes. This is normal - staging gets changes first before promotion to prod.

### Post-Sync Verification

- Staging health: HEALTHY
- Books count: 153 (matches prod)

## Verification Steps

```bash
# After sync, run migrations
curl -X POST https://staging.api.bluemoxon.com/api/v1/health/migrate

# Verify health
curl -s https://staging.api.bluemoxon.com/api/v1/health/deep | jq

# Verify data
bmx-api GET '/books?limit=5' | jq '.total'
```
