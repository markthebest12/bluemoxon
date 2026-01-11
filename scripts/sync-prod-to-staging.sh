#!/bin/bash
# =============================================================================
# Prod-to-Staging Sync Script
# =============================================================================
# Syncs production data to staging environment:
# - S3 images bucket
# - PostgreSQL database
#
# Pre-flight checks (via API - no direct DB access needed):
# - Verifies API versions match (git SHA comparison)
# - Verifies database health and schema validation status
# - Warns if mismatches detected, requires confirmation to proceed
#
# Usage:
#   ./scripts/sync-prod-to-staging.sh [OPTIONS]
#
# Options:
#   --images-only    Only sync S3 images
#   --db-only        Only sync database
#   --dry-run        Show what would be done without executing
#   --yes            Skip confirmation prompts
#   --skip-cache     Skip Redis cache flush after sync
#   -h, --help       Show this help message
#
# Prerequisites:
#   - AWS CLI configured with bmx-prod and bmx-staging profiles
#   - psql and pg_dump installed (brew install libpq)
#   - curl and jq for API version checks
#   - Network access to both RDS instances
#     NOTE: Prod (Aurora) and Staging (RDS) are in different accounts/VPCs.
#     For database sync to work, you need one of:
#     - VPC peering between accounts
#     - A bastion host with access to both databases
#     - AWS DMS for cross-account replication
#     The S3 sync works via local download/upload and doesn't require peering.
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

PROD_PROFILE="bmx-prod"
STAGING_PROFILE="bmx-staging"

# S3 Buckets
PROD_IMAGES_BUCKET="bluemoxon-images"
STAGING_IMAGES_BUCKET="bluemoxon-images-staging"

# Database
PROD_DB_SECRET="bluemoxon/db-credentials"
STAGING_DB_SECRET="bluemoxon-staging/database"

# Redis Cache (ElastiCache)
# Endpoint fetched dynamically from Terraform outputs
STAGING_REDIS_ENDPOINT=""
FLUSH_CACHE=true

# Flags
SYNC_IMAGES=true
SYNC_DB=true
DRY_RUN=false
AUTO_YES=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API Endpoints for version/migration checks
PROD_API="https://api.bluemoxon.com/api/v1"
STAGING_API="https://staging.api.bluemoxon.com/api/v1"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verify API versions and migration heads match before sync
verify_environments() {
    log_info "Verifying environment compatibility..."

    # Fetch API info (single call per environment, with timeout and error handling)
    PROD_INFO=$(curl -sf --connect-timeout 5 --max-time 30 "${PROD_API}/health/info" 2>/dev/null)
    if [ -z "$PROD_INFO" ]; then
        log_error "Failed to reach production API at ${PROD_API}/health/info"
        exit 1
    fi

    STAGING_INFO=$(curl -sf --connect-timeout 5 --max-time 30 "${STAGING_API}/health/info" 2>/dev/null)
    if [ -z "$STAGING_INFO" ]; then
        log_error "Failed to reach staging API at ${STAGING_API}/health/info"
        exit 1
    fi

    # Extract fields from cached responses
    PROD_VERSION=$(echo "$PROD_INFO" | jq -r '.version // "unknown"')
    STAGING_VERSION=$(echo "$STAGING_INFO" | jq -r '.version // "unknown"')
    PROD_SHA=$(echo "$PROD_INFO" | jq -r '.git_sha // "unknown"')
    STAGING_SHA=$(echo "$STAGING_INFO" | jq -r '.git_sha // "unknown"')

    echo "  Production:  version=$PROD_VERSION sha=$PROD_SHA"
    echo "  Staging:     version=$STAGING_VERSION sha=$STAGING_SHA"
    echo

    if [ "$PROD_SHA" != "$STAGING_SHA" ]; then
        log_warn "Git SHA mismatch detected!"
        log_warn "Production and staging are running different code versions."
        log_warn "This may cause issues if schema has changed between versions."
        echo
        if ! confirm "Continue anyway?"; then
            log_error "Aborting due to version mismatch."
            exit 1
        fi
    else
        log_success "API versions match"
    fi
}

