# Staging-Production Infrastructure Parity

**Date:** 2025-12-13
**Status:** In Progress
**Goal:** Full code and infrastructure parity between staging and production, with all resources under Terraform management.

## Problem Statement

Production and staging have diverged:
- **Code:** 68 commits in staging not yet in production
- **Infrastructure:** Production resources managed manually; staging managed by Terraform
- **Config:** `prod.tfvars` has `enable_lambda=false`, `enable_cloudfront=false`, etc.
- **Worker Lambda:** Exists in staging, missing in production

Current state violates infrastructure-as-code principles and creates deployment friction.

## Scope

### In Scope
1. All 68 code commits promoted from staging → main
2. Production Lambda, CloudFront, RDS, VPC resources imported into Terraform
3. Worker Lambda created in production (SQS + Lambda)
4. Same Terraform modules manage both environments
5. Fix staging bug: `ANALYSIS_QUEUE_NAME` env var not set

### Out of Scope
- Data migration (prod books stay in prod)
- Prod → staging data sync (separate task)

## Current Drift Analysis

### Staging (Forward Drift - Code Ahead of Infra)

| Resource | Change Needed | Impact |
|----------|---------------|--------|
| API Lambda | Add `ANALYSIS_QUEUE_NAME` env var | **Fixes async analysis bug** |
| Scraper Lambda | Add S3 IAM policy | Allows image uploads |
| Scraper Lambda | Timeout 120→90 | API Gateway compatibility |
| All Lambdas | X-Ray tracing → Active | Observability |

### Production (Resources Not in Terraform)

| Resource | Current State | Target State |
|----------|---------------|--------------|
| Lambda `bluemoxon-api` | Manual | Terraform-managed |
| CloudFront `E16BJX90QWQNQO` (frontend) | Manual (OAC) | Terraform-managed |
| CloudFront `E2IUCDBKX8CLOH` (images) | Manual (OAC) | Terraform-managed |
| RDS `bluemoxon-db` | Manual | Terraform-managed |
| NAT Gateway | Manual | Terraform-managed |
| Worker Lambda | Does not exist | Create via Terraform |

## Implementation Plan

### Phase 1: Fix Staging + Apply Pending Terraform

**Goal:** Clear forward drift in staging, fix async analysis bug.

```bash
cd infra/terraform
AWS_PROFILE=staging terraform apply -var-file=envs/staging.tfvars -var="db_password=$STAGING_DB_PASSWORD"
```

**Changes applied:**
- Lambda gets `ANALYSIS_QUEUE_NAME` env var
- Scraper gets S3 IAM policy
- Scraper timeout adjusted
- X-Ray tracing enabled

**Validation:**
- Test async analysis in staging UI
- `terraform plan` shows no changes

### Phase 2: Code Promotion (Staging → Main)

**Goal:** Promote 68 commits to production.

```bash
gh pr create --base main --head staging --title "chore: Promote staging to production"
# Wait for CI
gh pr merge --squash
```

**Key features being promoted:**
- eBay listing scraper + import
- Async analysis jobs (SQS + Worker Lambda)
- Wayback Archive integration
- Paste-to-extract order details
- Binder tier scoring
- Analysis enrichment (FMV, binder extraction)

### Phase 3: Import Production Resources into Terraform

**Goal:** Bring existing prod resources under Terraform management.

#### Step 3.1: Update prod.tfvars

```hcl
# Change from:
enable_cloudfront = false
enable_lambda = false
enable_database = false
enable_nat_gateway = false

# To:
enable_cloudfront = true
enable_lambda = true
enable_database = true
enable_nat_gateway = true
```

#### Step 3.2: Import Resources

```bash
cd infra/terraform
AWS_PROFILE=prod terraform init -reconfigure -backend-config="key=bluemoxon/prod/terraform.tfstate"

# Lambda
terraform import 'module.lambda[0].aws_lambda_function.this' bluemoxon-api
terraform import 'module.lambda[0].aws_iam_role.lambda_exec' bluemoxon-api-role
terraform import 'module.lambda[0].aws_cloudwatch_log_group.lambda' /aws/lambda/bluemoxon-api

# CloudFront (frontend)
terraform import 'module.frontend_cdn[0].aws_cloudfront_distribution.this' E16BJX90QWQNQO
terraform import 'module.frontend_cdn[0].aws_cloudfront_origin_access_identity.this' <OAI_ID>

# CloudFront (images)
terraform import 'module.images_cdn[0].aws_cloudfront_distribution.this' E2IUCDBKX8CLOH
terraform import 'module.images_cdn[0].aws_cloudfront_origin_access_identity.this' <OAI_ID>

# Database
terraform import 'module.database[0].aws_db_instance.this' bluemoxon-db
terraform import 'module.database[0].aws_security_group.this' <SG_ID>

# VPC Networking
terraform import 'module.vpc_networking[0].aws_nat_gateway.this[0]' <NAT_GW_ID>
terraform import 'module.vpc_networking[0].aws_eip.nat[0]' <EIP_ALLOC_ID>
terraform import 'module.vpc_networking[0].aws_route_table.private[0]' <RTB_ID>
```

#### Step 3.3: Reconcile Configuration

After import, run `terraform plan` and adjust Terraform config to match existing resource attributes (e.g., memory size, timeout, environment variables).

**Critical:** Do NOT let Terraform change production resources unexpectedly. Review plan carefully.

### Phase 4: Create Worker Lambda in Production

**Goal:** Enable async analysis in production.

After Phase 3 resources are imported and stable:

1. Ensure `analysis_worker` module is enabled in prod
2. Run `terraform apply` to create:
   - SQS queue: `bluemoxon-analysis-jobs`
   - SQS DLQ: `bluemoxon-analysis-jobs-dlq`
   - Lambda: `bluemoxon-analysis-worker`
   - IAM role + policies
   - EventSource mapping (SQS → Lambda)

3. Update `infra/config/production.json`:
```json
"lambda": {
  "function_name": "bluemoxon-api",
  "worker_function_name": "bluemoxon-analysis-worker",
  ...
}
```

4. Deploy to update workflow config

### Phase 5: Validate and Clean Up

**Validation:**
```bash
# Both envs should show no drift
AWS_PROFILE=staging terraform plan -var-file=envs/staging.tfvars -detailed-exitcode
AWS_PROFILE=prod terraform plan -var-file=envs/prod.tfvars -detailed-exitcode
```

**Clean up:**
- Archive `docs/STAGING_INFRASTRUCTURE_CHANGES.md` (manual hacks now in Terraform)
- Update `docs/INFRASTRUCTURE.md` with new parity state
- Test async analysis in production

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Terraform destroys/recreates prod resources | Review `terraform plan` carefully; use `lifecycle { prevent_destroy = true }` |
| CloudFront OAC vs OAI mismatch | May need to adjust module to support OAC or accept OAI |
| RDS modification causes downtime | Import only; don't let Terraform modify RDS attributes |
| Secrets Manager password rotation | Use actual password, not dummy, during import |

## Rollback Plan

- **Phase 1:** Staging only - low risk
- **Phase 2:** Revert PR if issues
- **Phase 3:** If import fails, `terraform state rm` the resource and continue manually
- **Phase 4:** Worker Lambda is additive - can delete if issues

## Success Criteria

1. `terraform plan` shows no changes for both staging and prod
2. Async analysis works in both environments
3. No resources managed outside Terraform
4. `prod.tfvars` has same feature flags enabled as `staging.tfvars`
5. Deploy workflow succeeds for both Lambda and Worker Lambda
