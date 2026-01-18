#!/bin/bash
# =============================================================================
# Restore Cleanup Lambda
# =============================================================================
# Creates the cleanup Lambda from the API Lambda's code package.
# Use this when the cleanup Lambda was deleted or needs to be recreated.
#
# Usage:
#   ./scripts/restore-cleanup-lambda.sh prod
#
# What it does:
#   1. Downloads the API Lambda code package
#   2. Creates the cleanup Lambda with correct configuration
#   3. Verifies the Lambda is working
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
        CLEANUP_FUNCTION="bluemoxon-staging-cleanup"
        API_FUNCTION="bluemoxon-staging-api"
        AWS_PROFILE="bmx-staging"
        IAM_ROLE="arn:aws:iam::652617421195:role/bluemoxon-staging-cleanup-role"
        SECRET_ARN="arn:aws:secretsmanager:us-west-2:652617421195:secret:bluemoxon-staging/database-ayNNLZ"
        IMAGES_BUCKET="bluemoxon-images-staging"
        BMX_ENVIRONMENT="staging"
        BMX_CLEANUP_ENVIRONMENT="staging"
        ;;
    prod)
        CLEANUP_FUNCTION="bluemoxon-prod-cleanup"
        API_FUNCTION="bluemoxon-prod-api"
        AWS_PROFILE="bmx-prod"
        IAM_ROLE="arn:aws:iam::266672885920:role/bluemoxon-prod-cleanup-role"
        SECRET_ARN="arn:aws:secretsmanager:us-west-2:266672885920:secret:bluemoxon/db-credentials-Firmtl"
        IMAGES_BUCKET="bluemoxon-images"
        BMX_ENVIRONMENT="production"
        BMX_CLEANUP_ENVIRONMENT="prod"
        ;;
    *)
        log_error "Invalid environment: $ENV (must be 'staging' or 'prod')"
        exit 1
        ;;
esac

# Check if cleanup Lambda already exists
log_info "Checking if $CLEANUP_FUNCTION already exists..."
if AWS_PROFILE=$AWS_PROFILE aws lambda get-function --function-name "$CLEANUP_FUNCTION" > /dev/null 2>&1; then
    log_error "Lambda $CLEANUP_FUNCTION already exists! Use redeploy script instead."
    exit 1
fi

log_info "Creating $CLEANUP_FUNCTION from $API_FUNCTION code..."

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Get API Lambda code URL
log_info "Fetching API Lambda code URL..."
CODE_URL=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function \
    --function-name "$API_FUNCTION" \
    --query 'Code.Location' \
    --output text)

# Download the code
log_info "Downloading Lambda code package..."
curl -s -o "$TEMP_DIR/lambda.zip" "$CODE_URL"

# Get layer ARN from API Lambda
log_info "Getting layer ARN..."
LAYER_ARN=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function \
    --function-name "$API_FUNCTION" \
    --query 'Configuration.Layers[0].Arn' \
    --output text)

# Get VPC config from API Lambda
log_info "Getting VPC configuration..."
SUBNET_IDS=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function \
    --function-name "$API_FUNCTION" \
    --query 'Configuration.VpcConfig.SubnetIds' \
    --output text | tr '\t' ',')
SECURITY_GROUP_IDS=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function \
    --function-name "$API_FUNCTION" \
    --query 'Configuration.VpcConfig.SecurityGroupIds' \
    --output text | tr '\t' ',')

# Create the cleanup Lambda
log_info "Creating Lambda function..."
AWS_PROFILE=$AWS_PROFILE aws lambda create-function \
    --function-name "$CLEANUP_FUNCTION" \
    --runtime python3.12 \
    --role "$IAM_ROLE" \
    --handler lambdas.cleanup.handler.handler \
    --zip-file "fileb://$TEMP_DIR/lambda.zip" \
    --timeout 300 \
    --memory-size 256 \
    --layers "$LAYER_ARN" \
    --vpc-config "SubnetIds=$SUBNET_IDS,SecurityGroupIds=$SECURITY_GROUP_IDS" \
    --environment "Variables={BMX_DATABASE_SECRET_ARN=$SECRET_ARN,BMX_ENVIRONMENT=$BMX_ENVIRONMENT,BMX_CLEANUP_ENVIRONMENT=$BMX_CLEANUP_ENVIRONMENT,BMX_IMAGES_BUCKET=$IMAGES_BUCKET}" \
    --tracing-config Mode=Active \
    --output text \
    --query 'FunctionArn'

# Wait for function to be active
log_info "Waiting for Lambda to be active..."
AWS_PROFILE=$AWS_PROFILE aws lambda wait function-active-v2 \
    --function-name "$CLEANUP_FUNCTION"

# Verify the function
log_info "Verifying Lambda configuration..."
FUNCTION_ARN=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function \
    --function-name "$CLEANUP_FUNCTION" \
    --query 'Configuration.FunctionArn' \
    --output text)

log_success "Cleanup Lambda restored successfully!"
log_info "Function: $CLEANUP_FUNCTION"
log_info "ARN: $FUNCTION_ARN"
log_info ""
log_warn "NOTE: Remember to run 'terraform apply' to sync state, or the next terraform run may cause issues."
