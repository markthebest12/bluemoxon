# Session: Deploy Path-Based Filtering (#907)

**Date:** 2026-01-06
**Issue:** https://github.com/markthebest12/bluemoxon/issues/907
**PR:** https://github.com/markthebest12/bluemoxon/pull/908 (MERGED to staging)

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

### BLOCKING BUG - In Progress
- [ ] **Debug layer S3 file not found issue** (pre-existing bug surfaced by #907)

---

## BLOCKING BUG: Layer S3 File Not Found

### Symptoms
Two deploy runs failed:
1. **Run 1:** Worker Lambda jobs failed with `NoSuchKey` for `lambda/backend.zip`
2. **Run 2 (force_full_deploy):** Deploy-api-lambda failed with `NoSuchKey` for `lambda/layer-d7e43d653da49bc1.zip`

### Error Message
```
An error occurred (InvalidParameterValueException) when calling the PublishLayerVersion operation:
Error occurred while GetObject. S3 Error Code: NoSuchKey.
S3 Error Message: The specified key does not exist.
```

### Key Facts
- `build-layer` job shows `✓ Upload layer to S3` (succeeded)
- `deploy-api-lambda` job can't find the file immediately after
- Layer S3 key computed from: `sha256sum backend/requirements.txt | cut -d' ' -f1 | head -c 16`
- Key format: `lambda/layer-${REQ_HASH}.zip`
- The atomicity check IS working - it correctly caught partial failures

### Investigation To Do
1. Check S3 bucket contents:
```bash
AWS_PROFILE=bmx-staging aws s3 ls s3://bluemoxon-frontend-staging/lambda/
```

2. Verify requirements.txt hash:
```bash
sha256sum backend/requirements.txt
```

3. Compare build-layer job S3 key vs deploy-api-lambda expected key

### Possible Causes
1. Hash computed differently between build-layer and deploy-api-lambda
2. Build-layer skipped upload (exists=true but file doesn't exist)
3. S3 bucket/key mismatch between jobs
4. configure.outputs.s3_frontend_bucket different between jobs

### Files to Check
- `.github/workflows/deploy.yml` lines 437-493 (build-layer job)
- `.github/workflows/deploy.yml` lines 687-711 (deploy-api-lambda layer handling)

---

## Next Steps

### Immediate (Debug Layer Bug)
1. Use `superpowers:systematic-debugging` skill
2. Check S3 bucket contents
3. Compare hashes between jobs
4. Fix the root cause
5. Re-run deploy workflow

### After Bug Fix
1. Verify staging deploy succeeds
2. Test path filtering (frontend-only change should skip backend)
3. Create PR from staging → main

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
