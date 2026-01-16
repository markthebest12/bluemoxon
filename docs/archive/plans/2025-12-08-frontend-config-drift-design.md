# Frontend Config Drift Solution Design

**Date**: 2025-12-08
**Status**: Approved
**Problem**: Frontend config (`infra/config/*.json`) becomes stale when Terraform recreates Cognito, causing login failures after deploys.

## Problem Statement

When Terraform destroys/recreates Cognito (or any resource the frontend depends on):

1. `infra/config/staging.json` has hardcoded Cognito pool ID
2. Terraform creates NEW pool with different ID
3. Config file is NOT updated automatically
4. CI/CD reads stale config → frontend built with wrong Cognito ID → login breaks
5. Requires manual debugging to find the mismatch

## Chosen Solution

**Approach**: Fetch Cognito config directly from AWS APIs at deploy time, with fallback to config files for bootstrapping.

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| When to sync | At deploy time (not post-terraform) | Bulletproof - can't deploy stale config |
| How to get config | AWS API calls (not terraform output) | Faster (~5s vs ~30s), no state access needed |
| Fallback | Config file if API returns empty | Handles bootstrap and API failures |

## Implementation

### Deploy Workflow Changes

Modify `.github/workflows/deploy.yml` configure job:

```yaml
configure:
  name: Configure Environment
  runs-on: ubuntu-latest
  outputs:
    environment: ${{ steps.config.outputs.environment }}
    cognito_user_pool_id: ${{ steps.config.outputs.cognito_user_pool_id }}
    cognito_client_id: ${{ steps.config.outputs.cognito_client_id }}
    cognito_domain: ${{ steps.config.outputs.cognito_domain }}
    # ... other outputs unchanged

  steps:
    - uses: actions/checkout@v6
      with:
        sparse-checkout: |
          infra/config
        sparse-checkout-cone-mode: false

    - name: Configure AWS credentials via OIDC
      uses: aws-actions/configure-aws-credentials@v5
      with:
        role-to-assume: ${{ github.ref_name == 'main' && secrets.AWS_DEPLOY_ROLE_ARN || secrets.AWS_STAGING_ROLE_ARN }}
        aws-region: us-west-2

    - name: Load environment configuration
      id: config
      run: |
        # Determine environment
        if [[ "${{ github.ref_name }}" == "main" ]]; then
          ENV="production"
          CONFIG_FILE="infra/config/production.json"
        else
          ENV="staging"
          CONFIG_FILE="infra/config/staging.json"
        fi
        echo "environment=$ENV" >> $GITHUB_OUTPUT

        # Try to get Cognito config from AWS (fresh, always correct)
        POOL_NAME="bluemoxon-${ENV}"
        POOL_ID=$(aws cognito-idp list-user-pools --max-results 60 \
          --query "UserPools[?Name=='${POOL_NAME}'].Id | [0]" \
          --output text 2>/dev/null || echo "")

        if [ -n "$POOL_ID" ] && [ "$POOL_ID" != "None" ]; then
          echo "Found Cognito pool via AWS API: $POOL_ID"

          # Get client ID
          CLIENT_ID=$(aws cognito-idp list-user-pool-clients --user-pool-id "$POOL_ID" \
            --query "UserPoolClients[0].ClientId" --output text)

          # Get domain
          DOMAIN=$(aws cognito-idp describe-user-pool --user-pool-id "$POOL_ID" \
            --query "UserPool.Domain" --output text)

          echo "cognito_user_pool_id=$POOL_ID" >> $GITHUB_OUTPUT
          echo "cognito_client_id=$CLIENT_ID" >> $GITHUB_OUTPUT
          echo "cognito_domain=${DOMAIN}.auth.us-west-2.amazoncognito.com" >> $GITHUB_OUTPUT
        else
          # Fallback to config file (bootstrapping or API failure)
          echo "::warning::Cognito pool not found via AWS API, using config file as fallback"
          echo "cognito_user_pool_id=$(jq -r '.cognito.user_pool_id' $CONFIG_FILE)" >> $GITHUB_OUTPUT
          echo "cognito_client_id=$(jq -r '.cognito.app_client_id' $CONFIG_FILE)" >> $GITHUB_OUTPUT
          echo "cognito_domain=$(jq -r '.cognito.domain' $CONFIG_FILE)" >> $GITHUB_OUTPUT
        fi

        # Other config from file (these don't change with terraform recreate)
        echo "api_url=$(jq -r '.urls.api' $CONFIG_FILE)" >> $GITHUB_OUTPUT
        echo "app_url=$(jq -r '.urls.app' $CONFIG_FILE)" >> $GITHUB_OUTPUT
        # ... rest of config loading unchanged
```

### IAM Permissions Required

The deploy role needs these Cognito permissions (likely already has them):

```json
{
  "Effect": "Allow",
  "Action": [
    "cognito-idp:ListUserPools",
    "cognito-idp:ListUserPoolClients",
    "cognito-idp:DescribeUserPool"
  ],
  "Resource": "*"
}
```

### Config File Role Change

Config files (`infra/config/*.json`) become **fallback/bootstrap** instead of source of truth:

- Used during first deploy before Cognito exists
- Used if AWS API calls fail
- Should still be kept reasonably up-to-date for documentation

## Flow Diagram

```
Push to main/staging
    │
    ▼
Configure job runs
    │
    ▼
AWS OIDC authentication
    │
    ▼
Query AWS: list-user-pools for "bluemoxon-{env}"
    │
    ├─ Found ──────────────────────────────┐
    │                                      │
    ▼                                      ▼
Fallback to config file         Use fresh AWS values
(+ warning annotation)                     │
    │                                      │
    └──────────────────────────────────────┘
                      │
                      ▼
            Build frontend with
            correct VITE_* env vars
                      │
                      ▼
                   Deploy
```

## What This Fixes

| Scenario | Before | After |
|----------|--------|-------|
| Terraform recreates Cognito | Deploy fails, manual config update needed | Auto-detects new pool ID |
| Fresh environment setup | Must update config file first | Config file used as bootstrap |
| Config file out of date | Silent failure, broken login | Ignored (AWS API used), warning logged |

## Testing Plan

1. **Verify AWS API queries work**: Run the configure job in isolation, confirm it finds the pool
2. **Test fallback**: Temporarily change pool name filter to non-existent, confirm fallback triggers with warning
3. **End-to-end**: After terraform recreate, deploy should work without manual intervention

## Future Considerations

- Could extend this pattern to other dynamic resources (API Gateway ID, CloudFront distribution)
- Could add a "config drift detection" step that warns if config file doesn't match AWS
- Consider SSM Parameter Store for cross-workflow config sharing (if more services need this pattern)
