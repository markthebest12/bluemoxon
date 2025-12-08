# Staging Authentication Investigation

**Date:** 2025-12-08
**Status:** In Progress
**Issue:** User cannot login to staging.app.bluemoxon.com

## Problem Statement

User gets "Invalid email or password" when attempting to login at https://staging.app.bluemoxon.com with mjramos76@gmail.com.

## Root Cause Analysis

### Issue 1: Frontend Cognito Configuration Mismatch

The frontend was built with **production Cognito IDs** instead of staging:

| Config | Frontend Had (Wrong) | Staging Actual |
|--------|---------------------|----------------|
| User Pool ID | `us-west-2_PvdIpXVKF` | `us-west-2_5pOhFH6LN` |
| Client ID | `3ndaok3psd2ncqfjrdb57825he` | `7h1b144ggk7j4dl9vr94ipe6k5` |
| Domain | `bluemoxon.auth...` | `bluemoxon-staging.auth...` |

**Cause:** Two competing deploy workflows:
- `deploy.yml` - Reads from `infra/config/staging.json` (correct pattern)
- `deploy-staging.yml` - Had hardcoded production Cognito IDs (wrong)

**Fix Applied:**
- Deleted `deploy-staging.yml` (redundant)
- Updated `infra/config/staging.json` with correct client ID

### Issue 2: Config File Drift from Terraform

The `infra/config/staging.json` file had stale Cognito client ID (`48ik81mrpc6anouk234sq31fbt`) that didn't match the Terraform-managed Cognito client (`7h1b144ggk7j4dl9vr94ipe6k5`).

**Cause:** When Cognito client was recreated/imported by Terraform, the config file wasn't updated.

**Fix Applied:** Manually updated config file.

**Prevention Needed:** Automated sync from Terraform outputs to config files (see GitHub issue #140).

### Issue 3: Fundamental Architecture Mismatch (UNSOLVED)

Staging has a **separate Cognito user pool** from production, but the **database is synced from production**.

This creates a UUID mismatch:

```
Production:
  - Cognito user: sub="abc-123-prod"
  - Database user: cognito_id="abc-123-prod" ✓ matches

Staging (after DB sync):
  - Cognito user: sub="xyz-789-staging" (different UUID)
  - Database user: cognito_id="abc-123-prod" (from prod sync)

Result: JWT contains "xyz-789-staging" but DB expects "abc-123-prod" ✗
```

## Changes Made

| File/Resource | Change |
|---------------|--------|
| `infra/config/staging.json` | Fixed `app_client_id` to `7h1b144ggk7j4dl9vr94ipe6k5` |
| `.github/workflows/deploy-staging.yml` | Deleted (was redundant with hardcoded wrong values) |
| AWS Cognito | Set password for mjramos76@gmail.com, status now CONFIRMED |

## Current State

```
Staging Cognito Pool: us-west-2_5pOhFH6LN
Staging Cognito Client: 7h1b144ggk7j4dl9vr94ipe6k5
Frontend bundle: ✅ Now has correct IDs
API health check: ✅ All healthy (DB, S3, Cognito)
Login flow: ❓ May still fail due to Cognito/DB UUID mismatch
```

### Staging Cognito Users

Only 2 users exist in staging Cognito:
- mjramos76@gmail.com (CONFIRMED)
- kevin.a.klein@disney.com (FORCE_CHANGE_PASSWORD)

## Architecture Decision Required

### Option A: Shared Cognito Pool

Frontend and API both use **production Cognito pool**.

**Pros:**
- No UUID mismatch - users authenticate against same pool as prod
- Simpler - no Cognito sync needed
- Users have same credentials as prod

**Cons:**
- Staging isn't fully isolated
- Can't test Cognito configuration changes
- Production Cognito callbacks need staging URLs

### Option B: Separate Cognito with User Sync

Staging has own Cognito pool, sync users from prod Cognito.

**Pros:**
- True isolation
- Can test Cognito changes safely

**Cons:**
- Complex - need to sync Cognito users AND update DB cognito_id mappings
- DB sync Lambda needs enhancement
- Users may have different passwords in staging

### Option C: Bypass Auth for Staging

Use API key authentication only, disable Cognito for staging.

**Pros:**
- Simple for testing
- No auth complexity

**Cons:**
- Can't test auth flows
- Not representative of production

### Recommendation

**Option A (Shared Cognito)** is simplest and was the original design (the deleted `deploy-staging.yml` had comments saying "Shared Cognito (uses prod Cognito pool)").

To implement:
1. Update `infra/config/staging.json` to use prod Cognito IDs
2. Update `infra/terraform/envs/staging.tfvars` to disable Cognito module OR
3. Keep staging Cognito for API-side validation but frontend uses prod

## Documentation Gaps Identified

1. **No documented decision** on staging Cognito architecture
2. **Config file not synced** when Terraform recreates resources
3. **CLAUDE.md** doesn't explain staging auth strategy
4. **No validation** in deploy workflow checking Cognito consistency

## Related GitHub Issues

- **#142** - Staging infrastructure self-validated rebuild (main tracking)
- **#141** - Post-apply validation needed
- **#140** - Auto-update GitHub vars after Terraform apply
- **#139** - ACM certificates not in Terraform
- **#138** - VPC endpoints not in Terraform
- **#120** - "User does not exist" Cognito errors (closed, but related)

## Key Files

```
infra/config/staging.json           # Frontend config source of truth
infra/config/production.json        # Prod config for reference
infra/terraform/envs/staging.tfvars # Terraform variables
infra/terraform/outputs.tf          # Cognito outputs defined here
.github/workflows/deploy.yml        # Single deploy workflow
docs/STAGING_ENVIRONMENT_PLAN.md    # Needs Cognito strategy update
CLAUDE.md                           # Needs staging auth documentation
```

## Next Steps

1. [ ] **Decide** staging auth architecture (A, B, or C)
2. [ ] **Update** `docs/STAGING_ENVIRONMENT_PLAN.md` with decision
3. [ ] **Update** `CLAUDE.md` with staging auth guidance
4. [ ] **Implement** chosen approach
5. [ ] **Add validation** to deploy workflow for Cognito consistency
6. [ ] **Test** end-to-end login after fix
7. [ ] **Consider** Terraform → config file automation (#140)
