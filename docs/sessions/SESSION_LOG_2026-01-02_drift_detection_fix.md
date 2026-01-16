# Session Log: Drift Detection Backend Config Fix

**Date:** 2026-01-02
**Issue:** Drift detection workflow failing for production
**Status:** PR #762 created, pending merge and verification

---

## Background

The drift detection workflow was failing with:

```text
Error: User: arn:aws:sts::266672885920:assumed-role/github-actions-deploy/GitHubActions
is not authorized to perform: s3:ListBucket on resource:
"arn:aws:s3:::bluemoxon-terraform-state-prod"
```

### Root Cause Analysis (Systematic Debugging)

**Initial symptom:** AccessDenied on S3 bucket

**Investigation revealed 3 underlying issues:**

| Issue | Details |
|-------|---------|
| **Wrong bucket name** | Workflow used `bluemoxon-terraform-state-prod` but actual bucket is `bluemoxon-terraform-state` |
| **Missing DynamoDB config** | `drift-detection.yml` had no lock table configuration at all |
| **Wrong DynamoDB for staging** | `deploy.yml` used `bluemoxon-terraform-locks` for both envs, but staging should use `bluemoxon-terraform-lock-staging` |

**Root cause:** Backend config was hardcoded in workflows instead of reading from the canonical `backends/*.hcl` files.

### Source of Truth

```text
infra/terraform/backends/prod.hcl     # Production backend config
infra/terraform/backends/staging.hcl  # Staging backend config
```

These files contain bucket, key, region, dynamodb_table, and encrypt settings.

---

## Changes Made

### PR #761 (Merged to staging)

- Quick fix for bucket name only
- **Superseded by PR #762**

### PR #762 (Merged to staging)

- Uses `backends/*.hcl` files as single source of truth
- Both `deploy.yml` and `drift-detection.yml` now use:

  ```yaml
  terraform init -backend-config="backends/prod.hcl"
  # OR
  terraform init -backend-config="backends/staging.hcl"
  ```

- **Verified:** Terraform Init now passes for BOTH staging and production

---

## Next Steps

1. ~~Wait for CI on PR #762~~ - Done
2. ~~Merge PR #762 to staging~~ - Done
3. ~~Trigger drift detection~~ - Done, verified Terraform Init passes for both environments
4. **Promote to main** - Create PR from staging to main
5. **Add drift detection permissions for production** - The prod IAM role needs `enable_github_oidc_drift_detection = true` in `prod.tfvars` and Terraform apply

### Outstanding Issue: Production IAM Permissions

The Terraform Plan step still fails for production because the IAM role lacks read permissions. To fix:

1. Add to `infra/terraform/envs/prod.tfvars`:

   ```hcl
   enable_github_oidc_drift_detection = true
   ```

2. Apply Terraform to production (requires manual apply or separate workflow)
3. Re-run drift detection to verify

---

## Critical Reminders for Future Sessions

### 1. ALWAYS Use Superpowers Skills

Invoke relevant skills BEFORE any action:

- `superpowers:systematic-debugging` - For any bug, failure, or unexpected behavior
- `superpowers:brainstorming` - Before any creative/implementation work
- `superpowers:verification-before-completion` - Before claiming work is done

**If there's even a 1% chance a skill applies, invoke it.**

### 2. NEVER Use Complex Shell Syntax

These trigger permission prompts and break auto-approve:

```bash
# BAD - NEVER USE:
# This is a comment before command    # Comments
command1 \                             # Backslash continuations
  --flag value
$(date +%s)                            # Command substitution
command1 && command2                   # && chaining
command1 || command2                   # || chaining
--password 'Test1234!'                 # ! in quoted strings
```

### 3. ALWAYS Use Simple Commands

```bash
# GOOD - ALWAYS USE:
command1 --flag value                  # Simple single-line
bmx-api GET /books                     # bmx-api for API calls
```

**For sequential operations:** Make separate Bash tool calls instead of using `&&`

```bash
# Instead of: git add . && git commit -m "msg"
# Use TWO separate Bash tool calls:
# Call 1: git add .
# Call 2: git commit -m "msg"
```

---

## Files Modified

- `.github/workflows/deploy.yml` - Use backend config file
- `.github/workflows/drift-detection.yml` - Use backend config file

## Related PRs/Issues

- PR #761 - Initial bucket name fix (merged, superseded)
- PR #762 - Proper DRY fix using backend config files (pending)
