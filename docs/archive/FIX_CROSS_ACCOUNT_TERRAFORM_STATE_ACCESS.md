# Fix: Cross-Account Terraform State S3 Access (Issue #293)

## Problem Summary

GitHub Actions OIDC role in staging account (652617421195) cannot access Terraform state bucket `bluemoxon-terraform-state` in production account (266672885920).

This prevents PR #291's feature (auto-sync deploy config from Terraform outputs) from working.

## Root Cause

Cross-account S3 access requires BOTH:

1. **Resource-based policy** (S3 bucket policy) - ✅ DONE (PR #291, applied by prod admin)
2. **Identity-based policy** (IAM role policy) - ❌ PENDING (this fix)

The staging AWS profile (`github-actions-deploy` user) lacks IAM admin permissions to modify the OIDC role policy.

## Current State

### Staging Account Resources

- **Account ID**: 652617421195
- **OIDC Provider**: `arn:aws:iam::652617421195:oidc-provider/token.actions.githubusercontent.com` (exists, not in Terraform)
- **OIDC Role**: `arn:aws:iam::652617421195:role/github-actions-deploy` (exists, not in Terraform)
- **Terraform Module**: `enable_github_oidc = false` in `staging.tfvars`

### Production Account Resources

- **Account ID**: 266672885920
- **State Bucket**: `s3://bluemoxon-terraform-state` (has bucket policy allowing staging role)
- **Lock Table**: `bluemoxon-terraform-locks` (DynamoDB)

### Access Test (Currently Fails)

```bash
AWS_PROFILE=staging aws s3 ls s3://bluemoxon-terraform-state/
# Error: AccessDenied - User is not authorized to perform: s3:ListBucket
```

## Solution Options

### Option 1: Manual IAM Policy Update (Recommended - Fastest)

**Prerequisites**: IAM admin access to staging account

**Steps**:

1. Create policy document:

```bash
cat > /tmp/terraform-state-policy.json <<'EOF'
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
EOF
```

1. Apply to role:

```bash
AWS_PROFILE=staging aws iam put-role-policy \
  --role-name github-actions-deploy \
  --policy-name terraform-state-access \
  --policy-document file:///tmp/terraform-state-policy.json
```

1. Validate:

```bash
# Test S3 access
AWS_PROFILE=staging aws s3 ls s3://bluemoxon-terraform-state/bluemoxon/staging/

# Test DynamoDB access
AWS_PROFILE=staging aws dynamodb scan \
  --table-name bluemoxon-terraform-locks \
  --limit 1 \
  --region us-west-2
```

1. Test in GitHub Actions:

```bash
# Manually trigger deploy workflow on staging branch
gh workflow run deploy.yml --ref staging
```

### Option 2: Import to Terraform and Enable Module (Comprehensive)

**Prerequisites**: IAM admin access to staging account

**Steps**:

1. Apply manual policy from Option 1 first

2. Import existing resources:

```bash
cd infra/terraform

# Import OIDC provider
terraform import 'module.github_oidc[0].aws_iam_openid_connect_provider.github' \
  'arn:aws:iam::652617421195:oidc-provider/token.actions.githubusercontent.com'

# Import IAM role
terraform import 'module.github_oidc[0].aws_iam_role.github_actions' \
  'github-actions-deploy'

# Import role policy
terraform import 'module.github_oidc[0].aws_iam_role_policy.deploy' \
  'github-actions-deploy:github-actions-deploy-policy'
```

1. Enable module in staging.tfvars:

```bash
# Change this line:
enable_github_oidc = false

# To:
enable_github_oidc = true
```

1. Run Terraform plan to verify:

```bash
AWS_PROFILE=staging terraform plan -var-file=envs/staging.tfvars -var="db_password=$STAGING_DB_PASSWORD"
```

Expected: No changes (imports match existing resources)

1. Apply if plan looks good:

```bash
AWS_PROFILE=staging terraform apply -var-file=envs/staging.tfvars -var="db_password=$STAGING_DB_PASSWORD"
```

## Terraform Changes Included

This PR includes the following Terraform updates (ready for Option 2):

### 1. github-oidc Module Updates

- **File**: `infra/terraform/modules/github-oidc/main.tf`
- **Change**: Added conditional Terraform state access policy statements

### 2. New Variables

- **File**: `infra/terraform/modules/github-oidc/variables.tf`
  - `terraform_state_bucket_arn` - S3 bucket ARN for cross-account access
  - `terraform_state_dynamodb_table_arn` - DynamoDB table ARN for lock access

- **File**: `infra/terraform/variables.tf`
  - Same variables added to root module

### 3. Staging Configuration

- **File**: `infra/terraform/envs/staging.tfvars`
  - Added Terraform state ARNs pointing to prod account resources
  - Will be used when `enable_github_oidc = true`

### 4. Documentation

- **File**: `docs/STAGING_INFRASTRUCTURE_CHANGES.md`
  - Added section 9 documenting this manual change requirement

## Validation

After applying either option:

### Test 1: AWS CLI Access

```bash
# Should succeed
AWS_PROFILE=staging aws s3 ls s3://bluemoxon-terraform-state/bluemoxon/staging/

# Should return state file
AWS_PROFILE=staging aws s3 cp \
  s3://bluemoxon-terraform-state/bluemoxon/staging/terraform.tfstate \
  .tmp/test-state.json

# Should show lock table
AWS_PROFILE=staging aws dynamodb describe-table \
  --table-name bluemoxon-terraform-locks \
  --region us-west-2
```

### Test 2: Terraform Output Reading

```bash
cd infra/terraform

# Initialize with staging backend
terraform init -backend-config="key=bluemoxon/staging/terraform.tfstate"

# Read outputs (should work now)
terraform output cognito_user_pool_id
terraform output api_url
```

### Test 3: GitHub Actions Workflow

1. Re-apply PR #291 changes to `deploy.yml`
2. Push to staging branch
3. Workflow should successfully read Terraform outputs

## Rollback Plan

If issues occur:

### Option 1 Rollback

```bash
# Remove the inline policy
AWS_PROFILE=staging aws iam delete-role-policy \
  --role-name github-actions-deploy \
  --policy-name terraform-state-access
```

### Option 2 Rollback

```bash
# Disable module
# Set enable_github_oidc = false in staging.tfvars
terraform apply -var-file=envs/staging.tfvars -var="db_password=$STAGING_DB_PASSWORD"
```

## Related Issues/PRs

- Issue #293 - This issue
- PR #291 - Auto-sync deploy config from Terraform (merged to staging, needs this fix)
- PR #292 - Revert workaround (merged to main)

## Next Steps After Fix

1. Re-implement PR #291's Terraform output reading in `deploy.yml`
2. Remove static config files approach
3. Test end-to-end deploy on staging
4. Promote to production

## Cost Impact

None - uses existing IAM permissions (no new resources).
