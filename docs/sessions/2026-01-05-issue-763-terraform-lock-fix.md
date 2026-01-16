# Session: Issue #763 - DynamoDB Terraform Lock Table Fix

**Date**: 2026-01-05
**Issue**: <https://github.com/bluemoxon/bluemoxon/issues/763>
**Status**: In Progress

## Problem Summary

DynamoDB table configuration mismatch in Terraform:

- `backends/staging.hcl:4` references: `bluemoxon-terraform-lock-staging`
- `envs/staging.tfvars:42` references: `bluemoxon-terraform-locks` (WRONG)

### Orphaned Tables to Investigate

**Staging (652617421195):**

- `bluemoxon-staging-terraform-locks` - orphaned?
- `bluemoxon-terraform-lock-staging` - ACTUAL (used)
- `bluemoxon-terraform-locks` - orphaned? (wrongly granted)

**Production (266672885920):**

- `bluemoxon-terraform-locks` - ACTUAL (used)
- `bluemoxon-terraform-locks-prod` - orphaned?

## Phases

1. [ ] Fix the mismatch in staging.tfvars
2. [ ] Verify orphaned tables are unused
3. [ ] Delete orphaned tables
4. [ ] Standardize naming convention

## Progress Log

### Entry 1 - Session Start

- Reviewed issue #763
- Created session log for continuity
- Starting brainstorming phase for approach

### Entry 2 - Fix Applied

- Confirmed the mismatch: staging.tfvars:46 referenced wrong table
- Fixed ARN from `bluemoxon-terraform-locks` to `bluemoxon-terraform-lock-staging`
- Terraform fmt and validate passed
- Created PR #845 targeting staging: <https://github.com/markthebest12/bluemoxon/pull/845>
- PR merged and deployed to production

### Entry 3 - Phase 2: Orphan Table Verification

- Scanned all orphaned tables for content
- All contain stale lock entries from old naming conventions
- Safe to delete:
  - Staging: `bluemoxon-staging-terraform-locks` (2 items), `bluemoxon-terraform-locks` (5 items)
  - Prod: `bluemoxon-terraform-locks-prod` (1 item)
- Active tables confirmed working:
  - Staging: `bluemoxon-terraform-lock-staging`
  - Prod: `bluemoxon-terraform-locks`

### Entry 4 - Phase 3: Deleting Orphaned Tables

- Created issue #847 for cleanup work: <https://github.com/markthebest12/bluemoxon/issues/847>
- Deleted 3 orphaned tables:
  - bluemoxon-staging-terraform-locks (staging)
  - bluemoxon-terraform-locks (staging)
  - bluemoxon-terraform-locks-prod (prod)
- Verified only active tables remain:
  - Staging: bluemoxon-terraform-lock-staging
  - Prod: bluemoxon-terraform-locks

### Entry 5 - Phase 4: Naming Standardization

- Created new tables with standardized naming:
  - Staging: bluemoxon-terraform-locks-staging (ACTIVE)
  - Prod: bluemoxon-terraform-locks-prod (ACTIVE)
- Updated all 4 config files (2 backend configs + 2 tfvars)
- Tested terraform init -reconfigure for staging - SUCCESS
- Created PR #848: <https://github.com/markthebest12/bluemoxon/pull/848>

### Entry 6 - Review Feedback Fixes

- Fixed bootstrap script: scripts/bootstrap-staging-terraform.sh
- Fixed documentation: infra/terraform/TERRAFORM.md
- Clarified CI/CD: deploy runs fresh terraform init, no break
- Correct cleanup list:
  - Staging: bluemoxon-terraform-lock-staging (from PR #845)
  - Prod: bluemoxon-terraform-locks (original)
- Added commit c8e1d26 with fixes

### Entry 7 - Production Deployment Complete

- Merged PR #849 (Top Authors fix) to staging alongside #848
- Both staging deploys succeeded
- Created PR #850 to promote staging to main
- Resolved merge conflict (kept new table name)
- Production deploy succeeded with smoke tests passing
- Deleted old tables:
  - Staging: bluemoxon-terraform-lock-staging
  - Prod: bluemoxon-terraform-locks
- Final state: Both environments now use `bluemoxon-terraform-locks-{env}` pattern

## Summary

Issue #763 fully resolved:

- Phase 1: Fixed ARN mismatch (PR #845)
- Phase 2: Verified orphaned tables
- Phase 3: Deleted 3 orphaned tables
- Phase 4: Standardized naming + cleanup (PR #848, #850)

Bonus: PR #849 (Top Authors volume fix) deployed to production
