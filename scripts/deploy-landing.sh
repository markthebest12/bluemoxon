#!/bin/bash
#
# Deploy the BlueMoxon landing/docs site to S3
#
# Usage: ./scripts/deploy-landing.sh
#
# This script:
# 1. Syncs HTML files from site/ to S3
# 2. Syncs screenshots from docs/screenshots/ to S3
# 3. Invalidates CloudFront cache
#

set -e

# Configuration
BUCKET="bluemoxon-landing"
DISTRIBUTION_ID="ES60BQB34DNYS"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Deploying BlueMoxon landing site...${NC}"

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Run: export AWS_PROFILE=bluemoxon"
    exit 1
fi

# Sync HTML files
echo -e "\n${GREEN}Syncing HTML files...${NC}"
aws s3 sync "$PROJECT_ROOT/site/" "s3://$BUCKET/" \
    --exclude "screenshots" \
    --exclude "screenshots/*" \
    --exclude ".DS_Store" \
    --content-type "text/html" \
    --delete

# Sync screenshots
echo -e "\n${GREEN}Syncing screenshots...${NC}"
aws s3 sync "$PROJECT_ROOT/docs/screenshots/" "s3://$BUCKET/screenshots/" \
    --exclude ".DS_Store" \
    --content-type "image/png" \
    --delete

# Invalidate CloudFront cache
echo -e "\n${GREEN}Invalidating CloudFront cache...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text)

echo -e "Invalidation ID: ${YELLOW}$INVALIDATION_ID${NC}"

echo -e "\n${GREEN}Deploy complete!${NC}"
echo -e "Site: https://bluemoxon.com"
echo -e "Note: CloudFront invalidation may take 1-2 minutes to propagate."