# Verify database schema is validated via API health endpoint
verify_database_health() {
    log_info "Checking database health via API..."

    # Fetch deep health (single call per environment, with timeout and error handling)
    PROD_HEALTH=$(curl -sf --connect-timeout 5 --max-time 30 "${PROD_API}/health/deep" 2>/dev/null)
    if [ -z "$PROD_HEALTH" ]; then
        log_error "Failed to reach production API at ${PROD_API}/health/deep"
        exit 1
    fi

    STAGING_HEALTH=$(curl -sf --connect-timeout 5 --max-time 30 "${STAGING_API}/health/deep" 2>/dev/null)
    if [ -z "$STAGING_HEALTH" ]; then
        log_error "Failed to reach staging API at ${STAGING_API}/health/deep"
        exit 1
    fi

    # Extract fields from cached responses
    PROD_DB_STATUS=$(echo "$PROD_HEALTH" | jq -r '.checks.database.status // "unknown"')
    PROD_SCHEMA_OK=$(echo "$PROD_HEALTH" | jq -r '.checks.database.schema_validated // false')
    PROD_BOOK_COUNT=$(echo "$PROD_HEALTH" | jq -r '.checks.database.book_count // 0')

    STAGING_DB_STATUS=$(echo "$STAGING_HEALTH" | jq -r '.checks.database.status // "unknown"')
    STAGING_SCHEMA_OK=$(echo "$STAGING_HEALTH" | jq -r '.checks.database.schema_validated // false')
    STAGING_BOOK_COUNT=$(echo "$STAGING_HEALTH" | jq -r '.checks.database.book_count // 0')

    echo "  Production:  status=$PROD_DB_STATUS schema_validated=$PROD_SCHEMA_OK books=$PROD_BOOK_COUNT"
    echo "  Staging:     status=$STAGING_DB_STATUS schema_validated=$STAGING_SCHEMA_OK books=$STAGING_BOOK_COUNT"
    echo

    if [ "$PROD_DB_STATUS" != "healthy" ]; then
        log_error "Production database is not healthy: $PROD_DB_STATUS"
        exit 1
    fi

    if [ "$PROD_SCHEMA_OK" != "true" ]; then
        log_error "Production schema validation failed"
        exit 1
    fi

    if [ "$STAGING_DB_STATUS" != "healthy" ]; then
        log_warn "Staging database is not healthy: $STAGING_DB_STATUS"
        log_warn "This may be expected if staging is empty or has stale data."
        echo
        if ! confirm "Continue anyway?"; then
            log_error "Aborting due to staging database issue."
            exit 1
        fi
    else
        log_success "Both databases are healthy"
    fi
}

# Fetch staging Redis endpoint from Terraform outputs
fetch_redis_endpoint() {
    log_info "Fetching staging Redis endpoint..."

    # Use subshell to avoid directory change affecting the main script
    STAGING_REDIS_ENDPOINT=$(
        cd infra/terraform 2>/dev/null || exit 1
        AWS_PROFILE="$STAGING_PROFILE" terraform output -raw redis_url 2>/dev/null
    ) || true

    if [ -z "$STAGING_REDIS_ENDPOINT" ]; then
        log_warn "Could not fetch Redis endpoint from Terraform"
        log_warn "Cache flush will be skipped"
        FLUSH_CACHE=false
        return 0
    fi

    log_info "  Endpoint: ${STAGING_REDIS_ENDPOINT:0:50}..."
}

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

    # Validate parsed values
    if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ]; then
        log_warn "Could not parse Redis endpoint: $STAGING_REDIS_ENDPOINT"
        return 0
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would flush Redis cache at $REDIS_HOST:$REDIS_PORT"
        return 0
    fi

    # Execute FLUSHALL with TLS (10 second timeout to prevent hanging)
    if timeout 10 redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls FLUSHALL; then
        log_success "Redis cache flushed successfully"
    else
        log_warn "Failed to flush Redis cache - dashboard may show stale data"
    fi
}

show_help() {
    head -30 "$0" | grep -E '^#' | tail -n +2 | sed 's/^# //' | sed 's/^#//'
    exit 0
}

