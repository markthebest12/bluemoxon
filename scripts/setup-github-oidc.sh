#!/bin/bash
# Setup AWS OIDC for GitHub Actions
# This script creates the necessary IAM resources for secure, keyless authentication
#
# Usage: ./scripts/setup-github-oidc.sh
#
# Prerequisites:
# - AWS CLI configured with admin access
# - jq installed

set -e

# Configuration
GITHUB_ORG="markthebest12"
GITHUB_REPO="bluemoxon"
AWS_PROFILE="${AWS_PROFILE:-bluemoxon}"
AWS_REGION="us-west-2"
ROLE_NAME="github-actions-deploy"

echo "Setting up GitHub OIDC for $GITHUB_ORG/$GITHUB_REPO"
echo "AWS Profile: $AWS_PROFILE"
echo "AWS Region: $AWS_REGION"
echo ""

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)
echo "AWS Account ID: $ACCOUNT_ID"

# Check if OIDC provider already exists
OIDC_PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$OIDC_PROVIDER_ARN" --profile "$AWS_PROFILE" 2>/dev/null; then
    echo "OIDC provider already exists"
else
    echo "Creating OIDC identity provider..."

    # Get GitHub's OIDC thumbprint (required for OIDC provider)
    # GitHub's thumbprint for actions: 6938fd4d98bab03faadb97b34396831e3780aea1
    aws iam create-open-id-connect-provider \
        --url "https://token.actions.githubusercontent.com" \
        --client-id-list "sts.amazonaws.com" \
        --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" \
        --profile "$AWS_PROFILE"

    echo "OIDC provider created"
fi

# Create trust policy for the IAM role
TRUST_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
                }
            }
        }
    ]
}
EOF
)

# Create permissions policy for deployment
PERMISSIONS_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaDeployment",
            "Effect": "Allow",
            "Action": [
                "lambda:UpdateFunctionCode",
                "lambda:GetFunction",
                "lambda:GetFunctionConfiguration"
            ],
            "Resource": "arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:bluemoxon-*"
        },
        {
            "Sid": "S3FrontendDeployment",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::bluemoxon-frontend",
                "arn:aws:s3:::bluemoxon-frontend/*"
            ]
        },
        {
            "Sid": "S3ImagesRead",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::bluemoxon-images",
                "arn:aws:s3:::bluemoxon-images/*"
            ]
        },
        {
            "Sid": "CloudFrontInvalidation",
            "Effect": "Allow",
            "Action": [
                "cloudfront:CreateInvalidation",
                "cloudfront:GetInvalidation"
            ],
            "Resource": "arn:aws:cloudfront::${ACCOUNT_ID}:distribution/E16BJX90QWQNQO"
        },
        {
            "Sid": "LambdaWaiters",
            "Effect": "Allow",
            "Action": [
                "lambda:GetFunctionConfiguration"
            ],
            "Resource": "arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:bluemoxon-*"
        }
    ]
}
EOF
)

# Check if role exists
if aws iam get-role --role-name "$ROLE_NAME" --profile "$AWS_PROFILE" 2>/dev/null; then
    echo "Role $ROLE_NAME already exists, updating..."

    # Update trust policy
    aws iam update-assume-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-document "$TRUST_POLICY" \
        --profile "$AWS_PROFILE"

    # Update permissions policy
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "github-actions-deploy-policy" \
        --policy-document "$PERMISSIONS_POLICY" \
        --profile "$AWS_PROFILE"
else
    echo "Creating IAM role $ROLE_NAME..."

    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --description "Role for GitHub Actions to deploy BlueMoxon" \
        --profile "$AWS_PROFILE"

    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "github-actions-deploy-policy" \
        --policy-document "$PERMISSIONS_POLICY" \
        --profile "$AWS_PROFILE"
fi

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo ""
echo "========================================"
echo "GitHub OIDC setup complete!"
echo "========================================"
echo ""
echo "Role ARN: $ROLE_ARN"
echo ""
echo "Add this secret to your GitHub repository:"
echo "  Name:  AWS_DEPLOY_ROLE_ARN"
echo "  Value: $ROLE_ARN"
echo ""
echo "To add the secret, run:"
echo "  gh secret set AWS_DEPLOY_ROLE_ARN --body '$ROLE_ARN'"
echo ""
echo "Or go to: https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/secrets/actions"
echo ""
