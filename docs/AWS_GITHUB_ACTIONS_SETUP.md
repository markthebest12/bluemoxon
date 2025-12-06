# AWS GitHub Actions Setup Guide

This document covers the manual bootstrap steps required to enable GitHub Actions deployments to an AWS account. These steps must be completed before the CI/CD pipeline can deploy to the environment.

## Overview

The deployment pipeline uses AWS OIDC (OpenID Connect) for secure, credential-less authentication from GitHub Actions. This eliminates the need for long-lived AWS access keys.

### Architecture

```
GitHub Actions → OIDC Token → AWS STS → Assume Role → Deploy Resources
```

### Prerequisites

- AWS CLI configured with admin access to the target account
- `jq` installed for JSON parsing
- GitHub CLI (`gh`) for adding secrets

## Step 1: Create OIDC Identity Provider

The OIDC provider allows AWS to trust tokens issued by GitHub Actions.

```bash
# Set your target account ID
AWS_ACCOUNT_ID="<your-account-id>"

# Assume admin role if using AWS Organizations
CREDS=$(aws sts assume-role \
  --role-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:role/OrganizationAccountAccessRole" \
  --role-session-name "setup-oidc" \
  --output json)

export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.Credentials.SessionToken')

# Verify you're in the correct account
aws sts get-caller-identity

# Create OIDC provider (skip if already exists)
aws iam create-open-id-connect-provider \
  --url "https://token.actions.githubusercontent.com" \
  --client-id-list "sts.amazonaws.com" \
  --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
```

**Note:** The thumbprint list contains GitHub's OIDC certificate thumbprints. These rarely change but can be verified at [GitHub's documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect).

## Step 2: Create IAM Role for GitHub Actions

Create a role that GitHub Actions can assume via OIDC.

### Trust Policy

Save as `/tmp/trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<GITHUB_ORG>/<REPO_NAME>:*"
        }
      }
    }
  ]
}
```

**Important:** Replace:
- `<AWS_ACCOUNT_ID>` with your AWS account ID
- `<GITHUB_ORG>/<REPO_NAME>` with your GitHub repository (e.g., `markthebest12/bluemoxon`)

### Create the Role

```bash
aws iam create-role \
  --role-name github-actions-deploy \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --description "Role for GitHub Actions deployment"
```

## Step 3: Create and Attach Deployment Policy

### Deployment Policy

Save as `/tmp/deploy-policy.json`. Adjust resource ARNs for your environment:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::bluemoxon-frontend-<ENV>",
        "arn:aws:s3:::bluemoxon-frontend-<ENV>/*",
        "arn:aws:s3:::bluemoxon-lambda-artifacts-<ENV>",
        "arn:aws:s3:::bluemoxon-lambda-artifacts-<ENV>/*"
      ]
    },
    {
      "Sid": "LambdaAccess",
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration",
        "lambda:PublishVersion",
        "lambda:UpdateAlias",
        "lambda:CreateAlias",
        "lambda:GetAlias",
        "lambda:ListVersionsByFunction",
        "lambda:DeleteFunction",
        "lambda:ListAliases"
      ],
      "Resource": "arn:aws:lambda:us-west-2:<AWS_ACCOUNT_ID>:function:bluemoxon-<ENV>-*"
    },
    {
      "Sid": "CloudFrontAccess",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-west-2:<AWS_ACCOUNT_ID>:log-group:/aws/lambda/bluemoxon-<ENV>-*"
    }
  ]
}
```

**Replace:**
- `<ENV>` with environment name (`staging` or `prod`)
- `<AWS_ACCOUNT_ID>` with your AWS account ID

### Create and Attach Policy

```bash
# Create the policy
aws iam create-policy \
  --policy-name github-actions-deploy-policy \
  --policy-document file:///tmp/deploy-policy.json

# Attach to role
aws iam attach-role-policy \
  --role-name github-actions-deploy \
  --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/github-actions-deploy-policy"
```

### Updating an Existing Policy

If you need to update the policy later:

```bash
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/github-actions-deploy-policy"

# Delete old versions (AWS limits to 5 versions)
aws iam list-policy-versions --policy-arn "$POLICY_ARN" \
  --query 'Versions[?!IsDefaultVersion].VersionId' --output text | \
  xargs -n1 -I{} aws iam delete-policy-version --policy-arn "$POLICY_ARN" --version-id {}

# Create new version
aws iam create-policy-version \
  --policy-arn "$POLICY_ARN" \
  --policy-document file:///tmp/deploy-policy.json \
  --set-as-default
```

## Step 4: Add GitHub Secrets

Add the role ARN as a repository secret:

```bash
# For staging
gh secret set AWS_STAGING_ROLE_ARN --body "arn:aws:iam::<STAGING_ACCOUNT_ID>:role/github-actions-deploy"

# For production
gh secret set AWS_DEPLOY_ROLE_ARN --body "arn:aws:iam::<PROD_ACCOUNT_ID>:role/github-actions-deploy"
```

### Required GitHub Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_DEPLOY_ROLE_ARN` | Production deploy role | `arn:aws:iam::123456789012:role/github-actions-deploy` |
| `AWS_STAGING_ROLE_ARN` | Staging deploy role | `arn:aws:iam::987654321098:role/github-actions-deploy` |

## Step 5: Verify Setup

Test the OIDC authentication by triggering a deployment:

```bash
# Push to staging branch to trigger staging deploy
git checkout staging
git merge main
git push origin staging

# Watch the workflow
gh run list --workflow Deploy --limit 1
gh run watch <run-id> --exit-status
```

## Troubleshooting

### Error: "No OpenIDConnect provider found"

The OIDC provider hasn't been created in the target account. Run Step 1.

### Error: "Not authorized to perform: sts:AssumeRoleWithWebIdentity"

