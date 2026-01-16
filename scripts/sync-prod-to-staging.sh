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
#   -h, --help       Show this help message
#
# Prerequisites:
#   - AWS CLI configured with bmx-prod and bmx-staging profiles
#   - curl and jq for API version checks
#
# Database sync uses Lambda (runs inside VPC with access to both databases).
# S3 sync uses local download/upload (works across accounts).
#
# Post-sync behavior:
#   - Dashboard stats may show stale data for up to 5 minutes (Redis cache TTL)
#   - Cache self-corrects without intervention
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
        # Exclude non-image prefixes:
        # - lambda/, deploy/ - Lambda deployment packages (staging has its own)
        # - data-import/ - One-time import files
        # - listings/ - Transient scraper staging area (staging can scrape fresh)
        S3_EXCLUDES="--exclude lambda/* --exclude deploy/* --exclude data-import/* --exclude listings/*"

        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY RUN] Would:"
            log_info "  1. Download book images from s3://${PROD_IMAGES_BUCKET}"
            log_info "  2. Upload to s3://${STAGING_IMAGES_BUCKET} (staging account)"
            log_info "  Excluding: lambda/, deploy/, data-import/, listings/"
            log_info "  Note: No --delete flag - staging keeps orphaned files"
            # Count prod objects (excluding the same prefixes)
            PROD_COUNT=$(aws --profile "$PROD_PROFILE" s3 ls "s3://${PROD_IMAGES_BUCKET}" --recursive 2>/dev/null | grep -v -E " (lambda|deploy|data-import|listings)/" | wc -l | tr -d ' ')
            log_info "  Total objects to sync: ~$PROD_COUNT"
        else
            log_info "Starting S3 sync..."
            log_info "Excluding: lambda/, deploy/, data-import/, listings/"

            # Sync from prod to staging using cross-account sync
            # First download to temp, then upload to staging
            TEMP_DIR=$(mktemp -d)
            trap "rm -rf $TEMP_DIR" EXIT

            log_info "Downloading from production..."
            aws --profile "$PROD_PROFILE" s3 sync "s3://${PROD_IMAGES_BUCKET}" "$TEMP_DIR" $S3_EXCLUDES --quiet

            log_info "Uploading to staging..."
            aws --profile "$STAGING_PROFILE" s3 sync "$TEMP_DIR" "s3://${STAGING_IMAGES_BUCKET}" --quiet

            log_success "S3 images sync complete!"
        fi
    fi
    echo
fi

# -----------------------------------------------------------------------------
# Database Sync (via Lambda)
# -----------------------------------------------------------------------------

if [ "$SYNC_DB" = true ]; then
    log_info "Syncing database via Lambda..."
    log_warn "WARNING: This will REPLACE ALL DATA in the staging database!"

    if ! confirm "Are you sure you want to continue?"; then
        log_info "Skipping database sync."
    else
        if [ "$DRY_RUN" = true ]; then
            log_info "[DRY RUN] Would invoke Lambda: bluemoxon-staging-db-sync"
        else
            RESPONSE_FILE=".tmp/sync-response-$$.json"
            mkdir -p .tmp

            log_info "Invoking Lambda function..."
            aws lambda invoke \
                --function-name bluemoxon-staging-db-sync \
                --profile "$STAGING_PROFILE" \
                --payload '{}' \
                "$RESPONSE_FILE" \
                --cli-read-timeout 300 \
                > /dev/null

            # Parse response
            BODY=$(cat "$RESPONSE_FILE" | jq -r '.body // .' 2>/dev/null)

            if echo "$BODY" | jq -e '.error' > /dev/null 2>&1; then
                log_warn "Sync completed with some failures"
            else
                log_success "Database sync complete!"
            fi

            # Show results
            TABLES_SYNCED=$(echo "$BODY" | jq -r '.results.tables_synced // [] | length' 2>/dev/null || echo "?")
            TOTAL_ROWS=$(echo "$BODY" | jq -r '.results.total_rows // "?"' 2>/dev/null)
            TABLES_FAILED=$(echo "$BODY" | jq -r '.results.tables_failed // [] | length' 2>/dev/null || echo "0")

            log_info "Results:"
            log_info "  Tables synced: $TABLES_SYNCED"
            log_info "  Total rows: $TOTAL_ROWS"

            if [ "$TABLES_FAILED" != "0" ]; then
                log_warn "  Tables failed: $TABLES_FAILED"
                echo "$BODY" | jq -r '.results.tables_failed[] | "    - \(.table): \(.error | split("\n")[0])"' 2>/dev/null || true
            fi

            rm -f "$RESPONSE_FILE"
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
