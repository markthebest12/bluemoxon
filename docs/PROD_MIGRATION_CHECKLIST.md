# Production Migration Checklist

This checklist documents the steps needed to migrate production infrastructure to Terraform, based on lessons learned from staging setup.

## Prerequisites

- [x] Terraform state backend set up in prod account (#106) - COMPLETED
- [x] GitHub OIDC configured for prod deploys (#102) - COMPLETED
- [x] Backup of current production state documented

## Migration Status (Updated 2024-12-09)

| Resource | Status | Issue | Notes |
|----------|--------|-------|-------|
| S3 Buckets (frontend, images) | IMPORTED | #108 | Using legacy names |
| S3 Logs Bucket | IMPORTED | #156 | bluemoxon-logs |
| API Gateway | IMPORTED | #107 | Includes custom domain, log group, Lambda permission |
| Cognito | IMPORTED | #110 | Using lifecycle ignore_changes for URL attributes |
| GitHub OIDC | IMPORTED | #137 | Provider + role + policy |
| CloudFront (frontend/images) | SKIPPED | #109 | Prod uses OAC, module uses OAI - managed externally |
| Lambda | SKIPPED | N/A | Different architecture - managed externally |
| Landing Site | IMPORTED | #154 | New landing-site module with OAC support (7 resources) |
| Route53 | IMPORTED | #111, #157 | Hosted zone + 10 alias records (11 resources) |
| ACM | EXTERNAL | #111 | Certs managed externally, ARNs passed to Terraform |

**Terraform State:** 49 resources in `s3://bluemoxon-terraform-state-prod/bluemoxon/prod/terraform.tfstate`

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

**Current State (Updated 2024-12-08):**
| Environment | Account | User Pool ID | Client ID | Notes |
|-------------|---------|--------------|-----------|-------|
| **Prod** | 266672885920 | `us-west-2_PvdIpXVKF` | `3ndaok3psd2ncqfjrdb57825he` | Production users |
| **Staging** | 652617421195 | `us-west-2_xhoIfvlHv` | `2fru2pb5qc5o3o241hec24mj29` | Separate pool (isolated) |

**Architecture:** Separate Cognito pools per environment with automatic `cognito_sub` migration in auth code.

```bash
# Import user pool
terraform import 'module.cognito.aws_cognito_user_pool.this' us-west-2_PvdIpXVKF

# Import app client
terraform import 'module.cognito.aws_cognito_user_pool_client.this' us-west-2_PvdIpXVKF/3ndaok3psd2ncqfjrdb57825he

# Import domain
terraform import 'module.cognito.aws_cognito_user_pool_domain.this[0]' bluemoxon
```

**Configuration (updated in `.github/workflows/deploy.yml`):**
- Each environment uses its own Cognito pool (separate authentication)
- Frontend builds with environment-specific Cognito config
- Auth code handles `cognito_sub` migration when users switch environments

**Callback URLs:**

Staging Cognito client (`48ik81mrpc6anouk234sq31fbt`):
- `http://localhost:5173/auth/callback`
- `https://staging.app.bluemoxon.com/auth/callback`

Prod Cognito client (`3ndaok3psd2ncqfjrdb57825he`):
- `http://localhost:5173/callback`
- `https://bluemoxon.com/callback`
- `https://www.bluemoxon.com/callback`
- `https://app.bluemoxon.com/auth/callback`

**Post-import:** Verify Terraform variables match the callback/logout URLs configured above.

**Warning:** `update-user-pool-client` is a full replacement, not a patch. Always include ALL settings (auth flows, callback URLs, OAuth config) or they will be removed.

**Required Auth Flows (ExplicitAuthFlows):**
The Cognito client MUST have these auth flows enabled for Amplify SDK `signIn` to work:
- `ALLOW_USER_PASSWORD_AUTH` - Required for direct username/password authentication
- `ALLOW_USER_SRP_AUTH` - Secure Remote Password protocol (recommended)
- `ALLOW_REFRESH_TOKEN_AUTH` - Required for token refresh

Without `ALLOW_USER_PASSWORD_AUTH`, login will fail with "Invalid email or password" even with correct credentials.

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

**Route53 Hosted Zone** - Use data source (don't import, registrar-managed):
```hcl
data "aws_route53_zone" "main" {
  name = "bluemoxon.com"
}
# Zone ID: Z09346283AE9VMIQQJ8VL
```

**Route53 Records** to create/import:
| Record | Type | Target |
|--------|------|--------|
| `bluemoxon.com` | A/AAAA | Landing CloudFront |
| `www.bluemoxon.com` | A/AAAA | Landing CloudFront |
| `app.bluemoxon.com` | A/AAAA | App CloudFront |
| `api.bluemoxon.com` | A | API Gateway |
| `staging.app.bluemoxon.com` | A/AAAA | Staging CloudFront |
| `staging.api.bluemoxon.com` | A | Staging API Gateway |

**ACM Certificates** - Keep external, pass ARNs to Terraform:
| Domain | Region | ARN |
|--------|--------|-----|
| `*.bluemoxon.com` | us-east-1 | `arn:aws:acm:us-east-1:266672885920:certificate/92395aeb-a01e-4a48-b4bd-0a9f1c04e861` |
| `api.bluemoxon.com` | us-west-2 | `arn:aws:acm:us-west-2:266672885920:certificate/85f33a7f-bd9e-4e60-befe-95cffea5cf9a` |
| `staging.api.bluemoxon.com` | us-west-2 | `arn:aws:acm:us-west-2:266672885920:certificate/fdc9433a-89c2-4a7c-a4c1-f7794b8f7db9` |

### 2.7 Landing Site (#154) - Prod Only

Marketing website at bluemoxon.com / www.bluemoxon.com (no staging equivalent).

**Resources:**
- S3 bucket: `bluemoxon-landing`
- CloudFront: `ES60BQB34DNYS` (dui69hltsg2ds.cloudfront.net)
- Aliases: bluemoxon.com, www.bluemoxon.com
- Uses same wildcard cert as app

```bash
# Import landing bucket
terraform import 'module.landing_bucket.aws_s3_bucket.this' bluemoxon-landing

# Import landing CloudFront
terraform import 'module.landing_cdn[0].aws_cloudfront_distribution.this' ES60BQB34DNYS
```

**Note:** The `bluemoxon-logs` bucket (CloudFront access logs) is optional to terraform.

### 2.6 GitHub Actions OIDC (#102)

Import the GitHub Actions OIDC provider and IAM role:

```bash
# Import OIDC provider
terraform import -var-file=envs/prod.tfvars \
  'module.github_oidc[0].aws_iam_openid_connect_provider.github' \
  "arn:aws:iam::266672885920:oidc-provider/token.actions.githubusercontent.com"

# Import IAM role
terraform import -var-file=envs/prod.tfvars \
  'module.github_oidc[0].aws_iam_role.github_actions' \
  "github-actions-deploy"

# Import IAM policy
terraform import -var-file=envs/prod.tfvars \
  'module.github_oidc[0].aws_iam_role_policy.deploy' \
  "github-actions-deploy:github-actions-deploy-policy"
```

**Note:** Prod uses legacy bucket names (`bluemoxon-frontend`, `bluemoxon-images`) which are configured as overrides in `prod.tfvars`.

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

## VPC Networking Requirements (Lambda in VPC)

When Lambda is deployed in a VPC (for RDS access), it **cannot reach AWS services** without:

### Required VPC Endpoints

| Service | Endpoint Type | Required For |
|---------|--------------|--------------|
| `com.amazonaws.us-west-2.secretsmanager` | Interface | Database credentials retrieval |
| `com.amazonaws.us-west-2.s3` | Gateway | S3 bucket access (images) |
| `com.amazonaws.us-west-2.cognito-idp` | Interface | Cognito API calls (health checks) |

### Current State (Staging Account 652617421195)

Created manually 2024-12-07:
- S3 Gateway Endpoint: `vpce-0fa311c71ef94ad87`
- Secrets Manager Interface Endpoint: (existed)
- Cognito Interface Endpoint: `vpce-0256de046ef7a09f4`

### Terraform Import Commands

```bash
# S3 Gateway Endpoint
terraform import 'aws_vpc_endpoint.s3' vpce-0fa311c71ef94ad87

# Cognito Interface Endpoint
terraform import 'aws_vpc_endpoint.cognito' vpce-0256de046ef7a09f4

# Secrets Manager (if not already in state)
terraform import 'aws_vpc_endpoint.secretsmanager' <endpoint-id>
```

### Deep Health Check Dependencies

The `/api/v1/health/deep` endpoint requires network access to:
1. **RDS** (PostgreSQL) - via VPC internal routing
2. **S3** - for images bucket check - needs VPC endpoint
3. **Cognito** - for user pool describe - needs VPC endpoint
4. **Secrets Manager** - for DB credentials - needs VPC endpoint

**Symptom of missing VPC endpoint:** Lambda times out (30s) with "Service Unavailable"

**Cross-Account Cognito Note:** When staging uses prod Cognito (shared users), the Cognito VPC endpoint in staging account cannot call `describe_user_pool` for prod account's pool. This causes "InvalidParameterException" in deep health check. However, JWT validation works because it uses the public JWKS endpoint (fetched via httpx, not boto3). This is expected behavior for cross-account Cognito sharing.

### Interface Endpoint Security Groups

Interface endpoints require security groups that allow HTTPS (443) from Lambda security group:
- Lambda SG → Endpoint SG on port 443

### S3 Bucket Requirements

Staging images bucket: `bluemoxon-staging-images` (created 2024-12-07 after accidental deletion)

If bucket is deleted, deep health check will fail (S3 check hangs/times out).

## Rollback Plan

If anything goes wrong:
1. Resources exist in AWS regardless of Terraform state
2. Can always remove from state: `terraform state rm <resource>`
3. Can re-import: `terraform import <resource> <id>`
4. Manual AWS console is always available as fallback

## Lessons from Staging Destroy/Apply Test (2024-12-08)

This section documents issues discovered during the staging Terraform conformance test (full destroy → apply from scratch).

### Issue 1: Cognito VPC Endpoint AZ Compatibility

**Problem:** Cognito VPC endpoint only supports certain AZs (us-west-2a, us-west-2b, us-west-2c), NOT us-west-2d.

**Error:** `InvalidParameter: VPC vpce-xxx availability zone(s) [us-west-2d] must be a subset of the VPC endpoint service's availability zones`

**Solution:** Added `cognito_endpoint_subnet_ids` variable to Terraform:
- `infra/terraform/variables.tf` - Root variable with fallback
- `infra/terraform/modules/vpc-networking/variables.tf` - Module variable
- `infra/terraform/modules/vpc-networking/main.tf` - Uses variable with fallback to `private_subnet_ids`
- `infra/terraform/main.tf` - Passes variable to module

**Prod Action Required:**
```hcl
# In envs/prod.tfvars, if VPC has us-west-2d subnets:
cognito_endpoint_subnet_ids = [
  "subnet-xxx",  # us-west-2a
  "subnet-yyy"   # us-west-2b
]
```

### Issue 2: Cognito IDs Change After Terraform Recreate

**Problem:** When Terraform destroys and recreates Cognito, the pool ID and client ID change.

**Impact:** After destroy/apply cycle:
- Old: `us-west-2_5pOhFH6LN` → New: `us-west-2_xhoIfvlHv`
- Config files and workflows reference old IDs

**Solution:** Updated `infra/config/staging.json` with new Cognito IDs:
```json
"cognito": {
  "user_pool_id": "us-west-2_xhoIfvlHv",
  "app_client_id": "2fru2pb5qc5o3o241hec24mj29",
  "domain": "bluemoxon-staging.auth.us-west-2.amazoncognito.com"
}
```

**Prod Action Required:**
- CRITICAL: Avoid destroying Cognito in prod (users would lose access)
- If must recreate: Update `infra/config/production.json` immediately after

### Issue 3: Cross-Account Secret Access with Default KMS

**Problem:** The db-sync Lambda cannot access prod secrets because they're encrypted with default KMS key (`aws/secretsmanager`).

**Error:** `InvalidRequestException: You can't access a secret from a different AWS account if you encrypt the secret with the default KMS service key`

**Options to Fix:**
1. **Re-encrypt prod secret** with customer-managed KMS key (requires key policy update)
2. **Use local sync script** with network access to both databases
3. **Use AWS DMS** for cross-account replication

**Current Workaround:** Use local `scripts/sync-prod-to-staging.sh` (requires VPC peering or bastion access)

### Issue 4: S3 Bucket Naming Convention

**Problem:** Sync script had wrong bucket name `bluemoxon-staging-images` instead of `bluemoxon-images-staging`.

**Convention:** `bluemoxon-{resource}-{environment}` NOT `bluemoxon-{environment}-{resource}`
- Correct: `bluemoxon-images-staging`, `bluemoxon-frontend-staging`
- Wrong: `bluemoxon-staging-images`, `bluemoxon-staging-frontend`

**Files Fixed:** `scripts/sync-prod-to-staging.sh`

### Issue 5: Ruff Formatting in CI

**Problem:** CI failed on Ruff format check for `backend/lambdas/db_sync/handler.py`.

**Solution:** Run `poetry run ruff format .` before committing.

**CI Requirement:** All Python code must pass:
```bash
poetry run ruff check .
poetry run ruff format --check .
```

### Issue 6: Lambda Placeholder Code Causes Health Check Failure

**Problem:** After Terraform applies, Lambda has placeholder code (not actual application). Health check fails until GitHub deploy workflow runs.

**Sequence Required:**
1. Terraform apply (creates Lambda with placeholder)
2. GitHub deploy workflow (deploys actual code)
3. Database sync (creates tables)
4. Deep health check passes

**Prod Consideration:** Plan deployment sequence carefully to minimize downtime.

## Post-Migration

- [ ] Merge staging branch to main (includes deploy.yml updates for staging custom domains)
- [ ] Test all endpoints
- [ ] Verify CI/CD deploys work
- [ ] Update documentation
- [ ] Train team on Terraform workflow

## Centralized Configuration (infra/config/*.json)

Environment-specific configuration is centralized in JSON files at `infra/config/`:

| File | Purpose |
|------|---------|
| `staging.json` | All staging environment values |
| `production.json` | All production environment values |

### Configuration Structure

```json
{
  "environment": "staging",
  "aws_account_id": "652617421195",
  "aws_region": "us-west-2",
  "domain": { "base": "...", "app": "...", "api": "..." },
  "urls": { "app": "...", "api": "..." },
  "cognito": { "user_pool_id": "...", "app_client_id": "...", "domain": "..." },
  "lambda": { "function_name": "...", ... },
  "s3": { "frontend_bucket": "...", "images_bucket": "..." },
  "cloudfront": { "frontend_distribution_id": "...", ... },
  "database": { ... },
  "features": { ... },
  "acm_certificates": { ... }
}
```

### Usage

**GitHub Actions workflows** read from these files via `jq`:
```bash
CONFIG_FILE="infra/config/staging.json"
COGNITO_POOL_ID=$(jq -r '.cognito.user_pool_id' $CONFIG_FILE)
```

**Terraform** can read via `jsondecode(file(...))`:
```hcl
locals {
  config = jsondecode(file("${path.module}/../../config/${var.environment}.json"))
  cognito_user_pool_id = local.config.cognito.user_pool_id
}
```

### Benefits

1. **Single source of truth** - No more scattered hardcoded values
2. **Easy auditing** - All config in one place per environment
3. **Workflow consistency** - CI and deploy use same source
4. **Terraform integration** - Can be consumed by Terraform modules
5. **Validation** - JSON schema can enforce structure

### Adding New Configuration

When adding new config values:
1. Add to both `staging.json` and `production.json`
2. Update workflow to read new value via `jq`
3. Add to smoke tests if validation needed
