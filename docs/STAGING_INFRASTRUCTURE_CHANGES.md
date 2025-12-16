# Staging Infrastructure Changes - 2025-12-07

## Summary

Manual changes made to fix staging environment issues. These need to be captured in Terraform.

## Changes Made

### 1. Deleted Cognito VPC Endpoint

**Problem**: PrivateLink access disabled error when using Managed Login + VPC endpoint
**Fix**: Deleted VPC endpoint `vpce-0256de046ef7a09f4`
**Command**:
```bash
AWS_PROFILE=staging aws ec2 delete-vpc-endpoints --vpc-endpoint-ids vpce-0256de046ef7a09f4
```

### 2. Created NAT Gateway

**Problem**: Lambda in VPC needs internet access to reach Cognito APIs
**Fix**: Created NAT Gateway like prod has

| Resource | ID |
|----------|-----|
| Elastic IP | `eipalloc-0b4dc0b1aba0c7b27` |
| NAT Gateway | `nat-0976b52974205934f` |
| Subnet (public, for NAT) | `subnet-0c5f84e98ba25334d` (us-west-2a) |

### 3. Created Private Route Table

**Problem**: Lambda subnets need to route through NAT Gateway
**Fix**: Created private route table with NAT route

| Resource | ID |
|----------|-----|
| Route Table | `rtb-00c330cfe9829abc4` |
| Route | 0.0.0.0/0 -> `nat-0976b52974205934f` |

**Associated Subnets** (private, for Lambda):
- `subnet-0ceb0276fa36428f2` (us-west-2b)
- `subnet-09eeb023cb49a83d5` (us-west-2c)
- `subnet-0bfb299044084bad3` (us-west-2d)

### 4. Updated Lambda VPC Configuration

**Fix**: Removed Lambda from public subnet (us-west-2a), keep only in private subnets
**Command**:
```bash
AWS_PROFILE=staging aws lambda update-function-configuration \
  --function-name bluemoxon-staging-api \
  --vpc-config SubnetIds=subnet-0ceb0276fa36428f2,subnet-09eeb023cb49a83d5,subnet-0bfb299044084bad3,SecurityGroupIds=sg-050fb5268bcd06443
```

### 5. Added Cognito IAM Permissions to Lambda Role

**Problem**: Lambda role `bluemoxon-staging-api-exec-role` lacked Cognito permissions
**Fix**: Added inline policy `cognito-access`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:Admin*",
        "cognito-idp:Describe*",
        "cognito-idp:Get*",
        "cognito-idp:List*"
      ],
      "Resource": "arn:aws:cognito-idp:us-west-2:652617421195:userpool/us-west-2_5pOhFH6LN"
    }
  ]
}
```

### 6. Enabled MFA on Cognito Pool

**Fix**: Set MFA to OPTIONAL with TOTP enabled (matches prod)
**Command**:
```bash
AWS_PROFILE=staging aws cognito-idp set-user-pool-mfa-config \
  --user-pool-id us-west-2_5pOhFH6LN \
  --mfa-configuration OPTIONAL \
  --software-token-mfa-configuration Enabled=true
```

### 8. Added Keep-Warm EventBridge Rule

**Problem**: Lambda cold starts take ~4 seconds, causing 503 timeouts on first request after idle
**Fix**: Created EventBridge rule to ping Lambda every 5 minutes

| Resource | ID/ARN |
|----------|--------|
| Rule | `bluemoxon-staging-keep-warm` |
| Rule ARN | `arn:aws:events:us-west-2:652617421195:rule/bluemoxon-staging-keep-warm` |

**Commands**:
```bash
AWS_PROFILE=staging aws events put-rule --name bluemoxon-staging-keep-warm --schedule-expression "rate(5 minutes)" --state ENABLED

AWS_PROFILE=staging aws lambda add-permission --function-name bluemoxon-staging-api --statement-id keep-warm-event --action lambda:InvokeFunction --principal events.amazonaws.com --source-arn arn:aws:events:us-west-2:652617421195:rule/bluemoxon-staging-keep-warm

