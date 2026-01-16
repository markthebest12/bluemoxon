# Session: Deploy Path-Based Filtering (#907)

**Date:** 2026-01-06
**Issue:** <https://github.com/markthebest12/bluemoxon/issues/907>
**PR:** <https://github.com/markthebest12/bluemoxon/pull/908> (MERGED to staging)

---

## CRITICAL: Session Continuation Rules

### 1. ALWAYS Use Superpowers Skills

**Invoke relevant skills BEFORE any action.** Even 1% chance a skill applies = invoke it.

Key skills for this task:

- `superpowers:systematic-debugging` - USE THIS for the layer S3 bug
- `superpowers:verification-before-completion` - before claiming done
- `superpowers:dispatching-parallel-agents` - for parallel agent work

### 2. Bash Command Rules (NEVER VIOLATE)

**NEVER use (triggers permission prompts):**

- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**

- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls

```bash
# BAD - will prompt:
aws lambda get-function-configuration \
  --function-name my-function

# GOOD - single line:
aws lambda get-function-configuration --function-name my-function
```

---

## Current Status

### Completed

- [x] Design document: `docs/plans/2026-01-06-deploy-path-filtering-design.md`
- [x] Implementation using 4 parallel subagents
- [x] All 13 tasks from design implemented
- [x] P0/P1/P2 code review fixes applied
- [x] PR #908 merged to staging

### P0/P1/P2 Fixes Applied

| Priority | Issue | Fix |
|----------|-------|-----|
| **P0-1** | Layer ARN race condition | Pass layer ARN via `deploy-api-lambda.outputs.layer_arn` instead of querying |
| **P0-2** | Version skew on partial deploy | Only run version check if `deploy-api-lambda.result == 'success'` |
| **P0-3** | Inconsistent path filters | Added `pyproject.toml`, `package.json`, `package-lock.json` to deploy filters |
| **P1-1** | `always()` masks upstream failures | Added `needs.configure.result == 'success'` to all deploy jobs |
| **P1-2** | No atomicity check | Added "Check for partial deploy failures" step in smoke-test |
| **P2-3** | Version cleanup only on API Lambda | Added cleanup step to all 7 Lambda deploy jobs |

### BLOCKING BUG - FIXED

- [x] **Debug layer S3 file not found issue** (pre-existing bug surfaced by #907)

---

## BLOCKING BUG: Layer S3 File Not Found - RESOLVED

### Root Cause

The `deploy-frontend` job's `aws s3 sync ... --delete` command was deleting the `lambda/` folder because it wasn't in `frontend-dist/`.

**Timeline (from workflow run 20772114798):**

- 05:58:12 - `build-layer` uploads `lambda/layer-d7e43d653da49bc1.zip` ✓
- 05:58:13 - `deploy-frontend` STARTS, runs `aws s3 sync --delete` (DELETES the layer file!)
- 05:58:27 - `deploy-api-lambda` uploads `backend.zip` (AFTER frontend sync deleted layer)
- 05:58:28 - `deploy-api-lambda` tries to publish layer → **NoSuchKey FAILURE**

### Fix Applied

Added `--exclude "lambda/*"` to the s3 sync command (line 1264):

```yaml
aws s3 sync frontend-dist/ s3://.../ --delete ... --exclude "lambda/*"
```

### Investigation Method

Used `superpowers:systematic-debugging` skill:

1. **Evidence gathering:** S3 bucket only had `backend.zip`, no layer files
2. **Log analysis:** GitHub Actions logs showed both layer uploads succeeded
3. **Timeline reconstruction:** Discovered deploy-frontend ran BETWEEN layer upload and layer publish
4. **Root cause:** Found `--delete` flag without `--exclude "lambda/*"`

---

## Next Steps

1. Commit and push the fix
2. Re-run deploy workflow
3. Verify staging deploy succeeds
4. Test path filtering (frontend-only change should skip backend)
5. Create PR from staging → main

---

## Implementation Summary

**Workflow structure:**

```
ci → changes → configure → generate-version
         ↓
   build-layer, build-backend, build-frontend, build-scraper (conditional)
         ↓
   deploy-api-lambda (leader, publishes layer, outputs layer_arn)
         ↓
   deploy-worker-lambda, deploy-eval-worker-lambda, deploy-cleanup-lambda,
   deploy-tracking-dispatcher-lambda, deploy-tracking-worker-lambda (use layer_arn from api-lambda)
         ↓
   deploy-scraper-lambda, deploy-frontend (independent)
         ↓
   run-migrations → smoke-test (includes atomicity check) → create-release
```

**Key features:**

- `dorny/paths-filter@v3` for path detection
- `force_full_deploy` workflow_dispatch input for override
- Layer ARN passed via outputs (not queried) - fixes P0-1
- Atomicity check fails workflow if ANY deploy job failed
- Version cleanup on ALL Lambda jobs (not just API)

---

## Git State

- **Branch:** `staging` (PR #908 merged)
- **Last commit:** `51c6154` - feat: Add path-based filtering to deploy workflow (#907)
- **Deploy runs:** 2 failed (layer S3 bug)

---

## Deferred Work

- **P2-1**: Refactor Lambda deploys to matrix strategy
- **P2-2**: Changes job placement optimization
