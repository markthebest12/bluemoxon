# Infrastructure Governance

## Problem Statement

Production and staging environments have drifted due to:

1. Production pre-dating Terraform adoption
2. `enable_*=false` flags creating escape hatches
3. Documentation not generated from Terraform outputs
4. No automated drift detection

## Remediation Plan

### Phase 1: Complete Terraform Import (Priority: HIGH)

Import all production resources that currently have `enable_*=false`:

```bash
# Resources to import:
# 1. Cognito User Pool + Client
terraform import 'module.cognito[0].aws_cognito_user_pool.this' us-west-2_POOLID

# 2. Lambda Function + IAM Role
terraform import 'module.lambda[0].aws_lambda_function.this' bluemoxon-api

# 3. CloudFront Distributions (requires OAI→OAC migration OR module update)
# Option A: Update module to support OAC
# Option B: Migrate prod to OAI during maintenance window

# 4. RDS Instance (already exists, import carefully)
terraform import 'module.database[0].aws_db_instance.this' bluemoxon-db
```

### Phase 2: Eliminate enable_* Divergence

Goal: Both `staging.tfvars` and `prod.tfvars` should have identical `enable_*` flags.

| Flag | Current Prod | Target | Action Required |
|------|--------------|--------|-----------------|
| enable_cloudfront | false | true | Update module for OAC or migrate prod |
| enable_cognito | false | true | Import existing pool, handle users |
| enable_lambda | false | true | Import function, migrate IAM |
| enable_database | false | true | Import RDS, careful with credentials |

### Phase 3: Auto-Generate Documentation

Create script to update CLAUDE.md from Terraform:

```bash
#!/bin/bash
# scripts/update-claude-md.sh

# Extract values from Terraform
cd infra/terraform

STAGING_COGNITO_POOL=$(AWS_PROFILE=staging terraform output -raw cognito_user_pool_id 2>/dev/null || echo "N/A")
STAGING_COGNITO_CLIENT=$(AWS_PROFILE=staging terraform output -raw cognito_client_id 2>/dev/null || echo "N/A")

# Update CLAUDE.md with sed or envsubst
sed -i '' "s/Pool ID: .*/Pool ID: ${STAGING_COGNITO_POOL}/" ../CLAUDE.md
sed -i '' "s/Client ID: .*/Client ID: ${STAGING_COGNITO_CLIENT}/" ../CLAUDE.md
```

Add to CI:

```yaml
# .github/workflows/ci.yml
- name: Validate documentation matches Terraform
  run: |
    ./scripts/validate-claude-md.sh
    if [ $? -ne 0 ]; then
      echo "::error::CLAUDE.md contains stale Terraform values"
      exit 1
    fi
```

### Phase 4: Drift Detection

Add scheduled workflow:

```yaml
# .github/workflows/drift-detection.yml
name: Terraform Drift Detection

on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC

jobs:
  detect-drift:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [staging, prod]
    steps:
      - uses: actions/checkout@v4

      - name: Terraform Plan (Drift Check)
        run: |
          cd infra/terraform
          terraform init
          terraform plan -detailed-exitcode -var-file=envs/${{ matrix.environment }}.tfvars
        env:
          AWS_PROFILE: ${{ matrix.environment }}
        continue-on-error: true
        id: plan

      - name: Alert on Drift
        if: steps.plan.outcome == 'failure'
        run: |
          echo "::error::Terraform drift detected in ${{ matrix.environment }}"
          # Send Slack/email notification
```

### Phase 5: Prevent Console Access

1. **Remove direct console access** for day-to-day operations
2. **Use SSO with read-only by default**, require approval for write
3. **All changes via PR** → Terraform plan in CI → Apply on merge

## Governance Rules

### Rule 1: No enable_* Divergence

```
FORBIDDEN: staging.tfvars and prod.tfvars having different enable_* values
EXCEPTION: Only during active migration with documented timeline
```

### Rule 2: No Manual AWS Changes

```
FORBIDDEN: Creating/modifying resources via Console or CLI without Terraform
EXCEPTION: Emergency break-glass with mandatory follow-up:
  1. Document in docs/MANUAL_CHANGES.md within 1 hour
  2. Create GitHub issue to terraformize within 24 hours
  3. Complete terraformization within 1 sprint
```

### Rule 3: Documentation as Code

```
REQUIRED: Values in CLAUDE.md must be generated from terraform output
VALIDATION: CI blocks merge if documentation contains hardcoded infrastructure values
```

## Migration Timeline

| Week | Action |
|------|--------|
| 1 | Import Cognito (prod) |
| 2 | Import Lambda + IAM (prod) |
| 3 | Update CloudFront module for OAC support |
| 4 | Import CloudFront distributions |
| 5 | Import RDS (maintenance window) |
| 6 | Remove all enable_*=false from prod.tfvars |
| 7 | Enable drift detection workflow |
| 8 | Restrict console access |

## Success Criteria

- [ ] `diff staging.tfvars prod.tfvars` shows only environment-specific values (names, ARNs), not structural differences
- [ ] `terraform plan` shows "No changes" for both environments
- [ ] CLAUDE.md values match `terraform output`
- [ ] Drift detection running daily with zero alerts
- [ ] No AWS console write access for non-emergency use
