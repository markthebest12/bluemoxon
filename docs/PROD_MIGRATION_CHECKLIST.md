# Production Migration Checklist

This checklist documents the steps needed to migrate production infrastructure to Terraform, based on lessons learned from staging setup.

## Prerequisites

- [ ] Terraform state backend set up in prod account (#106)
- [ ] GitHub OIDC configured for prod deploys (#102)
- [ ] Backup of current production state documented

### Resource Backups

Before importing any resource, back it up:

```bash
mkdir -p .tmp/prod-backup

# Cognito
aws cognito-idp describe-user-pool --user-pool-id us-west-2_PvdIpXVKF > .tmp/prod-backup/cognito-user-pool.json
aws cognito-idp describe-user-pool-client --user-pool-id us-west-2_PvdIpXVKF --client-id 3ndaok3psd2ncqfjrdb57825he > .tmp/prod-backup/cognito-client.json
aws cognito-idp list-users --user-pool-id us-west-2_PvdIpXVKF > .tmp/prod-backup/cognito-users.json

# Lambda
aws lambda get-function --function-name bluemoxon-api > .tmp/prod-backup/lambda-api.json

# API Gateway
aws apigatewayv2 get-api --api-id <API_ID> > .tmp/prod-backup/api-gateway.json
```

## Phase 1: State Backend (#106)

```bash
# In prod account, create:
# - S3 bucket: bluemoxon-terraform-state-prod
# - DynamoDB table: bluemoxon-terraform-locks-prod

aws --profile prod s3 mb s3://bluemoxon-terraform-state-prod --region us-west-2
aws --profile prod dynamodb create-table \
  --table-name bluemoxon-terraform-locks-prod \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-west-2
```

## Phase 2: Import Resources (Order Matters!)

### 2.1 S3 Buckets (#108)

```bash
cd infra/terraform
terraform init -backend-config="bucket=bluemoxon-terraform-state-prod" \
               -backend-config="key=bluemoxon/prod/terraform.tfstate"

# Frontend bucket
terraform import 'module.frontend_bucket.aws_s3_bucket.this' bluemoxon-frontend

# Images bucket
terraform import 'module.images_bucket.aws_s3_bucket.this' bluemoxon-images
```

### 2.2 CloudFront Distributions (#109)

```bash
# Get distribution IDs
aws --profile prod cloudfront list-distributions \
  --query 'DistributionList.Items[*].[Id,Comment]' --output table

# Import frontend CDN
terraform import 'module.frontend_cdn[0].aws_cloudfront_distribution.this' E16BJX90QWQNQO
terraform import 'module.frontend_cdn[0].aws_cloudfront_origin_access_identity.this' <OAI_ID>

# Import images CDN
terraform import 'module.images_cdn[0].aws_cloudfront_distribution.this' <IMAGES_DIST_ID>
```

### 2.3 Cognito (#110)

**Current State:**
| Environment | Account | User Pool ID | Client ID | Users |
|-------------|---------|--------------|-----------|-------|
| **Prod** | 266672885920 | `us-west-2_PvdIpXVKF` | `3ndaok3psd2ncqfjrdb57825he` | 7 users |
| **Staging** | 652617421195 | `us-west-2_5pOhFH6LN` | `48ik81mrpc6anouk234sq31fbt` | 0 users |

**Goal:** Staging uses prod Cognito for authentication (shared users), managed by Terraform.

```bash
# Import user pool
terraform import 'module.cognito.aws_cognito_user_pool.this' us-west-2_PvdIpXVKF

# Import app client
terraform import 'module.cognito.aws_cognito_user_pool_client.this' us-west-2_PvdIpXVKF/3ndaok3psd2ncqfjrdb57825he

# Import domain
terraform import 'module.cognito.aws_cognito_user_pool_domain.this[0]' bluemoxon
```

**Staging configuration (already done in `.github/workflows/deploy.yml`):**
- Staging deploys use prod Cognito IDs (shared authentication)
- Frontend builds with prod Cognito config baked in
- Staging Lambda env vars updated via deploy workflow

**Callback URLs (managed manually until Terraform import):**

Already configured in prod Cognito client:
- `http://localhost:5173/callback`
- `https://bluemoxon.com/callback`
- `https://www.bluemoxon.com/callback`
- `https://staging.app.bluemoxon.com/callback`

Logout URLs:
- `http://localhost:5173`
- `https://bluemoxon.com`
- `https://www.bluemoxon.com`
- `https://staging.app.bluemoxon.com`

**Post-import:** Update Terraform variables to include all callback/logout URLs.

**Cleanup:** After staging verified, remove staging Cognito pool (`us-west-2_5pOhFH6LN` in account 652617421195).

### 2.4 Lambda & API Gateway (#107)

```bash
# Import Lambda function
terraform import 'module.lambda.aws_lambda_function.this' bluemoxon-api

# Import IAM role
terraform import 'module.lambda.aws_iam_role.lambda_exec' bluemoxon-api-exec-role

# Import API Gateway
terraform import 'module.api_gateway.aws_apigatewayv2_api.this' <API_ID>
```

### 2.5 Route53 & ACM (#111)

```bash
# Import hosted zone (usually not needed, reference via data source)
# Import ACM certificates
terraform import 'aws_acm_certificate.frontend' arn:aws:acm:us-east-1:266672885920:certificate/92395aeb-a01e-4a48-b4bd-0a9f1c04e861
terraform import 'aws_acm_certificate.api' arn:aws:acm:us-west-2:266672885920:certificate/85f33a7f-bd9e-4e60-befe-95cffea5cf9a
```

## Phase 3: Verify & Document

### 3.1 Verify No Changes

```bash
terraform plan -var-file=envs/prod.tfvars

# Should show: "No changes. Your infrastructure matches the configuration."
```

### 3.2 Document Resource IDs

Update `infra/terraform/envs/prod.tfvars`:
```hcl
environment        = "prod"
aws_account_id     = "266672885920"
domain_name        = "bluemoxon.com"
app_subdomain      = "app"
api_subdomain      = "api"
enable_database    = true
enable_cloudfront  = true
# ... etc
```

## Custom Domain Configuration

### Lessons from Staging

When setting up custom domains, the certificate must be in the **same account** as the resource:

| Resource | Cert Region | Cert Account |
|----------|-------------|--------------|
| CloudFront | us-east-1 | Same as CloudFront distribution |
| API Gateway | us-west-2 (same as API) | Same as API Gateway |
| Route53 | N/A | Can be different account (prod owns domain) |

### ACM Certificates Required

| Domain | Region | Purpose |
|--------|--------|---------|
| `*.bluemoxon.com` | us-east-1 | CloudFront wildcard |
| `api.bluemoxon.com` | us-west-2 | API Gateway |

### DNS Validation

ACM certificates can be validated via DNS in a different account:
1. Request certificate in target account
2. Get DNS validation record
3. Create CNAME in Route53 (prod account owns bluemoxon.com)
4. Wait for ISSUED status

### CloudFront Configuration

```bash
# Add custom domain alias
aws cloudfront update-distribution \
  --id <DIST_ID> \
  --distribution-config "{ ... Aliases: { Items: ['app.bluemoxon.com'], Quantity: 1 }, ViewerCertificate: { ACMCertificateArn: '...', SSLSupportMethod: 'sni-only' } }"
```

### API Gateway Custom Domain

```bash
# Create custom domain
aws apigatewayv2 create-domain-name \
  --domain-name "api.bluemoxon.com" \
  --domain-name-configurations CertificateArn=<ARN>,EndpointType=REGIONAL

# Create API mapping
aws apigatewayv2 create-api-mapping \
  --domain-name "api.bluemoxon.com" \
  --api-id <API_ID> \
  --stage '$default'
```

### Route53 Records

| Record | Type | Value |
|--------|------|-------|
| `app.bluemoxon.com` | A (Alias) | CloudFront distribution |
| `app.bluemoxon.com` | AAAA (Alias) | CloudFront distribution |
| `api.bluemoxon.com` | A (Alias) | API Gateway regional domain |

## Cognito URL Updates

When changing domains, update Cognito app client:
- Callback URLs: `https://app.bluemoxon.com/auth/callback`
- Logout URLs: `https://app.bluemoxon.com`

## Lambda CORS Updates

Update Lambda environment variable:
```
CORS_ORIGINS=https://app.bluemoxon.com,http://localhost:5173
```

## Rollback Plan

If anything goes wrong:
1. Resources exist in AWS regardless of Terraform state
2. Can always remove from state: `terraform state rm <resource>`
3. Can re-import: `terraform import <resource> <id>`
4. Manual AWS console is always available as fallback

## Post-Migration

- [ ] Merge staging branch to main (includes deploy.yml updates for staging custom domains)
- [ ] Test all endpoints
- [ ] Verify CI/CD deploys work
- [ ] Update documentation
- [ ] Train team on Terraform workflow
