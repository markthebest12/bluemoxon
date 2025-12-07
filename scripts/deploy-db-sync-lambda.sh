#!/bin/bash
# =============================================================================
# Deploy Database Sync Lambda
# =============================================================================
# Builds and deploys the database sync Lambda to the staging account.
#
# Usage:
#   ./scripts/deploy-db-sync-lambda.sh [--create|--update]
#
# Options:
#   --create    Create new Lambda function (first time)
#   --update    Update existing Lambda code (subsequent deploys)
#
# Prerequisites:
#   - AWS CLI configured with 'staging' profile
#   - Docker (for building Lambda package with correct binaries)
# =============================================================================

set -euo pipefail

# Configuration
FUNCTION_NAME="bluemoxon-staging-db-sync"
LAMBDA_DIR="backend/lambdas/db_sync"
BUILD_DIR=".tmp/lambda-build"
RUNTIME="python3.12"
TIMEOUT=900  # 15 minutes
MEMORY=512
AWS_PROFILE="staging"

# VPC Configuration (staging VPC)
VPC_SUBNETS="subnet-0c5f84e98ba25334d,subnet-0ceb0276fa36428f2,subnet-09eeb023cb49a83d5,subnet-0bfb299044084bad3"
SECURITY_GROUP="sg-050fb5268bcd06443"  # Same as API Lambda

# Secrets (get full ARNs dynamically to include suffixes)
PROD_SECRET_ARN="arn:aws:secretsmanager:us-west-2:266672885920:secret:bluemoxon/db-credentials-Firmtl"
STAGING_SECRET_ARN=$(aws --profile staging secretsmanager describe-secret --secret-id "bluemoxon-staging/database" --query 'ARN' --output text)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
ACTION="${1:---update}"

cd "$(dirname "$0")/.."

log_info "Building Lambda package..."

# Clean and create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Install dependencies using Docker with Lambda Python runtime
# This ensures binary compatibility with Lambda's Amazon Linux 2023 environment
log_info "Installing dependencies using Lambda Docker image..."
docker run --rm \
    --entrypoint /bin/bash \
    -v "$(pwd)/$BUILD_DIR:/output" \
    --platform linux/amd64 \
    public.ecr.aws/lambda/python:3.12 \
    -c "pip install psycopg2-binary==2.9.9 -t /output --quiet && rm -rf /output/*.dist-info /output/__pycache__"

log_info "boto3 provided by Lambda runtime (not bundled)"

# Copy handler
cp "$LAMBDA_DIR/handler.py" "$BUILD_DIR/"

# Create ZIP
log_info "Creating deployment package..."
cd "$BUILD_DIR"
zip -r ../db-sync-lambda.zip . -q
cd ..

PACKAGE_SIZE=$(du -h db-sync-lambda.zip | cut -f1)
log_info "Package size: $PACKAGE_SIZE"

if [ "$ACTION" == "--create" ]; then
    log_info "Creating Lambda function..."

    # First create IAM role
    ROLE_NAME="${FUNCTION_NAME}-role"

    # Check if role exists
    if ! aws --profile "$AWS_PROFILE" iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        log_info "Creating IAM role..."

        aws --profile "$AWS_PROFILE" iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document '{
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }' > /dev/null

        # Attach basic execution policy
        aws --profile "$AWS_PROFILE" iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

        # Attach VPC execution policy
        aws --profile "$AWS_PROFILE" iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"

        # Create inline policy for Secrets Manager access (both accounts)
        aws --profile "$AWS_PROFILE" iam put-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-name "secrets-access" \
            --policy-document '{
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": ["secretsmanager:GetSecretValue"],
                    "Resource": [
                        "'"$PROD_SECRET_ARN"'*",
                        "'"$STAGING_SECRET_ARN"'*"
                    ]
                }]
            }'

        log_info "Waiting for IAM role to propagate..."
        sleep 10
    fi

    ROLE_ARN=$(aws --profile "$AWS_PROFILE" iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)

    # Create Lambda function
    aws --profile "$AWS_PROFILE" lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --role "$ROLE_ARN" \
        --handler "handler.handler" \
        --timeout "$TIMEOUT" \
        --memory-size "$MEMORY" \
        --zip-file "fileb://db-sync-lambda.zip" \
        --vpc-config "SubnetIds=$VPC_SUBNETS,SecurityGroupIds=$SECURITY_GROUP" \
        --environment "Variables={PROD_SECRET_ARN=$PROD_SECRET_ARN,STAGING_SECRET_ARN=$STAGING_SECRET_ARN,PROD_SECRET_REGION=us-west-2}" \
        --tags "Environment=staging,Purpose=database-sync" \
        --query '{FunctionName:FunctionName,State:State}' \
        --output table

    log_success "Lambda function created!"

else
    log_info "Updating Lambda function code..."

    aws --profile "$AWS_PROFILE" lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://db-sync-lambda.zip" \
        --query '{FunctionName:FunctionName,LastModified:LastModified}' \
        --output table

    log_success "Lambda function updated!"
fi

# Cleanup
rm -rf "$BUILD_DIR" db-sync-lambda.zip

echo
log_info "To invoke the Lambda:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --profile staging --payload '{}' .tmp/sync-response.json && cat .tmp/sync-response.json | jq"
