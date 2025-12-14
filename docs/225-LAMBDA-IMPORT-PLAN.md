# Issue #225: Import Production Lambda into Terraform

## Overview

Production Lambda (`bluemoxon-api`) is currently managed outside Terraform, creating drift risk and deployment inconsistencies. This plan standardizes configuration between environments and imports the production Lambda into Terraform management.

## Design Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Approach** | Standardize first, then import | Reduces variables during import; validates changes in staging |
| **Env Vars** | New unified `BMX_` prefix | Clean break avoids legacy confusion; explicit namespace |
| **API Key Auth** | Hash-based (`BMX_API_KEY_HASH`) | Matches current prod pattern; secure |
| **Memory/Timeout** | 512 MB / 600s (both envs) | Buffer for prompt iteration; can reduce later |
| **IAM Role** | Module-created role | Consistent naming; easier to maintain |

## Current State Analysis

### Lambda Configuration Drift

| Setting | Staging | Production | Target |
|---------|---------|------------|--------|
| Memory | 256 MB | 512 MB | **512 MB** |
| Timeout | 30s | 600s | **600s** |
| IAM Role | `bluemoxon-staging-api-exec-role` | `bluemoxon-lambda-role` | `bluemoxon-api-exec-role` |

### Environment Variable Drift

| Purpose | Staging | Production | Target |
|---------|---------|------------|--------|
| Images bucket | `IMAGES_BUCKET` | `S3_BUCKET` | `BMX_IMAGES_BUCKET` |
| CDN URL | `IMAGES_CDN_URL` | `CLOUDFRONT_URL` | `BMX_IMAGES_CDN_URL` |
| API key hash | `API_KEY_HASH` | `API_KEY_HASH` | `BMX_API_KEY_HASH` |
| Cognito pool | `cognito_user_pool_id` | `COGNITO_USER_POOL_ID` | `BMX_COGNITO_USER_POOL_ID` |
| Cognito client | `cognito_client_id` | `COGNITO_CLIENT_ID` | `BMX_COGNITO_CLIENT_ID` |
| Allowed emails | `ALLOWED_EDITOR_EMAILS` | `ALLOWED_EDITOR_EMAILS` | `BMX_ALLOWED_EDITOR_EMAILS` |

## Implementation Plan

### Phase 1: Backend Code Changes (PR #1)

Update `backend/app/core/config.py` to read from `BMX_*` environment variables with fallback to current names for backwards compatibility during rollout.

**Files to modify:**
- `backend/app/core/config.py` - Add `BMX_` prefix support

**Acceptance criteria:**
- Code reads `BMX_*` vars first, falls back to old names
- All tests pass
- No functional change to current deployments

### Phase 2: Standardize Staging (PR #2)

Update staging Terraform to use standardized configuration.

**Files to modify:**
- `infra/terraform/envs/staging.tfvars` - Update memory, timeout
- `infra/terraform/main.tf` - Update env var names in Lambda module call

**Changes:**
```hcl
# staging.tfvars
lambda_memory_size = 512
lambda_timeout     = 600
```

**Acceptance criteria:**
- `terraform plan` shows only expected changes
- `terraform apply` succeeds
- Deep health check passes
- Smoke tests pass

### Phase 3: Import Production Lambda (PR #3)

Import production Lambda into Terraform state and migrate to module-created IAM role.

**Step-by-step:**

1. **Update prod.tfvars:**
```hcl
enable_lambda = true
lambda_function_name_override = "bluemoxon-api"
# Remove: lambda_function_name_external, lambda_invoke_arn_external, external_lambda_role_name
```

2. **Update main.tf environment variables** to use `BMX_*` naming

3. **Import Lambda function:**
```bash
cd infra/terraform
AWS_PROFILE=bluemoxon terraform import \
  -var-file=envs/prod.tfvars \
  -var="db_password=$PROD_DB_PASSWORD" \
  'module.lambda[0].aws_lambda_function.this' \
  bluemoxon-api
```

4. **Plan and verify:**
```bash
AWS_PROFILE=bluemoxon terraform plan \
  -var-file=envs/prod.tfvars \
  -var="db_password=$PROD_DB_PASSWORD"
```

5. **Apply:**
```bash
AWS_PROFILE=bluemoxon terraform apply \
  -var-file=envs/prod.tfvars \
  -var="db_password=$PROD_DB_PASSWORD"
```

**Acceptance criteria:**
- Lambda continues running during apply
- New IAM role created with all necessary permissions
- Deep health check passes
- Smoke tests pass

### Phase 4: Cleanup (PR #4)

1. Remove fallback code from `config.py`
2. Delete old IAM role `bluemoxon-lambda-role` via console/CLI
3. Update documentation

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Lambda downtime during role switch | Low | High | Lambda role updates are atomic; no restart needed |
| Env var typo breaks service | Medium | High | Deploy to staging first; comprehensive testing |
| Missing IAM permissions | Medium | High | Audit existing role; copy all policies |
| Terraform import fails | Low | Low | Can retry; existing Lambda unaffected |

## Rollback Plan

**Phase 2 rollback (staging):**
```bash
# Revert tfvars and apply
git checkout HEAD~1 -- infra/terraform/envs/staging.tfvars
terraform apply -var-file=envs/staging.tfvars
```

**Phase 3 rollback (production):**
1. Old IAM role still exists until manual deletion
2. Revert prod.tfvars to `enable_lambda = false`
3. Apply to remove Lambda from state (doesn't delete Lambda)
4. Lambda continues using old role

## Verification Checklist

- [ ] Staging deep health passes after Phase 2
- [ ] Staging smoke tests pass after Phase 2
- [ ] Production deep health passes after Phase 3
- [ ] Production smoke tests pass after Phase 3
- [ ] No 5xx errors in CloudWatch after each phase
- [ ] Version header matches expected deploy
- [ ] Old IAM role deleted in Phase 4

## Timeline

This work should be done sequentially with validation between each phase:
1. Phase 1 (Backend) → Merge to staging → Deploy
2. Phase 2 (Staging TF) → Apply → Validate 24h
3. Phase 3 (Prod TF) → Apply → Validate 24h
4. Phase 4 (Cleanup) → Complete
