# Sync Script Redis Cache Flush Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Redis cache flush to prod-staging sync script to prevent stale data after database sync.

**Architecture:** After database sync completes, connect to staging ElastiCache using redis-cli with TLS and execute FLUSHALL. Get endpoint from Terraform outputs. Handle dry-run mode and graceful failures.

**Tech Stack:** Bash, redis-cli, AWS CLI, Terraform

**Issue:** #1053

---

## Prerequisites Check

Before starting:
- [ ] redis-cli installed (`brew install redis`)
- [ ] AWS profiles configured (`bmx-staging`)
- [ ] VPC access to staging ElastiCache (same as DB access)

---

## Task 1: Add Redis Configuration to Script

**Files:**
- Modify: `scripts/sync-prod-to-staging.sh:43-69` (Configuration section)

**Step 1: Add Redis configuration variables**

Add after line 52 (Database section):

```bash
# Redis Cache (ElastiCache)
# Endpoint fetched dynamically from Terraform outputs
STAGING_REDIS_ENDPOINT=""
FLUSH_CACHE=true
```

**Step 2: Add --skip-cache flag to argument parser**

Add new case in the argument parser (after --db-only case around line 206):

```bash
        --skip-cache)
            FLUSH_CACHE=false
            shift
            ;;
```

**Step 3: Update help text**

Add to header comment (around line 21):

```bash
#   --skip-cache     Skip Redis cache flush after sync
```

**Step 4: Commit**

```bash
git add scripts/sync-prod-to-staging.sh
git commit -m "feat(sync): Add Redis cache configuration and --skip-cache flag (#1053)"
```

---

## Task 2: Add Redis Endpoint Fetch Function

**Files:**
- Modify: `scripts/sync-prod-to-staging.sh` (Helper Functions section)

**Step 1: Add function to fetch Redis endpoint from Terraform**

Add after `verify_database_health()` function (around line 183):

```bash
# Fetch staging Redis endpoint from Terraform outputs
fetch_redis_endpoint() {
    log_info "Fetching staging Redis endpoint..."

    # Get endpoint from Terraform output
    cd infra/terraform
    STAGING_REDIS_ENDPOINT=$(AWS_PROFILE="$STAGING_PROFILE" terraform output -raw redis_url 2>/dev/null)
    cd - > /dev/null

    if [ -z "$STAGING_REDIS_ENDPOINT" ]; then
        log_warn "Could not fetch Redis endpoint from Terraform"
        log_warn "Cache flush will be skipped"
        FLUSH_CACHE=false
        return 0
    fi

    log_info "  Endpoint: ${STAGING_REDIS_ENDPOINT:0:50}..."
}
```

**Step 2: Commit**

```bash
git add scripts/sync-prod-to-staging.sh
git commit -m "feat(sync): Add Redis endpoint fetch from Terraform (#1053)"
```

---

## Task 3: Add Cache Flush Function

**Files:**
- Modify: `scripts/sync-prod-to-staging.sh` (Helper Functions section)

**Step 1: Add function to flush Redis cache**

Add after `fetch_redis_endpoint()`:

```bash
# Flush staging Redis cache
flush_redis_cache() {
    if [ "$FLUSH_CACHE" != true ]; then
        log_info "Skipping cache flush (--skip-cache)"
        return 0
    fi

    if [ -z "$STAGING_REDIS_ENDPOINT" ]; then
        log_warn "No Redis endpoint available, skipping cache flush"
        return 0
    fi

    log_info "Flushing staging Redis cache..."

    # Check for redis-cli
    if ! command -v redis-cli &> /dev/null; then
        log_warn "redis-cli not found. Install with: brew install redis"
        log_warn "Cache flush skipped - dashboard may show stale data for up to 5 minutes"
        return 0
    fi

    # Parse endpoint (format: rediss://host:port)
    REDIS_HOST=$(echo "$STAGING_REDIS_ENDPOINT" | sed 's|rediss://||' | cut -d: -f1)
    REDIS_PORT=$(echo "$STAGING_REDIS_ENDPOINT" | sed 's|rediss://||' | cut -d: -f2)

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would flush Redis cache at $REDIS_HOST:$REDIS_PORT"
        return 0
    fi

    # Execute FLUSHALL with TLS
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls FLUSHALL; then
        log_success "Redis cache flushed successfully"
    else
        log_warn "Failed to flush Redis cache - dashboard may show stale data"
    fi
}
```

