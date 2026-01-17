#!/bin/bash
# =============================================================================
# Redeploy Scraper Lambda
# =============================================================================
# Forces the scraper Lambda to redeploy, which gets a new IP address.
# Use this when eBay blocks the current Lambda IP.
#
# Usage:
#   ./scripts/redeploy-scraper.sh staging
#   ./scripts/redeploy-scraper.sh prod
#
# What it does:
#   Updates a FORCE_REDEPLOY environment variable with current timestamp,
#   which forces AWS to create a new Lambda instance with a new IP.
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Validate arguments
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <staging|prod>"
    exit 1
fi

ENV="$1"

case "$ENV" in
    staging)
        FUNCTION_NAME="bluemoxon-staging-scraper"
        AWS_PROFILE="bmx-staging"
        ;;
    prod)
        FUNCTION_NAME="bluemoxon-prod-scraper"
        AWS_PROFILE="bmx-prod"
        ;;
    *)
        log_error "Invalid environment: $ENV (must be 'staging' or 'prod')"
        exit 1
        ;;
esac

log_info "Redeploying $FUNCTION_NAME to get new IP..."

# Get current environment variables
log_info "Fetching current configuration..."
CURRENT_ENV=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --query 'Environment.Variables' \
    --output json 2>/dev/null || echo '{}')

if [[ "$CURRENT_ENV" == "null" || "$CURRENT_ENV" == "{}" ]]; then
    CURRENT_ENV='{}'
fi

# Add/update FORCE_REDEPLOY with current timestamp
TIMESTAMP=$(date +%Y%m%d%H%M%S)
NEW_ENV=$(echo "$CURRENT_ENV" | jq --arg ts "$TIMESTAMP" '. + {"FORCE_REDEPLOY": $ts}')

log_info "Updating Lambda configuration with FORCE_REDEPLOY=$TIMESTAMP..."

# Write environment to temp file (AWS CLI needs specific JSON format)
ENV_FILE=$(mktemp)
echo "{\"Variables\": $NEW_ENV}" > "$ENV_FILE"

# Update the function configuration
AWS_PROFILE=$AWS_PROFILE aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --environment "file://$ENV_FILE" \
    --output text \
    --query 'LastUpdateStatus' > /dev/null

rm -f "$ENV_FILE"

# Wait for update to complete
log_info "Waiting for update to complete..."
AWS_PROFILE=$AWS_PROFILE aws lambda wait function-updated \
    --function-name "$FUNCTION_NAME"

# Verify the update
LAST_MODIFIED=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --query 'LastModified' \
    --output text)

log_success "Scraper Lambda redeployed successfully!"
log_info "Function: $FUNCTION_NAME"
log_info "Last modified: $LAST_MODIFIED"
log_info "New instances will have a fresh IP address."

# Optional: invoke a test to warm up the new instance
read -p "Invoke a warmup request now? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Sending warmup request..."
    AWS_PROFILE=$AWS_PROFILE aws lambda invoke \
        --function-name "$FUNCTION_NAME" \
        --payload '{"warmup": true}' \
        --cli-binary-format raw-in-base64-out \
        /dev/null > /dev/null 2>&1
    log_success "Warmup complete - new instance is ready."
fi
