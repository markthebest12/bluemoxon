# Session: Cleanup Lambda Naming Fix (Production)

**Date:** 2025-12-30
**Status:** COMPLETE - Verified in Production

---

## CRITICAL REMINDERS FOR CONTINUATION

### 1. ALWAYS Use Superpowers Skills

- **brainstorming** - Before any creative/design work
- **test-driven-development** - Before implementing any feature
- **verification-before-completion** - Before claiming work is done
- **requesting-code-review** - After completing significant work
- **systematic-debugging** - For any bugs/failures

### 2. NEVER Use These (Permission Prompts)

- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

### 3. ALWAYS Use

- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls

---

## Problem Statement

Maintenance tab in production admin getting "Request failed with status code 500".

### Root Cause

**Lambda naming mismatch:**

- API code uses: `f"bluemoxon-{settings.environment}-cleanup"`
- `settings.environment` = `"production"` (from `BMX_ENVIRONMENT`)
- So API tries to invoke: `bluemoxon-production-cleanup`
- But Terraform created: `bluemoxon-prod-cleanup` (using `environment = "prod"`)

**Error from logs:**

```
botocore.exceptions.ClientError: An error occurred (AccessDeniedException) when calling the Invoke operation:
User: arn:aws:sts::266672885920:assumed-role/bluemoxon-lambda-role/bluemoxon-prod-api
is not authorized to perform: lambda:InvokeFunction
on resource: arn:aws:lambda:us-west-2:266672885920:function:bluemoxon-production-cleanup
```

### Decision Made

Rename Lambda to `bluemoxon-production-cleanup` to match the standard naming convention used elsewhere (where `BMX_ENVIRONMENT=production`).

---

## Changes Made

### 1. Added `cleanup_function_name_override` variable

**File:** `infra/terraform/variables.tf`

```hcl
variable "cleanup_function_name_override" {
  type        = string
  description = "Override cleanup Lambda function name (for legacy naming, e.g., bluemoxon-production-cleanup)"
  default     = null
}
```

### 2. Updated cleanup_lambda module to use override

**File:** `infra/terraform/main.tf` (line 581)

```hcl
function_name = coalesce(var.cleanup_function_name_override, "${local.name_prefix}-cleanup")
```

### 3. Added override to prod.tfvars

**File:** `infra/terraform/envs/prod.tfvars`

```hcl
cleanup_function_name_override = "bluemoxon-production-cleanup"
```

---

## AWS Changes Applied Directly

Before CI/CD deploy, applied these changes directly to AWS:

1. **Deleted old Lambda:** `bluemoxon-prod-cleanup`
2. **Created new Lambda:** `bluemoxon-production-cleanup` (with placeholder code)
3. **Updated IAM policy:** API Lambda can now invoke new cleanup Lambda
4. **Created new IAM role:** `bluemoxon-production-cleanup-role`
5. **Created new CloudWatch log group:** `/aws/lambda/bluemoxon-production-cleanup`

---

## PRs Merged

| PR | Description | Target |
|----|-------------|--------|
| #704 | Add cleanup_function_name_override variable | staging |
| #705 | Promote staging to production | main |

---

## Deploy Status

**Deploy run:** 20607105410
**Status:** SUCCESS

The deploy workflow:

1. ✅ CI checks passed
2. ✅ Build artifacts created
3. ✅ Deploy to production completed
4. ✅ Smoke tests passed

**Verification:**

```
bmx-api --prod POST /admin/cleanup '{"action":"stale"}'
{"stale_archived":0,"sources_checked":0,"sources_expired":0,...}
```

Maintenance tab now works correctly.

---

## NEXT STEPS (When Resuming)

### 1. Check Deploy Status

```bash
gh run view 20607105410 --repo markthebest12/bluemoxon --json status,conclusion
```

### 2. If Deploy Succeeded, Verify Cleanup Works

```bash
bmx-api --prod POST /admin/cleanup '{"action":"stale"}'
```

### 3. If Deploy Failed, Check Logs

```bash
gh run view 20607105410 --repo markthebest12/bluemoxon --log-failed
```

---

## Files Modified

| File | Change |
|------|--------|
| `infra/terraform/variables.tf` | Added `cleanup_function_name_override` variable |
| `infra/terraform/main.tf` | Updated cleanup_lambda module to use coalesce with override |
| `infra/terraform/envs/prod.tfvars` | Added `cleanup_function_name_override = "bluemoxon-production-cleanup"` |

---

## Key Files Reference

- **API cleanup endpoint:** `backend/app/api/v1/admin.py:422` - uses `f"bluemoxon-{settings.environment}-cleanup"`
- **Terraform cleanup module:** `infra/terraform/modules/cleanup-lambda/main.tf`
- **IAM policy for API invoke:** `infra/terraform/modules/cleanup-lambda/main.tf:202-217`

---

## Commands for Verification

```bash
gh run view 20607105410 --repo markthebest12/bluemoxon --json status,conclusion

curl -s https://api.bluemoxon.com/api/v1/health/deep | jq '.status'

bmx-api --prod POST /admin/cleanup '{"action":"stale"}'

AWS_PROFILE=bmx-prod aws lambda list-functions --query "Functions[?contains(FunctionName, 'cleanup')].FunctionName" --output text
```

---

## Related Context

- Issue #697 mobile acquisitions UI was deployed to production successfully earlier in this session
- The cleanup Lambda issue is separate from issue #697
- Session log for #697: `docs/sessions/2025-12-30-issue-697-mobile-acquisitions.md`
