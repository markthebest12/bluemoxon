# Session Log: Opus IAM Fix and FMV Scraper Environment

**Date:** December 31, 2025
**Issues:** #718 (FMV scraper targeting), #719 (Opus AccessDeniedException)
**Status:** COMPLETE - Both fixes deployed and verified

---

## Summary

Both production issues resolved:

1. **#718 FMV Fix**: Deployed via PR #722 → #723. Code now checks `ENVIRONMENT` env var for scraper targeting.
2. **#719 Opus Fix**: IAM policy updated via AWS CLI to add `aws-marketplace:ViewSubscriptions` and `aws-marketplace:Subscribe` permissions.

**Verification:** Opus analysis job for book 553 completed successfully at 07:21 UTC.

---

## Background

### Issue #718: FMV Scraper Targeting (FIXED)

Production eval worker was calling staging scraper Lambda because `get_scraper_environment()` didn't check `ENVIRONMENT` env var.

**Fix applied to `backend/app/config.py:155-169`:**

```python
def get_scraper_environment() -> str:
    return (
        os.getenv("BMX_SCRAPER_ENVIRONMENT")
        or os.getenv("BMX_ENVIRONMENT")
        or os.getenv("ENVIRONMENT", "staging")  # Added ENVIRONMENT check
    )
```

### Issue #719: Opus AccessDeniedException (FIXED)

**Root Cause:** Lambda execution role missing `aws-marketplace` permissions required for Opus 4.5 model access verification at runtime.

**Fix applied via AWS CLI:**

```bash
AWS_PROFILE=bmx-prod aws iam put-role-policy \
  --role-name bluemoxon-prod-analysis-worker-exec-role \
  --policy-name bedrock-access \
  --policy-document file:///tmp/bedrock-access-policy.json
```

The policy now includes:

```json
{
  "Effect": "Allow",
  "Action": [
    "aws-marketplace:ViewSubscriptions",
    "aws-marketplace:Subscribe"
  ],
  "Resource": "*"
}
```

**Note:** The Terraform code in `infra/terraform/modules/analysis-worker/main.tf` also contains this fix, but couldn't be applied via `terraform apply` due to missing `db_password` variable. The AWS CLI fix is applied directly to the IAM role.

---

## Final State

| Step | Status |
|------|--------|
| Terraform IAM fix committed | COMPLETE |
| PR #722 merged to staging | COMPLETE |
| Staging deploy | COMPLETE |
| PR #723 merged to production | COMPLETE |
| Production deploy (run 20614126241) | COMPLETE |
| IAM policy applied to production | COMPLETE (via AWS CLI) |
| Opus test in production | COMPLETE - job 10c6c99c completed |
| Issues #718, #719 | CLOSED |

---

## Verification

**Opus Job Test:**

```text
Job ID: 10c6c99c-e6cf-4ade-8bc6-25cc11890e48
Book: 553 (The Greville Memoirs)
Model: opus
Status: completed
Duration: ~4 minutes
Generated at: 2025-12-31T07:17:39 UTC
```

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/config.py:155-169` | `get_scraper_environment()` - FMV fix |
| `infra/terraform/modules/analysis-worker/main.tf:209-242` | `bedrock_access` policy - Opus IAM fix (Terraform) |
| IAM Role: `bluemoxon-prod-analysis-worker-exec-role` | Direct IAM fix applied |

---

## PRs Created

| PR | Title | Status |
|----|-------|--------|
| #722 | fix: Production FMV scraper targeting and Opus IAM permissions | MERGED to staging |
| #723 | chore: Promote staging to production (Opus IAM fix #719) | MERGED to main |

---

## Remaining Work

### Eval Runbook Regeneration

Books with eval runbooks generated before the FMV fix may be missing comparables. To regenerate:

```bash
bmx-api --prod POST /books/{id}/eval-runbook/generate
```

### Terraform State Sync

The direct IAM fix via AWS CLI means Terraform state is now out of sync. Next `terraform apply` will attempt to update the policy to match the Terraform code (which should be identical, so no change expected).

---

## CRITICAL REMINDERS FOR CONTINUATION

### 1. ALWAYS Use Superpowers Skills

Before ANY task, check if a skill applies:

- `superpowers:brainstorming` - Before creative/feature work
- `superpowers:systematic-debugging` - Before fixing bugs
- `superpowers:verification-before-completion` - Before claiming work done
- `superpowers:finishing-a-development-branch` - When completing work
- `superpowers:test-driven-development` - Before writing implementation code
- `superpowers:writing-plans` - Before multi-step implementations
- `superpowers:executing-plans` - When implementing from a plan

**If there's even a 1% chance a skill applies, INVOKE IT.**

### 2. Bash Command Rules - NEVER USE

These trigger permission prompts and break auto-approve:

- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` or `$((...))` command/arithmetic substitution
- `||` or `&&` chaining (even simple chaining breaks auto-approve)
- `!` in quoted strings (bash history expansion corrupts values)

### 3. Bash Command Rules - ALWAYS USE

- Simple single-line commands only
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)
- Use command description field instead of inline comments
