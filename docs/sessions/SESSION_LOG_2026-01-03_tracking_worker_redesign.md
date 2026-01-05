# Session Log: Tracking Worker Redesign

**Date**: 2026-01-03
**Issue**: #516 Code Review Feedback - Carrier API Support Redesign
**Branch**: `refactor/tracking-worker-redesign` (merged to `staging`)
**PR**: #773 (staging -> main)

---

## Summary

Redesigned carrier API tracking from monolithic Lambda to distributed SQS architecture with circuit breaker pattern. Implemented 12 tasks using parallel subagent batches, reducing execution from 12 sequential to 4 batches.

## Background

Code review on PR #771 identified 5 critical architectural issues:

| Issue | Problem | Solution |
|-------|---------|----------|
| Lambda overload | HTTP + polling in one Lambda | Split into API + Dispatcher + Worker |
| Timeout risk | 50 books × 15s = 750s | SQS fan-out, 1 book per worker |
| Phone validation | API-only, DB bypass possible | CHECK constraint in PostgreSQL |
| Carrier detection | Non-deterministic dict order | Require explicit carrier |
| No circuit breaker | Hammers failing APIs | Per-carrier failure tracking, 30min cooldown |

## What Was Built

**Architecture**: EventBridge -> Dispatcher Lambda -> SQS Queue -> Worker Lambda

**Files Created**:
- `backend/app/workers/tracking_dispatcher.py` - Queries books, sends to SQS
- `backend/app/workers/tracking_worker.py` - Fetches carrier API, updates DB
- `backend/app/services/circuit_breaker.py` - Opens after 3 failures
- `backend/app/models/carrier_circuit.py` - Circuit state model
- `backend/alembic/versions/x7890123abcd_phone_e164_constraint.py` - E.164 + circuit table
- `infra/terraform/modules/tracking-worker/` - Full Terraform module
- `.github/workflows/deploy.yml` - Updated for new Lambdas

**Test Coverage**: 43 new tests, 1000 total backend tests passing

## Issues Fixed During Session

1. **Migration branch conflict** - Made `x7890123abcd` a merge migration with `down_revision = ("w6789012wxyz", "5d2aef44594e")`
2. **Frontend Prettier** - Fixed formatting in 4 Vue/TypeScript files

## Next Steps

1. Push session log: `git push origin staging`
2. Wait for CI to pass on PR #773
3. Merge PR #773 to main
4. Watch deploy workflow: `gh run watch <id> --exit-status`
5. Run migrations: `bmx-api POST /health/migrate`
6. Test tracking in staging
7. Promote to production

---

## CRITICAL REMINDERS FOR NEXT SESSION

### 1. ALWAYS Use Superpowers Skills

**If there's even a 1% chance a skill applies, INVOKE IT.**

| Situation | Skill |
|-----------|-------|
| Before creative/feature work | `superpowers:brainstorming` |
| Before multi-step implementation | `superpowers:writing-plans` |
| Executing plans in same session | `superpowers:subagent-driven-development` |
| Any implementation | `superpowers:test-driven-development` |
| After all tasks complete | `superpowers:finishing-a-development-branch` |
| Receiving review feedback | `superpowers:receiving-code-review` |
| Need isolated workspace | `superpowers:using-git-worktrees` |

### 2. NEVER Use These (Permission Prompt Triggers)

```bash
# BAD - ALWAYS triggers prompts:
# Comment lines before commands
command \
  --with-continuation     # backslash line continuations
$(date +%s)               # command substitution
cmd1 && cmd2              # chaining with &&
cmd1 || cmd2              # chaining with ||
--password 'Test1234!'    # ! in quoted strings
```

### 3. ALWAYS Use These Patterns

```bash
# GOOD - Simple single-line commands:
poetry run pytest tests/
git add file.py
git commit -m "message"
aws lambda get-function-configuration --function-name foo

# Use bmx-api for BlueMoxon API calls (no prompts):
bmx-api GET /books
bmx-api --prod GET /health
bmx-api POST /books '{"title":"..."}'
```

**Make separate sequential Bash tool calls instead of && chaining.**

---

## Current State

- **Branch**: `staging` at commit `4802ba1`
- **PR #773**: Open, CI running after migration merge fix
- **Worktree**: Removed (was at `.worktrees/tracking-worker-redesign`)
- **Feature branch**: Deleted after merge to staging
