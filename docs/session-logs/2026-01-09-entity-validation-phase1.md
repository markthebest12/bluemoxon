# Session Log: Entity Proliferation Prevention (#955)

**Date:** 2026-01-09
**Issue:** #955 - Prevent entity proliferation with API-level validation
**Design Doc:** docs/plans/2026-01-09-entity-proliferation-prevention-design.md
**Implementation Plan:** docs/plans/2026-01-09-entity-validation-phases-2-4.md
**Branch:** staging (current: feat-898-exchange-rates worktree)

**Child Issues:**

- #967: Phase 2 - Entity endpoints validation
- #968: Phase 3 - Book endpoints (DEFERRED)
- #969: Phase 4 - Rollout config
- #971: Author.name unique constraint (NEW - deferred from code review)

---

## Current Status: DEPLOYED TO PRODUCTION

**PR #970 merged and deployed** - 2026-01-09T05:39:28Z

Entity validation is now live in production. The feature prevents duplicate entity creation with fuzzy matching at the API level.

### What's Live

- POST /publishers, /binders, /authors return 409 when similar entity exists
- Fuzzy thresholds: 80% publisher/binder, 75% author (configurable via env vars)
- `?force=true` parameter bypasses validation
- Caching with 5-min TTL, DB queries run outside lock

### UI Validation Test Cases

Try creating these in the UI (Settings > Publishers/Authors/Binders > Add New):

| Entity Type | Try Creating | Should Match |
|-------------|--------------|--------------|
| Publisher | "Macmillan" | "Macmillan and Co." |
| Publisher | "Chapman Hall" | "Chapman & Hall" |
| Author | "Dickens, Charles" | "Charles Dickens" |
| Author | "Chas. Darwin" | "Charles Darwin" |
| Binder | "Riviere" | "Riviere & Son" |
| Binder | "Sangorski" | "Sangorski & Sutcliffe" |

---

## Code Review - COMPLETED

**PR:** #970 (staging -> main) - MERGED

### All Issues Fixed

| Priority | Issue | Fix |
|----------|-------|-----|
| P0 | Response type inconsistency | Added `responses={409: {"model": EntityValidationError}}` to decorators |
| P0 | Caching concurrency | Refactored to run DB queries outside lock (double-checked locking) |
| P1 | Double cache invalidation | `invalidate_entity_cache("publisher")` now calls legacy cache internally |
| P1 | Cache race condition | Publisher/Binder have DB unique constraints. Author deferred to #971 |
| P3 | Magic numbers | Added `DEFAULT_THRESHOLD_*` constants with reasoning comments |
| P3 | model_dump() exposure | Using explicit `include={}` parameter |
| P3 | Test cache smell | Investigated - no duplicate calls found (already clean) |

### Commits

| SHA | Message |
|-----|---------|
| 6c14f0c | fix(#970): address code review feedback for entity validation |
| 60cb223 | Merge main into staging to sync branches |

---

## Deferred Work

### #971: Add unique constraint to Author.name column

- Publisher and Binder models have `unique=True` on name (race condition protected)
- Author model is missing this constraint
- Requires: check for existing duplicates, migration, deploy
- Created as separate issue to not block this PR

### #968: Phase 3 - Book endpoints

- Book creation uses get_or_create pattern
- Needs refactor to integrate entity validation
- Lower priority - entity endpoints cover main use case

---

## CRITICAL: Session Continuation Rules

### 1. ALWAYS Use Superpowers Skills

**IF A SKILL MIGHT APPLY (even 1% chance), YOU MUST INVOKE IT.**

| Situation | Required Skill |
|-----------|----------------|
| Starting any task | superpowers:using-superpowers |
| Receiving code review | superpowers:receiving-code-review |
| Writing implementation | superpowers:test-driven-development |
| Before claiming done | superpowers:verification-before-completion |
| Planning multi-step work | superpowers:writing-plans |
| Debugging any issue | superpowers:systematic-debugging |
| Parallel independent tasks | superpowers:dispatching-parallel-agents |

**This is NOT optional. This is NOT negotiable.**

### 2. NEVER Use These (Trigger Permission Prompts)

```text
FORBIDDEN - causes permission dialog toil:

# comment before command        <- NEVER
command \                       <- NEVER (backslash continuation)
  --with-continuation
$(command substitution)         <- NEVER
cmd1 && cmd2                    <- NEVER (even simple chaining)
cmd1 || cmd2                    <- NEVER
'string with ! in it'           <- NEVER (bash history expansion)
```

### 3. ALWAYS Use These Instead

```text
CORRECT - no permission prompts:

command1 --arg value            <- Simple single-line commands
                                <- Use separate Bash tool calls for sequences

bmx-api GET /books              <- BlueMoxon API (staging)
bmx-api --prod GET /books       <- BlueMoxon API (production)
bmx-api POST /publishers '{"name":"test"}'
```

**For sequential commands:** Make separate Bash tool calls instead of using `&&`

**For API testing:** Always use `bmx-api` - it handles auth automatically

---

## Key Files Modified

### Backend

- `backend/app/api/v1/publishers.py` - 409 validation, explicit model_dump
- `backend/app/api/v1/authors.py` - 409 validation, explicit model_dump
- `backend/app/api/v1/binders.py` - 409 validation, explicit model_dump
- `backend/app/services/entity_matching.py` - Lock outside DB query, threshold docs
- `backend/app/services/entity_validation.py` - Validation helper
- `backend/app/config.py` - Threshold env vars

### Infrastructure

- `infra/terraform/variables.tf` - entity_validation_mode, threshold vars
- `infra/terraform/modules/lambda/main.tf` - Pass vars to Lambda
- `infra/terraform/envs/prod.tfvars` - enforce mode, thresholds
- `infra/terraform/envs/staging.tfvars` - enforce mode, thresholds

---

## References

- Design doc: `docs/plans/2026-01-09-entity-proliferation-prevention-design.md`
- Implementation plan: `docs/plans/2026-01-09-entity-validation-phases-2-4.md`
- Parent Issue: <https://github.com/markthebest12/bluemoxon/issues/955>
- Phase 2 Issue: <https://github.com/markthebest12/bluemoxon/issues/967>
- Phase 4 Issue: <https://github.com/markthebest12/bluemoxon/issues/969>
- Author constraint: <https://github.com/markthebest12/bluemoxon/issues/971>
- PR (merged): <https://github.com/markthebest12/bluemoxon/pull/970>