Check the trust policy:
1. Verify the `Federated` ARN matches your account
2. Verify the `sub` condition matches your repository
3. Ensure the OIDC provider exists

### Error: "AccessDeniedException" during deployment

The IAM policy is missing required permissions. Common missing permissions:
- `lambda:GetFunctionConfiguration` - needed for `aws lambda wait function-updated`
- `lambda:CreateAlias` - needed if alias doesn't exist
- `s3:ListBucket` - needed for sync operations

### Error: "Credentials could not be loaded"

GitHub Actions couldn't assume the role. Check:
1. Secret name matches workflow reference
2. Role ARN is correct
3. Trust policy allows the repository

## Environment-Specific Configuration

### Current Setup

| Environment | AWS Account | Role ARN | GitHub Secret |
|-------------|-------------|----------|---------------|
| Production | 058264531112 | `arn:aws:iam::058264531112:role/github-actions-deploy` | `AWS_DEPLOY_ROLE_ARN` |
| Staging | 652617421195 | `arn:aws:iam::652617421195:role/github-actions-deploy` | `AWS_STAGING_ROLE_ARN` |

### Deploy Workflow Configuration

The deploy workflow (`deploy.yml`) selects the role based on the branch:

```yaml
role-to-assume: ${{ needs.configure.outputs.environment == 'production' && secrets.AWS_DEPLOY_ROLE_ARN || secrets.AWS_STAGING_ROLE_ARN }}
```

## Complete Setup Script

For convenience, here's a complete script that performs all steps:

```bash
#!/bin/bash
set -e

# Configuration - UPDATE THESE
AWS_ACCOUNT_ID="<your-account-id>"
GITHUB_REPO="markthebest12/bluemoxon"
ENVIRONMENT="staging"  # or "prod"
AWS_REGION="us-west-2"

# Assume admin role (if using Organizations)
echo "Assuming admin role..."
CREDS=$(aws sts assume-role \
  --role-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:role/OrganizationAccountAccessRole" \
  --role-session-name "setup-github-actions" \
  --output json)

export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.Credentials.SessionToken')

echo "Connected to account: $(aws sts get-caller-identity --query 'Account' --output text)"

# Step 1: Create OIDC provider
echo "Creating OIDC provider..."
aws iam create-open-id-connect-provider \
  --url "https://token.actions.githubusercontent.com" \
  --client-id-list "sts.amazonaws.com" \
  --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" "1c58a3a8518e8759bf075b76b750d4f2df264fcd" \
  2>/dev/null || echo "OIDC provider already exists"

# Step 2: Create trust policy
echo "Creating IAM role..."
cat > /tmp/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name github-actions-deploy \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --description "Role for GitHub Actions deployment" \
  2>/dev/null || echo "Role already exists, updating trust policy..." && \
  aws iam update-assume-role-policy \
    --role-name github-actions-deploy \
    --policy-document file:///tmp/trust-policy.json

# Step 3: Create deployment policy
echo "Creating deployment policy..."
cat > /tmp/deploy-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::bluemoxon-frontend-${ENVIRONMENT}",
        "arn:aws:s3:::bluemoxon-frontend-${ENVIRONMENT}/*",
        "arn:aws:s3:::bluemoxon-lambda-artifacts-${ENVIRONMENT}",
        "arn:aws:s3:::bluemoxon-lambda-artifacts-${ENVIRONMENT}/*"
      ]
    },
    {
      "Sid": "LambdaAccess",
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode", "lambda:GetFunction", "lambda:GetFunctionConfiguration",
        "lambda:PublishVersion", "lambda:UpdateAlias", "lambda:CreateAlias",
        "lambda:GetAlias", "lambda:ListVersionsByFunction", "lambda:DeleteFunction", "lambda:ListAliases"
      ],
      "Resource": "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:bluemoxon-${ENVIRONMENT}-*"
    },
    {
      "Sid": "CloudFrontAccess",
      "Effect": "Allow",
      "Action": ["cloudfront:CreateInvalidation", "cloudfront:GetInvalidation"],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/lambda/bluemoxon-${ENVIRONMENT}-*"
    }
  ]
}
EOF

POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/github-actions-deploy-policy"

if aws iam get-policy --policy-arn "$POLICY_ARN" 2>/dev/null; then
  echo "Policy exists, updating..."
  aws iam list-policy-versions --policy-arn "$POLICY_ARN" \
    --query 'Versions[?!IsDefaultVersion].VersionId' --output text | \
    xargs -n1 -I{} aws iam delete-policy-version --policy-arn "$POLICY_ARN" --version-id {} 2>/dev/null || true
  aws iam create-policy-version \
    --policy-arn "$POLICY_ARN" \
    --policy-document file:///tmp/deploy-policy.json \
    --set-as-default
else
  echo "Creating new policy..."
  aws iam create-policy \
    --policy-name github-actions-deploy-policy \
    --policy-document file:///tmp/deploy-policy.json
fi

aws iam attach-role-policy \
  --role-name github-actions-deploy \
  --policy-arn "$POLICY_ARN" 2>/dev/null || true

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/github-actions-deploy"
echo ""
echo "=========================================="
echo "Setup complete!"
echo "Role ARN: $ROLE_ARN"
echo "=========================================="
echo ""
echo "Add this secret to GitHub:"
if [[ "$ENVIRONMENT" == "staging" ]]; then
  echo "  gh secret set AWS_STAGING_ROLE_ARN --body \"$ROLE_ARN\""
else
  echo "  gh secret set AWS_DEPLOY_ROLE_ARN --body \"$ROLE_ARN\""
fi
```

## Related Documentation

- [GitHub OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [AWS IAM OIDC Identity Providers](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [BlueMoxon Deploy Workflow](.github/workflows/deploy.yml)
