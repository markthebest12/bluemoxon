# Session: Deploy Path-Based Filtering (#907)

**Date:** 2026-01-06
**Issue:** https://github.com/markthebest12/bluemoxon/issues/907

---

## CRITICAL: Session Continuation Rules

### 1. ALWAYS Use Superpowers Skills
**Invoke relevant skills BEFORE any action.** Even 1% chance a skill applies = invoke it.

Key skills for this task:
- `superpowers:dispatching-parallel-agents` - for parallel agent work
- `superpowers:verification-before-completion` - before claiming done
- `superpowers:systematic-debugging` - if tests fail

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

## Background

**Issue #907:** Add path-based filtering to deploy workflow to skip unnecessary builds/deploys when only specific components change.

**Goal:** 40-60% time reduction for partial deploys by:
- Detecting which paths changed (backend/frontend/scraper)
- Skipping builds for unchanged components
- Running deploy jobs only for changed components
- Always running smoke tests if ANY deploy succeeded

## Current Status

### Completed
- [x] Design document: `docs/plans/2026-01-06-deploy-path-filtering-design.md`
- [x] Implementation using 4 parallel subagents
- [x] All 13 tasks from design implemented
- [x] YAML syntax validated
- [x] File staged for commit

### In Progress
- [ ] **Commit and push branch** (on `feat/deploy-path-filtering` from staging)
- [ ] Create PR to staging

### Remaining
- [ ] Test in staging environment
- [ ] Create PR from staging → main (production)

## Implementation Summary

**4 parallel agents implemented:**
1. Agent 1 (Tasks 1-2): `changes` job + conditional build jobs
2. Agent 2 (Tasks 3-8): 6 backend Lambda deploy jobs
3. Agent 3 (Tasks 9-10): scraper + frontend deploy jobs
4. Agent 4 (Tasks 11-13): run-migrations + smoke-test updates

**New workflow structure:**
```
ci → changes → configure → generate-version
         ↓
   build-layer, build-backend, build-frontend, build-scraper (conditional)
         ↓
   deploy-api-lambda (leader, publishes layer)
         ↓
   deploy-worker-lambda, deploy-eval-worker-lambda, deploy-cleanup-lambda,
   deploy-tracking-dispatcher-lambda, deploy-tracking-worker-lambda (parallel)
         ↓
   deploy-scraper-lambda, deploy-frontend (independent)
         ↓
   run-migrations → smoke-test → create-release
```

**Key features:**
- `dorny/paths-filter@v3` for path detection
- `force_full_deploy` workflow_dispatch input for override
- Jobs skip when component unchanged AND force_full_deploy=false
- smoke-test runs if ANY deploy job succeeded (uses `always()`)

## Next Steps

### Immediate (Complete the PR)
```bash
# 1. Commit (files already staged)
git commit -m "feat: Add path-based filtering to deploy workflow (#907)"

# 2. Push branch
git push -u origin feat/deploy-path-filtering

# 3. Create PR to staging
gh pr create --base staging --title "feat: Add path-based filtering to deploy workflow (#907)" --body "..."
```

### After PR Created
1. Wait for CI to pass on PR
2. Merge to staging
3. Monitor staging deploy workflow
4. Verify path filtering works (frontend-only change should skip backend)
5. Create PR from staging → main

## Files Modified

- `.github/workflows/deploy.yml` - Complete rewrite with path filtering
- `docs/session-2026-01-06-deploy-path-filtering.md` - This file
- `docs/plans/2026-01-06-deploy-path-filtering-design.md` - Design document

## Git State

- **Branch:** `feat/deploy-path-filtering` (from `origin/staging`)
- **Files staged:** deploy.yml, session log, design doc
- **Ready for:** commit and push

---

## Design Decisions (Completed)

1. **Layer handling:** Skip entirely when backend unchanged
2. **Deploy granularity:** Per-Lambda jobs (7+ jobs) for max parallelism
3. **Smoke tests:** Always run full suite
4. **Force override:** Boolean `force_full_deploy` input
5. **Path categories:** Backend/Frontend/Scraper only (3 categories)

## Design Document
See: `docs/plans/2026-01-06-deploy-path-filtering-design.md`

## Implementation Plan for New Session

Start new session with:
```
Implement #907 deploy path-based filtering per design in docs/plans/2026-01-06-deploy-path-filtering-design.md

Use subagents in parallel for:
- Task 1-2: Path filter + conditional builds (one agent)
- Tasks 3-8: Backend Lambda deploy jobs (one agent - 6 jobs)
- Tasks 9-10: Scraper + Frontend deploy jobs (one agent)
- Tasks 11-13: Migrations, smoke-test, release updates (one agent)

Session log: docs/session-2026-01-06-deploy-path-filtering.md
```

## Notes

- Current deploy.yml is ~2000 lines
- Splitting into 8 deploy jobs will increase lines but improve parallelism
- Layer ARN must be passed from build-layer to all Lambda deploy jobs
