#!/bin/bash
# =============================================================================
# Prod-to-Staging Sync Script
# =============================================================================
# Syncs production data to staging environment:
# - S3 images bucket
# - PostgreSQL database
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
#   - AWS CLI configured with both default (prod) and staging profiles
#   - psql and pg_dump installed (brew install libpq)
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

PROD_PROFILE=""  # Default profile
STAGING_PROFILE="staging"

# S3 Buckets
PROD_IMAGES_BUCKET="bluemoxon-images"
STAGING_IMAGES_BUCKET="bluemoxon-images-staging"

# Database
PROD_DB_SECRET="bluemoxon/db-credentials"
STAGING_DB_SECRET="bluemoxon-staging/database"

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
# S3 Images Sync
# -----------------------------------------------------------------------------

if [ "$SYNC_IMAGES" = true ]; then
    log_info "Syncing S3 images bucket..."
    log_info "  From: s3://${PROD_IMAGES_BUCKET}"
    log_info "  To:   s3://${STAGING_IMAGES_BUCKET}"

    # Get bucket sizes for comparison
    log_info "Checking bucket sizes..."

    PROD_SIZE=$(aws s3 ls "s3://${PROD_IMAGES_BUCKET}" --recursive --summarize 2>/dev/null | grep "Total Size" | awk '{print $3, $4}' || echo "unknown")
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
            PROD_COUNT=$(aws s3 ls "s3://${PROD_IMAGES_BUCKET}" --recursive 2>/dev/null | wc -l | tr -d ' ')
            log_info "  Total objects to sync: $PROD_COUNT"
        else
            log_info "Starting S3 sync..."

            # Sync from prod to staging using cross-account sync
            # First download to temp, then upload to staging
            TEMP_DIR=$(mktemp -d)
            trap "rm -rf $TEMP_DIR" EXIT

            log_info "Downloading from production..."
            aws s3 sync "s3://${PROD_IMAGES_BUCKET}" "$TEMP_DIR" --quiet

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

    PROD_CREDS=$(get_secret "$PROD_DB_SECRET" "")
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
