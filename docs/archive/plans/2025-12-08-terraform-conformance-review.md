# Terraform Conformance Review & Rebuild Test

**Date:** 2025-12-08
**Status:** In Progress
**Goal:** Ensure staging can be torn down and rebuilt from Terraform, conforming to HashiCorp style guides

## References

- <https://developer.hashicorp.com/terraform/tutorials/modules/pattern-module-creation>
- <https://developer.hashicorp.com/terraform/language/style>

## Audit Summary

**Overall: GOOD - No critical issues that would break destroy + apply**

| Area | Status | Notes |
|------|--------|-------|
| File organization | ✅ Good | Missing `versions.tf` in all 10 modules |
| Variable ordering | ⚠️ 2 modules | `lambda` and `db-sync-lambda` need reordering |
| Output ordering | ✅ Excellent | All alphabetical |
| Variable completeness | ✅ Excellent | All have type, description, defaults |
| Naming conventions | ✅ Perfect | All underscore_separated |
| Meta-argument ordering | ✅ Good | count/for_each first, lifecycle/depends_on last |
| Output exports | ✅ Excellent | Comprehensive exports |
| Backend config | ✅ Correct | S3 + DynamoDB locks, env-specific keys |
| Environment separation | ✅ Excellent | staging.tfvars and prod.tfvars |
| Terraform formatting | ✅ Passed | `terraform fmt -check` clean |
| Destroy/Apply safety | ✅ Safe | No hardcoded values, proper lifecycles |

## Modules (10 total)

```text
infra/terraform/modules/
├── api-gateway/
├── cloudfront/
├── cognito/
├── db-sync-lambda/
├── github-oidc/
├── lambda/
├── rds/
├── s3/
├── secrets/
└── vpc-networking/
```

## Required Fixes

### High Priority (Conformance)

#### 1. Add `versions.tf` to all 10 modules

Each module needs this file:

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

**Files to create:**

- [ ] `modules/api-gateway/versions.tf`
- [ ] `modules/cloudfront/versions.tf`
- [ ] `modules/cognito/versions.tf`
- [ ] `modules/db-sync-lambda/versions.tf`
- [ ] `modules/github-oidc/versions.tf`
- [ ] `modules/lambda/versions.tf`
- [ ] `modules/rds/versions.tf`
- [ ] `modules/s3/versions.tf`
- [ ] `modules/secrets/versions.tf`
- [ ] `modules/vpc-networking/versions.tf`

#### 2. Fix variable ordering (alphabetical)

**`modules/lambda/variables.tf`:**

- Swap `environment` and `environment_variables` (environment_variables should come first alphabetically)

**`modules/db-sync-lambda/variables.tf`:**

- Move `cognito_user_pool_id` to correct alphabetical position (near top, after nothing or before `environment_variables`)

### Medium Priority (Style Improvements)

#### 3. Add validation rules

Consider adding to:

- **RDS:** `instance_class` validation against allowed values
- **Lambda:** `memory_size` validation (128-10240 MB)
- **API Gateway:** `cors_max_age` validation

#### 4. Update module READMEs

Document:

- RDS: `deletion_protection` blocks destroy unless manually disabled
- Lambda: `filename` changes ignored by lifecycle (code via CI/CD)
- Constraints and dependencies between modules

### Low Priority (Nice-to-Have)

#### 5. Create conformance checklist for future modules

Document in `infra/terraform/TERRAFORM.md` or new file.

## Rebuild Test Plan

### Decision Needed: Database Handling

**Options:**

1. **Full destroy including RDS** - True test, staging data lost (resync from prod after)
2. **Preserve RDS** - `terraform state rm` before destroy, re-import after
3. **Snapshot + restore** - Take snapshot, destroy, restore from snapshot

**Decision:** TBD (user choosing option 1 for true reproducibility test)

### Pre-Destroy Checklist

- [ ] Document current Terraform state: `terraform state list > .tmp/state-before.txt`
- [ ] Note any resources NOT in Terraform (check STAGING_INFRASTRUCTURE_CHANGES.md)
- [ ] Verify prod database sync Lambda can repopulate data
- [ ] Take RDS snapshot (if option 3)
- [ ] Notify team staging will be down

### Destroy Sequence

```bash
cd infra/terraform

# Initialize for staging
terraform init -backend-config="key=bluemoxon/staging/terraform.tfstate"

# Plan destroy
terraform plan -destroy -var-file=envs/staging.tfvars -out=destroy.tfplan

# Review plan carefully!
terraform show destroy.tfplan

# Execute destroy
terraform apply destroy.tfplan
```

### Apply Sequence

```bash
# Plan apply
terraform plan -var-file=envs/staging.tfvars -out=apply.tfplan

# Review plan
terraform show apply.tfplan

# Execute apply
terraform apply apply.tfplan
```

### Post-Apply Validation

- [ ] `terraform state list` matches expected resources
- [ ] API health check: `curl https://staging.api.bluemoxon.com/api/v1/health/deep`
- [ ] Frontend loads: `curl -I https://staging.app.bluemoxon.com`
- [ ] Cognito user pool exists and has correct config
- [ ] RDS instance accessible
- [ ] Lambda functions deployed (code will need CI/CD redeploy)
- [ ] CloudFront distributions active
- [ ] S3 buckets exist with correct policies

### Post-Rebuild Tasks

- [ ] Redeploy Lambda code via CI/CD (Terraform only creates function, not code)
- [ ] Redeploy frontend via CI/CD
- [ ] Resync database from prod: `aws lambda invoke --function-name bluemoxon-staging-db-sync ...`
- [ ] Recreate Cognito users (separate pool from prod)
- [ ] Run `cognito_only` sync to map users
- [ ] Test login flow

## Known Resources NOT in Terraform

From `docs/STAGING_INFRASTRUCTURE_CHANGES.md`:

- ACM certificates (created manually, referenced by ARN in tfvars)
- Route53 records (managed separately)
- VPC endpoints (partially imported)

These need to be documented/imported or recreated manually after destroy.

## Implementation Order

1. **Fix conformance issues** (versions.tf, variable ordering)
2. **Run terraform fmt and validate**
3. **terraform plan** to verify no unintended changes
4. **Update documentation** (READMEs, conformance checklist)
5. **Commit all changes**
6. **Execute destroy + apply test**
7. **Validate and document results**

## Session Context

### Staging Cognito (just fixed today)

- Pool ID: `us-west-2_5pOhFH6LN`
- Client ID: `7h1b144ggk7j4dl9vr94ipe6k5`
- User: `mjramos76@gmail.com` (password changed by user)
- Login: Working as of 2025-12-08

### Recent Changes

- Added `cognito_user_pool_id` to db-sync-lambda module
- Added `cognito_only` mode for user mapping
- Fixed staging login issues

## Next Steps

1. User to decide on database handling for rebuild test (option 1, 2, or 3)
2. Implement conformance fixes
3. Execute rebuild test
4. Document results