AWS_PROFILE=staging aws events put-targets --rule bluemoxon-staging-keep-warm --targets '[{"Id":"1","Arn":"arn:aws:lambda:us-west-2:652617421195:function:bluemoxon-staging-api"}]'
```

### 7. Fixed API Gateway CORS (earlier session)

**Fix**: Updated CORS to include correct origin
**Config**:
```json
{
  "AllowCredentials": true,
  "AllowHeaders": ["*"],
  "AllowMethods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
  "AllowOrigins": ["https://staging.app.bluemoxon.com", "http://localhost:5173"],
  "ExposeHeaders": ["x-environment", "x-app-version"],
  "MaxAge": 3600
}
```

## Current Status

**Working**:
- Login flow
- Admin page (users list, roles, MFA status)
- API endpoints (books, etc.)
- CORS properly configured
- Cognito IAM permissions
- MFA enabled at pool level (OPTIONAL with TOTP)
- MFA status display per user
- "Enable MFA" button for users

**Known Issues**:
- Other users show "User does not exist" (expected - exist in DB from prod sync but not in staging Cognito)

## Remaining Terraform Work

All above changes need to be added to Terraform modules:

1. **VPC Module**: Add NAT Gateway, private route table, subnet associations
2. **Lambda Module**: Update VPC config to use only private subnets
3. **IAM Module**: Add Cognito permissions to Lambda execution role
4. **Cognito Module**: Set MFA configuration to OPTIONAL with TOTP

## Key Differences: Staging vs Prod

| Component | Production | Staging |
|-----------|------------|---------|
| NAT Gateway | `nat-0551444ab65c31f8c` | `nat-0976b52974205934f` |
| Cognito VPC Endpoint | None | None (deleted) |
| MFA | OPTIONAL | OPTIONAL |
| Cognito Pool | `us-west-2_PvdIpXVKF` | `us-west-2_5pOhFH6LN` |

## Staging AWS Resource IDs

| Resource | ID |
|----------|-----|
| VPC | `vpc-03f78def84c9e85e0` (default VPC) |
| Lambda | `bluemoxon-staging-api` |
| Lambda Exec Role | `bluemoxon-staging-api-exec-role` |
| API Gateway | `ikxdby8a89` |
| Cognito Pool | `us-west-2_5pOhFH6LN` |
| Cognito Client | `48ik81mrpc6anouk234sq31fbt` |
| Cognito Domain | `bluemoxon-staging` |
| NAT Gateway | `nat-0976b52974205934f` |
| Elastic IP | `eipalloc-0b4dc0b1aba0c7b27` |
| Private Route Table | `rtb-00c330cfe9829abc4` |
| Public Subnet | `subnet-0c5f84e98ba25334d` (us-west-2a) |
| Private Subnets | `subnet-0ceb0276fa36428f2`, `subnet-09eeb023cb49a83d5`, `subnet-0bfb299044084bad3` |
| Lambda Security Group | `sg-050fb5268bcd06443` |

### 9. GitHub Actions OIDC Role - Cross-Account Terraform State Access

**Problem**: GitHub Actions role cannot access Terraform state bucket in prod account for `terraform output` reading
**Related**: PR #291 (auto-sync from Terraform), PR #292 (revert workaround), Issue #293

**Root Cause**: Cross-account S3 access requires BOTH:
- Resource-based policy (bucket policy on `bluemoxon-terraform-state`) ✅ DONE via prod admin
- Identity-based policy (IAM policy on staging role) ❌ PENDING

**Required IAM Policy** (needs IAM admin access):

Add inline policy `terraform-state-access` to role `github-actions-deploy`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformStateAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::bluemoxon-terraform-state",
        "arn:aws:s3:::bluemoxon-terraform-state/*"
      ]
    },
    {
      "Sid": "DynamoDBLockAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:us-west-2:266672885920:table/bluemoxon-terraform-locks"
    }
  ]
}
```

**Commands** (requires IAM admin):

```bash
# Create policy document
cat > /tmp/terraform-state-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformStateAccess",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::bluemoxon-terraform-state",
        "arn:aws:s3:::bluemoxon-terraform-state/*"
      ]
    },
    {
      "Sid": "DynamoDBLockAccess",
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"],
      "Resource": "arn:aws:dynamodb:us-west-2:266672885920:table/bluemoxon-terraform-locks"
    }
  ]
}
EOF

# Apply to role
AWS_PROFILE=staging aws iam put-role-policy \
  --role-name github-actions-deploy \
  --policy-name terraform-state-access \
  --policy-document file:///tmp/terraform-state-policy.json
```

**Validation**:

```bash
# Test S3 access
AWS_PROFILE=staging aws s3 ls s3://bluemoxon-terraform-state/bluemoxon/staging/

# Test DynamoDB access (read lock table)
AWS_PROFILE=staging aws dynamodb scan \
  --table-name bluemoxon-terraform-locks \
  --limit 1 \
  --region us-west-2
```

**Alternative**: Enable github-oidc Terraform module and import existing role (requires IAM import permissions).

## Estimated Monthly Cost Impact

| Resource | Cost |
|----------|------|
| NAT Gateway | ~$32/month |
| Elastic IP | ~$3.65/month (if unattached) |

Total staging cost increase: ~$32/month (NAT Gateway was missing from original plan)

### 10. Lambda Invoke Permission for Eval Runbook Worker

**Date**: 2025-12-16
**Problem**: Eval runbook worker Lambda cannot invoke scraper Lambda for eBay FMV lookup
**Error**: `AccessDeniedException: User is not authorized to perform: lambda:InvokeFunction on resource: arn:aws:lambda:us-west-2:652617421195:function:bluemoxon-staging-scraper`

**Fix**: Added inline policy `lambda-invoke` to role `bluemoxon-staging-eval-runbook-worker-role`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-west-2:652617421195:function:bluemoxon-staging-scraper"
    }
  ]
}
```

**Command**:
```bash
AWS_PROFILE=bmx-staging aws iam put-role-policy \
  --role-name bluemoxon-staging-eval-runbook-worker-role \
  --policy-name lambda-invoke \
  --policy-document '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "lambda:InvokeFunction", "Resource": "arn:aws:lambda:us-west-2:652617421195:function:bluemoxon-staging-scraper"}]}'
```

**Note**: This permission should be managed by Terraform via the `lambda_invoke_arns` variable in the eval-runbook-worker module, but the staging eval-runbook-worker appears to have been created manually (role name pattern differs from Terraform module).
