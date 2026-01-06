#!/bin/bash
# =============================================================================
# Bootstrap Terraform State Backend for Staging
# =============================================================================
# Run this script with an AWS profile that has admin permissions in the
# staging account (652617421195).
#
# Usage:
#   AWS_PROFILE=staging-admin ./scripts/bootstrap-staging-terraform.sh
#
# Or if using SSO:
#   aws sso login --profile staging-admin
#   AWS_PROFILE=staging-admin ./scripts/bootstrap-staging-terraform.sh
# =============================================================================

set -euo pipefail

BUCKET_NAME="bluemoxon-staging-terraform-state"
TABLE_NAME="bluemoxon-terraform-locks-staging"
REGION="us-west-2"
ACCOUNT_ID="652617421195"

echo "============================================"
echo "  Bootstrapping Staging Terraform Backend"
echo "============================================"
echo ""
echo "Account: $ACCOUNT_ID"
echo "Region:  $REGION"
echo "Bucket:  $BUCKET_NAME"
echo "Table:   $TABLE_NAME"
echo ""

# Verify we're in the right account
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
if [[ "$CURRENT_ACCOUNT" != "$ACCOUNT_ID" ]]; then
  echo "ERROR: Expected account $ACCOUNT_ID but got $CURRENT_ACCOUNT"
  echo "Please set AWS_PROFILE to a staging admin profile"
  exit 1
fi

echo "Verified: Running in staging account $ACCOUNT_ID"
echo ""

# -----------------------------------------------------------------------------
# S3 Bucket
# -----------------------------------------------------------------------------
echo "=== S3 Bucket ==="

# Check if bucket exists
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
  echo "Bucket $BUCKET_NAME already exists"
else
  echo "Creating bucket $BUCKET_NAME..."
  aws s3api create-bucket \
    --bucket "$BUCKET_NAME" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"
  echo "Created bucket"
fi

# Enable versioning
echo "Enabling versioning..."
aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled
echo "Versioning enabled"

# Enable encryption
echo "Enabling encryption..."
aws s3api put-bucket-encryption \
  --bucket "$BUCKET_NAME" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
echo "Encryption enabled"

# Block public access
echo "Blocking public access..."
aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "Public access blocked"

echo ""

# -----------------------------------------------------------------------------
# DynamoDB Table
# -----------------------------------------------------------------------------
echo "=== DynamoDB Lock Table ==="

# Check if table exists
if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" 2>/dev/null; then
  echo "Table $TABLE_NAME already exists"
else
  echo "Creating table $TABLE_NAME..."
  aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION"

  echo "Waiting for table to be active..."
  aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION"
  echo "Table created and active"
fi

echo ""

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo "============================================"
echo "  Bootstrap Complete!"
echo "============================================"
echo ""
echo "Terraform backend configuration:"
echo ""
echo "  terraform {"
echo "    backend \"s3\" {"
echo "      bucket         = \"$BUCKET_NAME\""
echo "      key            = \"bluemoxon/staging/terraform.tfstate\""
echo "      region         = \"$REGION\""
echo "      encrypt        = true"
echo "      dynamodb_table = \"$TABLE_NAME\""
echo "    }"
echo "  }"
echo ""
echo "Next steps:"
echo "  1. cd infra/terraform"
echo "  2. terraform init -backend-config=\"bucket=$BUCKET_NAME\" \\"
echo "       -backend-config=\"key=bluemoxon/staging/terraform.tfstate\" \\"
echo "       -backend-config=\"dynamodb_table=$TABLE_NAME\""
echo "  3. terraform plan -var-file=envs/staging.tfvars"
echo "  4. terraform apply -var-file=envs/staging.tfvars"
echo ""