confirm() {
    if [ "$AUTO_YES" = true ]; then
        return 0
    fi

    local prompt="$1"
    echo -e "${YELLOW}$prompt${NC}"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

get_secret() {
    local secret_name="$1"
    local profile_arg=""

    if [ -n "${2:-}" ]; then
        profile_arg="--profile $2"
    fi

    aws secretsmanager get-secret-value \
        $profile_arg \
        --secret-id "$secret_name" \
        --query 'SecretString' \
        --output text
}

# -----------------------------------------------------------------------------
# Parse Arguments
# -----------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case $1 in
        --images-only)
            SYNC_IMAGES=true
            SYNC_DB=false
            shift
            ;;
        --db-only)
            SYNC_IMAGES=false
            SYNC_DB=true
            shift
            ;;
        --skip-cache)
            FLUSH_CACHE=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --yes|-y)
            AUTO_YES=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# -----------------------------------------------------------------------------
# Main Script
# -----------------------------------------------------------------------------

echo "=============================================="
echo "  BlueMoxon Prod → Staging Sync"
echo "=============================================="
echo

if [ "$DRY_RUN" = true ]; then
    log_warn "DRY RUN MODE - No changes will be made"
    echo
fi

# Show what will be synced
echo "Sync configuration:"
echo "  Images: $([ "$SYNC_IMAGES" = true ] && echo "YES" || echo "NO")"
echo "  Database: $([ "$SYNC_DB" = true ] && echo "YES" || echo "NO")"
echo

# -----------------------------------------------------------------------------
# Pre-flight Verification
# -----------------------------------------------------------------------------

verify_environments
verify_database_health

# -----------------------------------------------------------------------------
# S3 Images Sync
# -----------------------------------------------------------------------------

if [ "$SYNC_IMAGES" = true ]; then
    log_info "Syncing S3 images bucket..."
    log_info "  From: s3://${PROD_IMAGES_BUCKET}"
    log_info "  To:   s3://${STAGING_IMAGES_BUCKET}"

    # Get bucket sizes for comparison
    log_info "Checking bucket sizes..."

    PROD_SIZE=$(aws --profile "$PROD_PROFILE" s3 ls "s3://${PROD_IMAGES_BUCKET}" --recursive --summarize 2>/dev/null | grep "Total Size" | awk '{print $3, $4}' || echo "unknown")
    STAGING_SIZE=$(aws --profile "$STAGING_PROFILE" s3 ls "s3://${STAGING_IMAGES_BUCKET}" --recursive --summarize 2>/dev/null | grep "Total Size" | awk '{print $3, $4}' || echo "unknown")

    echo "  Production size: $PROD_SIZE"
    echo "  Staging size: $STAGING_SIZE"
    echo

    if ! confirm "This will overwrite staging images with production data."; then
        log_info "Skipping images sync."
    else
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY RUN] Would:"
            log_info "  1. Download all objects from s3://${PROD_IMAGES_BUCKET}"
            log_info "  2. Upload to s3://${STAGING_IMAGES_BUCKET} (staging account)"
            # Count prod objects
            PROD_COUNT=$(aws --profile "$PROD_PROFILE" s3 ls "s3://${PROD_IMAGES_BUCKET}" --recursive 2>/dev/null | wc -l | tr -d ' ')
            log_info "  Total objects to sync: $PROD_COUNT"
        else
            log_info "Starting S3 sync..."

            # Sync from prod to staging using cross-account sync
            # First download to temp, then upload to staging
            TEMP_DIR=$(mktemp -d)
            trap "rm -rf $TEMP_DIR" EXIT

            log_info "Downloading from production..."
            aws --profile "$PROD_PROFILE" s3 sync "s3://${PROD_IMAGES_BUCKET}" "$TEMP_DIR" --quiet

            log_info "Uploading to staging..."
            aws --profile "$STAGING_PROFILE" s3 sync "$TEMP_DIR" "s3://${STAGING_IMAGES_BUCKET}" --quiet

            log_success "S3 images sync complete!"
        fi
    fi
    echo
fi

# -----------------------------------------------------------------------------
# Database Sync
# -----------------------------------------------------------------------------

