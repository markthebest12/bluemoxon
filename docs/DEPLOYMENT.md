# Deployment Guide

BlueMoxon uses **GitHub Actions** for CI/CD and **Terraform** for infrastructure management. This guide covers the deployment workflows and manual deployment procedures.

## Deployment Workflow

### Automated Deployment (Recommended)

All deployments go through GitHub Actions:

```text
Feature Branch → PR to staging → Merge → Deploy to Staging
                                            ↓
                              PR staging→main → Merge → Deploy to Production
```

| Workflow | Trigger | Target |
|----------|---------|--------|
| `ci.yml` | PR to staging/main | CI checks only |
| `deploy.yml` | Push to main | Production |
| `deploy-staging.yml` | Push to staging | Staging |
| `deploy-site.yml` | Push to main (site/* changes) | Marketing site |
| `terraform.yml` | PR with infra/* changes | Plan only |

### Environment URLs

| Environment | Frontend | API | Purpose |
|-------------|----------|-----|---------|
| Production | app.bluemoxon.com | api.bluemoxon.com | Live users |
| Staging | staging.app.bluemoxon.com | staging.api.bluemoxon.com | Testing |

## Prerequisites

### Local Tools

```bash
# AWS CLI v2
brew install awscli

# Terraform
brew install terraform

# PostgreSQL client (for DB access)
brew install libpq

# GitHub CLI
brew install gh
```

### AWS Profiles

Configure AWS profiles in `~/.aws/credentials`:

```ini
[default]
# Production account (266672885920)

[staging]
# Staging account (637423662077)
```

Verify access:

```bash
aws sts get-caller-identity
AWS_PROFILE=staging aws sts get-caller-identity
```

## Manual Deployment

### Deploy Backend (Lambda)

Build and deploy the Lambda function:

```bash
# Build deployment package (requires Docker for Linux binaries)
docker run --rm \
  -v $(pwd)/backend:/app:ro \
  -v .tmp/lambda-deploy:/output \
  --platform linux/amd64 \
  public.ecr.aws/lambda/python:3.12 \
  /bin/bash -c "
    pip install -q -t /output -r /app/requirements.txt
    cp -r /app/app /output/
  "

# Create zip
cd .tmp/lambda-deploy
zip -q -r ../bluemoxon-api.zip . -x "*.pyc" -x "*__pycache__*"
cd ../..

# Deploy to staging
AWS_PROFILE=staging aws s3 cp .tmp/bluemoxon-api.zip s3://bluemoxon-staging-deploy/lambda/bluemoxon-api.zip
AWS_PROFILE=staging aws lambda update-function-code \
  --function-name bluemoxon-staging-api \
  --s3-bucket bluemoxon-staging-deploy \
  --s3-key lambda/bluemoxon-api.zip

# Deploy to production
aws s3 cp .tmp/bluemoxon-api.zip s3://bluemoxon-deploy/lambda/bluemoxon-api.zip
aws lambda update-function-code \
  --function-name bluemoxon-api \
  --s3-bucket bluemoxon-deploy \
  --s3-key lambda/bluemoxon-api.zip
```

### Deploy Frontend

Build and deploy the Vue SPA:

```bash
cd frontend
npm run build

# Deploy to staging
AWS_PROFILE=staging aws s3 sync dist/ s3://bluemoxon-staging-frontend/
AWS_PROFILE=staging aws cloudfront create-invalidation \
  --distribution-id <STAGING_DISTRIBUTION_ID> \
  --paths "/*"

# Deploy to production
aws s3 sync dist/ s3://bluemoxon-frontend/
aws cloudfront create-invalidation \
  --distribution-id E16BJX90QWQNQO \
  --paths "/*"
```

### Deploy Marketing Site

```bash
# Deploy site/index.html to production (no staging for marketing site)
aws s3 cp site/index.html s3://bluemoxon-landing/index.html
aws cloudfront create-invalidation \
  --distribution-id ES60BQB34DNYS \
  --paths "/*"
```

## Infrastructure Changes (Terraform)

### Plan Changes

```bash
cd infra/terraform

# Staging
AWS_PROFILE=staging terraform plan -var-file=envs/staging.tfvars

# Production
terraform plan -var-file=envs/prod.tfvars
```

### Apply Changes

```bash
# Apply to staging first
AWS_PROFILE=staging terraform apply -var-file=envs/staging.tfvars

# Validate staging works
curl -s https://staging.api.bluemoxon.com/api/v1/health/deep | jq

# Then apply to production
terraform apply -var-file=envs/prod.tfvars
```

### Import Existing Resources

If a resource was created manually, import it before modifying:

```bash
terraform import 'module.cognito.aws_cognito_user_pool.this' us-west-2_POOLID
```

## Database Operations

### Run Migrations

```bash
# Get staging credentials
AWS_PROFILE=staging aws secretsmanager get-secret-value \
  --secret-id bluemoxon-staging/database \
  --query SecretString --output text | jq

# Run migrations
cd backend
DATABASE_URL="postgresql://user:pass@host:5432/bluemoxon" \
  poetry run alembic upgrade head
```

### Sync Production to Staging

Use the db-sync Lambda to copy production data to staging:

```bash
AWS_PROFILE=staging aws lambda invoke \
  --function-name bluemoxon-staging-db-sync \
  --payload '{}' \
  .tmp/sync-response.json

cat .tmp/sync-response.json | jq
```

## Post-Deployment Verification

### Health Checks

```bash
# Production
curl -s https://api.bluemoxon.com/api/v1/health/deep | jq

# Staging
curl -s https://staging.api.bluemoxon.com/api/v1/health/deep | jq
```

### Check Version

```bash
# API version header
curl -sI https://api.bluemoxon.com/api/v1/books | grep X-App-Version

# Full version info
curl -s https://api.bluemoxon.com/api/v1/health/info | jq
```

### Smoke Tests

The deploy workflows automatically run smoke tests:

1. API health endpoint returns 200
2. Books API returns paginated response
3. Frontend loads with expected content
4. Image URLs return proper Content-Type

## Rollback

### Lambda Rollback

```bash
# List recent versions
aws lambda list-versions-by-function --function-name bluemoxon-api

# Rollback by redeploying previous commit
git checkout <previous-sha>
# Then follow manual deploy steps above
```

### Frontend Rollback

```bash
# Redeploy from previous commit
git checkout <previous-sha>
cd frontend
npm run build
aws s3 sync dist/ s3://bluemoxon-frontend/
aws cloudfront create-invalidation --distribution-id E16BJX90QWQNQO --paths "/*"
```

### Terraform Rollback

```bash
# Revert to previous state (use with caution)
git checkout <previous-sha> -- infra/terraform/
terraform apply -var-file=envs/prod.tfvars
```

## Troubleshooting

### Deploy Workflow Fails

1. Check GitHub Actions logs: `gh run view <run-id> --log-failed`
2. Verify OIDC role permissions in AWS IAM
3. Check `AWS_DEPLOY_ROLE_ARN` secret is set correctly

### Lambda Errors After Deploy

```bash
# Check CloudWatch logs
aws logs tail /aws/lambda/bluemoxon-api --since 5m

# Check function configuration
aws lambda get-function-configuration --function-name bluemoxon-api
```

### Health Check Fails

1. Check deep health: `curl -s https://api.bluemoxon.com/api/v1/health/deep | jq`
2. Look for specific service failures (DB, S3, Cognito)
3. Check VPC endpoints if services timeout

### CloudFront Not Updating

```bash
# Check invalidation status
aws cloudfront list-invalidations --distribution-id E16BJX90QWQNQO

# Force new invalidation
aws cloudfront create-invalidation --distribution-id E16BJX90QWQNQO --paths "/*"
```

---

*Last Updated: December 2025*