**Step 2: Commit**

```bash
git add scripts/sync-prod-to-staging.sh
git commit -m "feat(sync): Add Redis cache flush function (#1053)"
```

---

## Task 4: Integrate Cache Flush into Sync Flow

**Files:**
- Modify: `scripts/sync-prod-to-staging.sh` (Main Script section)

**Step 1: Call fetch_redis_endpoint in pre-flight**

Add after `verify_database_health` call (around line 264):

```bash
# Fetch Redis endpoint for cache flush
if [ "$FLUSH_CACHE" = true ]; then
    fetch_redis_endpoint
fi
```

**Step 2: Call flush_redis_cache after database sync**

Add after database sync completion (around line 427, after `log_success "Database sync complete!"`):

```bash
            # Flush Redis cache after DB sync
            flush_redis_cache
```

**Step 3: Update dry-run output**

In the dry-run section for database (around line 375), add:

```bash
            if [ "$FLUSH_CACHE" = true ] && [ -n "$STAGING_REDIS_ENDPOINT" ]; then
                log_info "  4. Flush staging Redis cache"
            fi
```

**Step 4: Commit**

```bash
git add scripts/sync-prod-to-staging.sh
git commit -m "feat(sync): Integrate Redis cache flush into sync flow (#1053)"
```

---

## Task 5: Update Prerequisites Documentation

**Files:**
- Modify: `scripts/sync-prod-to-staging.sh` (Header comments)

**Step 1: Add redis-cli to prerequisites**

Update the Prerequisites section (around line 25-34):

```bash
# Prerequisites:
#   - AWS CLI configured with bmx-prod and bmx-staging profiles
#   - psql and pg_dump installed (brew install libpq)
#   - redis-cli for cache flush (brew install redis) - optional but recommended
#   - curl and jq for API version checks
#   - Terraform initialized in infra/terraform/
#   - Network access to both RDS instances and ElastiCache
```

**Step 2: Commit**

```bash
git add scripts/sync-prod-to-staging.sh
git commit -m "docs(sync): Update prerequisites for Redis cache flush (#1053)"
```

---

## Task 6: Test Dry Run

**Step 1: Install redis-cli if not present**

```bash
brew install redis
```

**Step 2: Run dry-run test**

```bash
./scripts/sync-prod-to-staging.sh --db-only --dry-run --yes
```

**Expected output includes:**
- "Fetching staging Redis endpoint..."
- "Endpoint: rediss://..."
- "[DRY RUN] Would flush Redis cache at ..."

**Step 3: Run with --skip-cache flag**

```bash
./scripts/sync-prod-to-staging.sh --db-only --dry-run --yes --skip-cache
```

**Expected output includes:**
- "Skipping cache flush (--skip-cache)"

---

## Task 7: Create PR to Staging

**Step 1: Push branch and create PR**

```bash
git push -u origin feat/sync-redis-flush
gh pr create --base staging --title "feat(sync): Add Redis cache flush after database sync (#1053)" --body "## Summary
- Adds Redis cache flush to sync script after DB sync completes
- Prevents stale dashboard data in staging after sync
- Gracefully handles missing redis-cli or unreachable endpoint

## Changes
- Add --skip-cache flag option
- Fetch Redis endpoint from Terraform outputs
- Execute FLUSHALL after database sync
- Update prerequisites documentation

## Test Plan
- [x] Dry-run shows cache flush step
- [x] --skip-cache flag works
- [ ] Actual sync flushes cache (will test after merge)

Closes #1053"
```

---

## Summary

| Task | Description | Commit Message |
|------|-------------|----------------|
| 1 | Add config and --skip-cache flag | `feat(sync): Add Redis cache configuration...` |
| 2 | Add endpoint fetch function | `feat(sync): Add Redis endpoint fetch...` |
| 3 | Add cache flush function | `feat(sync): Add Redis cache flush function...` |
| 4 | Integrate into sync flow | `feat(sync): Integrate Redis cache flush...` |
| 5 | Update docs | `docs(sync): Update prerequisites...` |
| 6 | Test dry run | (no commit) |
| 7 | Create PR | (PR creation) |