if [ "$SYNC_DB" = true ]; then
    log_info "Syncing database..."

    # Check for psql and pg_dump (try common homebrew paths)
    PSQL_CMD="psql"
    PG_DUMP_CMD="pg_dump"

    if ! command -v psql &> /dev/null; then
        if [ -x "/opt/homebrew/opt/libpq/bin/psql" ]; then
            PSQL_CMD="/opt/homebrew/opt/libpq/bin/psql"
            PG_DUMP_CMD="/opt/homebrew/opt/libpq/bin/pg_dump"
        else
            log_error "psql and pg_dump are required. Install with: brew install libpq"
            log_error "Then add to PATH: export PATH=\"/opt/homebrew/opt/libpq/bin:\$PATH\""
            exit 1
        fi
    fi

    # Get database credentials from Secrets Manager
    log_info "Fetching database credentials..."

    PROD_CREDS=$(get_secret "$PROD_DB_SECRET" "$PROD_PROFILE")
    STAGING_CREDS=$(get_secret "$STAGING_DB_SECRET" "$STAGING_PROFILE")

    # Parse credentials (handle both 'database' and 'dbname' keys)
    PROD_HOST=$(echo "$PROD_CREDS" | jq -r '.host')
    PROD_PORT=$(echo "$PROD_CREDS" | jq -r '.port // 5432')
    PROD_USER=$(echo "$PROD_CREDS" | jq -r '.username')
    PROD_PASS=$(echo "$PROD_CREDS" | jq -r '.password')
    PROD_DB=$(echo "$PROD_CREDS" | jq -r '.database // .dbname // "bluemoxon"')

    STAGING_HOST=$(echo "$STAGING_CREDS" | jq -r '.host')
    STAGING_PORT=$(echo "$STAGING_CREDS" | jq -r '.port // 5432')
    STAGING_USER=$(echo "$STAGING_CREDS" | jq -r '.username')
    STAGING_PASS=$(echo "$STAGING_CREDS" | jq -r '.password')
    STAGING_DB=$(echo "$STAGING_CREDS" | jq -r '.database // .dbname // "bluemoxon"')

    log_info "Source database:"
    log_info "  Host: $PROD_HOST"
    log_info "  Database: $PROD_DB"
    log_info "  User: $PROD_USER"
    echo
    log_info "Target database:"
    log_info "  Host: $STAGING_HOST"
    log_info "  Database: $STAGING_DB"
    log_info "  User: $STAGING_USER"
    echo

    log_warn "WARNING: This will REPLACE ALL DATA in the staging database!"

    if ! confirm "Are you sure you want to continue?"; then
        log_info "Skipping database sync."
    else
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY RUN] Would:"
            log_info "  1. Dump production database to temp file"
            log_info "  2. Drop and recreate staging database"
            log_info "  3. Restore dump to staging"
        else
            DUMP_FILE=$(mktemp).sql
            trap "rm -f $DUMP_FILE" EXIT

            log_info "Dumping production database..."
            PGPASSWORD="$PROD_PASS" "$PG_DUMP_CMD" \
                -h "$PROD_HOST" \
                -p "$PROD_PORT" \
                -U "$PROD_USER" \
                -d "$PROD_DB" \
                --no-owner \
                --no-acl \
                -F p \
                > "$DUMP_FILE"

            DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
            log_info "Dump complete: $DUMP_SIZE"

            log_info "Restoring to staging database..."

            # Drop existing tables and restore
            PGPASSWORD="$STAGING_PASS" "$PSQL_CMD" \
                -h "$STAGING_HOST" \
                -p "$STAGING_PORT" \
                -U "$STAGING_USER" \
                -d "$STAGING_DB" \
                -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" \
                2>/dev/null || true

            PGPASSWORD="$STAGING_PASS" "$PSQL_CMD" \
                -h "$STAGING_HOST" \
                -p "$STAGING_PORT" \
                -U "$STAGING_USER" \
                -d "$STAGING_DB" \
                -f "$DUMP_FILE" \
                --quiet \
                2>/dev/null

            log_success "Database sync complete!"

            # Show table counts
            log_info "Staging database table counts:"
            PGPASSWORD="$STAGING_PASS" "$PSQL_CMD" \
                -h "$STAGING_HOST" \
                -p "$STAGING_PORT" \
                -U "$STAGING_USER" \
                -d "$STAGING_DB" \
                -c "SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;" \
                2>/dev/null || true
        fi
    fi
fi

echo
echo "=============================================="
if [ "$DRY_RUN" = true ]; then
    log_info "DRY RUN complete - no changes were made"
else
    log_success "Sync complete!"
fi
echo "=============================================="
