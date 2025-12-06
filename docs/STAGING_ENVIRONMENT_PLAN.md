# Staging Environment Plan

## Current Status (Updated 2025-12-06)

### Completed
- ✅ Staging AWS account created (652617421195)
- ✅ GitHub OIDC provider configured in staging
- ✅ IAM role `github-actions-deploy` created
- ✅ `AWS_STAGING_ROLE_ARN` secret added to GitHub
- ✅ Deploy workflow updated for multi-environment support
- ✅ Staging branch configured with protection rules
- ✅ Terraform modules created (Lambda, API Gateway, S3, CloudFront, Cognito)
- ✅ Staging infrastructure deployed via Terraform
- ✅ CI/CD pipeline deploys to staging on push

### Outstanding
- ⏳ Staging database (RDS) - needed for full functionality
- ⏳ DATABASE_URL configuration for Lambda
- ⏳ Data sync scripts for prod → staging

---

## Overview

Create `staging.app.bluemoxon.com` as an isolated replica of production in a separate AWS account, with:
- Independent infrastructure (can be modified without affecting prod)
- Shared Cognito authentication (prod users work in staging)
- Version tracking across environments
- Cost-optimized (scales to near-zero when idle)
- Terraform-managed infrastructure

---

## Table of Contents

1. [Current Infrastructure](#1-current-infrastructure)
2. [Version Number System](#2-version-number-system)
3. [AWS Account Setup](#3-aws-account-setup)
4. [Infrastructure Architecture](#4-infrastructure-architecture)
5. [Deploy Workflow](#5-deploy-workflow)
6. [Data Sync Strategy](#6-data-sync-strategy)
7. [Implementation Phases](#7-implementation-phases)

---

## 1. Current Infrastructure

### Staging Environment Resources

| Resource | Name/ID | Status |
|----------|---------|--------|
| AWS Account | 652617421195 | ✅ Active |
| Lambda Function | `bluemoxon-staging-api` | ✅ Deployed |
| API Gateway | `ikxdby8a89.execute-api.us-west-2.amazonaws.com` | ✅ Active |
| Frontend S3 | `bluemoxon-frontend-staging` | ✅ Active |
| Images S3 | `bluemoxon-images-staging` | ✅ Active |
| Frontend CloudFront | `d3rkfi55tpd382.cloudfront.net` | ✅ Active |
| Images CloudFront | `d2zwmzka4w6cws.cloudfront.net` | ✅ Active |
| Cognito User Pool | `us-west-2_5pOhFH6LN` | ✅ Active |
| Cognito Client | `30cjt0d9rt1bf1baukbsvm3o` | ✅ Active |
| Cognito Domain | `bluemoxon-staging.auth.us-west-2.amazoncognito.com` | ✅ Active |
| RDS Database | N/A | ❌ Not deployed |

### Production Environment Resources (For Reference)

| Resource | Name/ID | Status |
|----------|---------|--------|
| AWS Account | 058264531112 | ✅ Active |
| Lambda Function | `bluemoxon-api` | ✅ Active |
| API Gateway | `api.bluemoxon.com` | ✅ Active |
| Frontend S3 | `bluemoxon-frontend` | ✅ Active |
| Frontend CloudFront | `E16BJX90QWQNQO` | ✅ Active |
| Cognito User Pool | `us-west-2_PvdIpXVKF` | ✅ Active |
| Cognito Client | `3ndaok3psd2ncqfjrdb57825he` | ✅ Active |
| RDS Database | Active | ✅ Active |

---

## 2. Version Number System

### Version Format

```
v{YYYY.MM.DD}-{short-sha}
Example: v2025.12.06-9b22b0a
```

### Implementation (Completed)

- **VERSION file**: `0.0.0-dev` (placeholder, auto-generated at deploy)
- **Deploy workflow**: Generates version as `YYYY.MM.DD-<short-sha>`
- **Backend**: Returns version in `X-App-Version` header and `/health/version` endpoint
- **Frontend**: Version injected at build time via Vite config

---

## 3. AWS Account Setup

### AWS Organizations Structure

```
Management Account (Production)
├── bluemoxon (058264531112) - Production
└── bluemoxon-staging (652617421195) - Staging
```

### Step-by-Step Setup (For New Account)

See [AWS_GITHUB_ACTIONS_SETUP.md](./AWS_GITHUB_ACTIONS_SETUP.md) for detailed instructions.

**Quick Reference:**

```bash
# 1. Create OIDC provider
aws iam create-open-id-connect-provider \
  --url "https://token.actions.githubusercontent.com" \
  --client-id-list "sts.amazonaws.com" \
  --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" "1c58a3a8518e8759bf075b76b750d4f2df264fcd"

# 2. Create IAM role with trust policy (see AWS_GITHUB_ACTIONS_SETUP.md)

# 3. Create and attach deploy policy (see AWS_GITHUB_ACTIONS_SETUP.md)

# 4. Add GitHub secret
gh secret set AWS_STAGING_ROLE_ARN --body "arn:aws:iam::<account-id>:role/github-actions-deploy"
```

### GitHub Secrets

| Secret | Value | Description |
|--------|-------|-------------|
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::058264531112:role/github-actions-deploy` | Production deploy role |
| `AWS_STAGING_ROLE_ARN` | `arn:aws:iam::652617421195:role/github-actions-deploy` | Staging deploy role |

---

## 4. Infrastructure Architecture

### Staging vs Prod Comparison

| Component | Production | Staging | Notes |
|-----------|------------|---------|-------|
| Lambda Runtime | python3.11 | python3.11 | Must match CI/CD |
| Lambda Memory | 512 MB | 256 MB | Cost savings |
| RDS | PostgreSQL | **Pending** | Needed for full function |
| CloudFront | Standard | Standard | Same config |
| S3 | Standard | Standard | Same config |
| Cognito | Dedicated pool | Dedicated pool | Separate user management |

### Terraform Structure

```
infra/terraform/
├── main.tf                 # Main infrastructure
├── variables.tf            # Variable definitions
├── outputs.tf              # Output values
├── locals.tf               # Local values
├── providers.tf            # AWS provider config
├── backend.tf              # State backend config
├── envs/
│   ├── staging.tfvars      # Staging-specific values
│   └── prod.tfvars         # Production-specific values
├── modules/
│   ├── api-gateway/        # API Gateway v2 (HTTP)
│   ├── cloudfront/         # CloudFront distributions
│   ├── cognito/            # Cognito user pool
│   ├── lambda/             # Lambda function
│   ├── rds/                # RDS PostgreSQL (not yet deployed)
│   └── s3/                 # S3 buckets
└── placeholder/
    └── placeholder.zip     # Initial Lambda placeholder
```

### Terraform Commands

```bash
# Initialize for staging
cd infra/terraform
terraform init -backend-config="key=bluemoxon/staging/terraform.tfstate"

# Plan changes
terraform plan -var-file=envs/staging.tfvars

# Apply changes
terraform apply -var-file=envs/staging.tfvars

# For production
terraform init -backend-config="key=bluemoxon/prod/terraform.tfstate"
terraform plan -var-file=envs/prod.tfvars
```

---

## 5. Deploy Workflow

### GitFlow Branching

```
main ─────●─────●─────●─────→  [Production: app.bluemoxon.com]
           \     \     \
staging ────●─────●─────●────→  [Staging: d3rkfi55tpd382.cloudfront.net]
             \   / \   /
feature/* ────●     ●────────→  [Feature branches]
```

### Workflow Triggers

| Branch | Workflow | Deploys To |
|--------|----------|------------|
| `main` | Deploy | Production (058264531112) |
| `staging` | Deploy | Staging (652617421195) |
| PR to main | CI | N/A (just tests) |

### Environment Configuration (deploy.yml)

The deploy workflow uses a `configure` job to set environment-specific values:

```yaml
configure:
  runs-on: ubuntu-latest
  outputs:
    environment: ${{ steps.config.outputs.environment }}
    lambda_function_name: ${{ steps.config.outputs.lambda_function_name }}
    s3_frontend_bucket: ${{ steps.config.outputs.s3_frontend_bucket }}
    # ... more outputs
  steps:
    - name: Set environment configuration
      id: config
      run: |
        if [[ "${{ github.ref_name }}" == "main" ]]; then
          echo "environment=production" >> $GITHUB_OUTPUT
          echo "lambda_function_name=bluemoxon-api" >> $GITHUB_OUTPUT
          # ... production values
        elif [[ "${{ github.ref_name }}" == "staging" ]]; then
          echo "environment=staging" >> $GITHUB_OUTPUT
          echo "lambda_function_name=bluemoxon-staging-api" >> $GITHUB_OUTPUT
          # ... staging values
        fi
```

### AWS Role Selection

Secrets cannot be passed through job outputs. The deploy job uses conditional expression:

```yaml
role-to-assume: ${{ needs.configure.outputs.environment == 'production' && secrets.AWS_DEPLOY_ROLE_ARN || secrets.AWS_STAGING_ROLE_ARN }}
```

---

## 6. Data Sync Strategy

### Database Sync (Future)

When staging RDS is deployed, use snapshot-based sync:

```bash
# scripts/sync-prod-to-staging.sh
# 1. Create snapshot of prod
# 2. Share snapshot with staging account
# 3. Copy snapshot to staging
# 4. Restore staging cluster from snapshot
```

### S3 Image Sync

```bash
#!/bin/bash
# scripts/sync-s3-prod-to-staging.sh

PROD_BUCKET="bluemoxon-images"
STAGING_BUCKET="bluemoxon-images-staging"

# Sync requires cross-account access or intermediate step
aws s3 sync "s3://$PROD_BUCKET" "s3://$STAGING_BUCKET" --delete
```

---

## 7. Implementation Phases

### Phase 1: Foundation ✅ Complete
- [x] VERSION file and version system
- [x] Staging branch created
- [x] Branch protection rules configured
- [x] AWS account created

### Phase 2: AWS Staging Account ✅ Complete
- [x] AWS account "bluemoxon-staging" created
- [x] IAM OIDC provider configured
- [x] GitHub Actions deploy role created
- [x] GitHub secrets added

### Phase 3: Terraform Infrastructure ✅ Complete
- [x] `infra/terraform/` structure created
- [x] Lambda module
- [x] API Gateway module
- [x] S3 + CloudFront modules
- [x] Cognito module
- [x] Staging environment deployed

### Phase 4: CI/CD ✅ Complete
- [x] Deploy workflow supports staging
- [x] Environment-specific configuration
- [x] Smoke tests for staging

### Phase 5: Database ⏳ Pending
- [ ] Deploy RDS module to staging
- [ ] Configure DATABASE_URL environment variable
- [ ] Run initial database migration
- [ ] Test full application flow

### Phase 6: Data Migration ⏳ Pending
- [ ] Create database sync script
- [ ] Run initial database sync
- [ ] Create S3 image sync script
- [ ] Run S3 sync

### Phase 7: DNS & SSL (Optional)
- [ ] Configure `staging.app.bluemoxon.com` DNS
- [ ] Add SSL certificate for custom domain
- [ ] Update CloudFront alternate domain

### Future: Production Migration
- [ ] Port Terraform to manage production
- [ ] Import existing prod resources
- [ ] Decommission CDK

---

## Cost Estimate (Staging)

| Resource | Monthly Cost |
|----------|--------------|
| Lambda (minimal use) | ~$0 |
| API Gateway | ~$1 |
| S3 Storage (~1GB) | ~$0.02 |
| CloudFront | ~$1 |
| RDS (when deployed) | ~$15-43 |
| **Current Total** | **~$2/month** |
| **With RDS** | **~$20-45/month** |

---

## Quick Reference

### URLs

| Environment | URL |
|-------------|-----|
| Production App | https://app.bluemoxon.com |
| Production API | https://api.bluemoxon.com/api/v1 |
| Staging App | https://d3rkfi55tpd382.cloudfront.net |
| Staging API | https://ikxdby8a89.execute-api.us-west-2.amazonaws.com |

### Common Commands

```bash
# Merge main to staging and deploy
git checkout staging
git merge origin/main
git push origin staging
gh run watch $(gh run list --workflow Deploy --limit 1 --json databaseId -q '.[0].databaseId') --exit-status

# Check staging Lambda logs
aws logs tail /aws/lambda/bluemoxon-staging-api --follow --profile staging

# Test staging API
curl https://ikxdby8a89.execute-api.us-west-2.amazonaws.com/health
```
