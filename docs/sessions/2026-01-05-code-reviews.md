# Session Log: Brutal Code Reviews

**Date:** 2026-01-05
**Purpose:** Senior dev code reviews on multiple PRs before merge

---

## CRITICAL SESSION RULES

### 1. ALWAYS Use Superpowers Skills
**Invoke relevant skills BEFORE any response or action.** Even 1% chance a skill applies means invoke it.

Key skills for this codebase:
- `superpowers:brainstorming` - Before any creative/feature work
- `superpowers:systematic-debugging` - Before proposing bug fixes
- `superpowers:verification-before-completion` - Before claiming work is done
- `superpowers:requesting-code-review` - After completing major features

### 2. NEVER Use These (Trigger Permission Prompts)
```bash
# BAD - will ALWAYS prompt:
# This is a comment before command
curl -s https://api.example.com/health

aws lambda get-function-configuration \
  --function-name my-function

AWS_PROFILE=staging aws logs filter-log-events --start-time $(date +%s000)

git add . && git commit -m "message"

--password 'Test1234!'  # The ! gets corrupted
```

### 3. ALWAYS Use These Patterns
```bash
# GOOD - simple single-line commands:
curl -s https://api.example.com/health
aws lambda get-function-configuration --function-name my-function
bmx-api GET /books
bmx-api --prod GET /books/123
```

**Use separate Bash tool calls instead of && chaining.**

---

## PRs Reviewed This Session

### PR #811 - health.py Migration Refactor (Issue #801)
**Status:** CRITICAL ISSUES - DO NOT MERGE
**Problems Found:**
1. **P0: Lambda package missing alembic.ini and alembic/ directory** - Will crash in production
2. **P0: Transaction corruption** - Alembic creates own connection, db session won't see changes
3. **P1: No concurrency protection** - Race condition on simultaneous calls
4. **P1: HTTP 200 on failure** - Returns success status code even when failed
5. **P1: Lost granularity** - No per-migration visibility

### PR #812 - Remove /fix-publisher-tiers (Issue #804)
**Status:** Insufficient - fixes one hole while many remain
**Problems Found:**
1. **P0: Other unauthenticated endpoints exist** - health.py has /migrate, /cleanup-orphans, /merge-binders all without auth
2. **P1: Orphaned TIER_1_PUBLISHERS constant** not removed
3. **P2: No security audit trail**

### PR #816 - Analysis Parsing and Timeout Handling (Issues #814, #815)
**Status:** ACCEPTABLE after fixes
**Fixed Issues:**
- Bold markdown regex now handles `**Low**`, `__Low__`, case-insensitive
- `completed_at` added to all 5 exception handlers (worker.py, eval_worker.py, books.py)
**Remaining:** Session log should be removed

### PR #817 - Promote Staging to Production (fixes from #816)
**Status:** ACCEPTABLE
- Clean promotion of #816 fixes
- `completed_at` fixes already on main from earlier promotion

### PR #818 - Extract BookResponse Builder (Issue #802)
**Status:** CRITICAL - Stale branch will revert #815 fixes
**Problems Found:**
1. **P0: Branch based on old commit** - Will REVERT all `completed_at` fixes from #815
2. **P1: N+1 query potential** - Helper does 2 DB queries per call
3. **P2: Serialization round-trip wasteful**
**Action Required:** Must rebase on current staging before merge

### PR #819 - Promote BookResponse Refactor
**Status:** ACCEPTABLE
- Clean promotion after #818 was rebased
- No regression of `completed_at` fixes

### PR #820 - Move TIER_1_PUBLISHERS to Database (Issue #803)
**Status:** ALMOST READY - scope creep issue
**Fixed in Revision:**
- N+1 query fixed with joinedload
- Functional index on LOWER(alias_name) added
- Index on publisher_id added
- Downgrade cleans up orphaned publishers
**Remaining Issues:**
1. **P1: Unrelated get_by_author changes** - Breaking API change (count semantics changed)
2. **P2: Test fixtures duplicate migration seed data**

---

## Common Patterns Found Across PRs

### Anti-Patterns Identified
1. **Stale branches** - Creating PRs from old base commits that revert recent fixes
2. **Scope creep** - Adding unrelated changes to PRs
3. **Session logs as documentation** - AI working notes don't belong in repo
4. **Incomplete security fixes** - Fixing one vulnerability while leaving similar ones
5. **Missing indexes** - Queries using functions without functional indexes

### Best Practices Reinforced
1. Always rebase on target branch before creating PR
2. One logical change per PR
3. Check for N+1 queries when adding DB lookups
4. Use joinedload for relationships accessed in same request
5. Functional indexes for case-insensitive queries

---

## Next Steps

1. **PR #811** - Needs major rework or should be abandoned
   - Either add alembic files to Lambda package, or
   - Keep embedded SQL approach (ugly but works)

2. **PR #812** - Create follow-up issues for remaining unauth endpoints:
   - `/health/migrate`
   - `/health/cleanup-orphans`
   - `/health/merge-binders`
   - `/listings/extract`

3. **PR #820** - Remove get_by_author changes before merge
   - Revert stats.py to only remove TIER_1_PUBLISHERS constant
   - Create separate PR for volume counting change

4. **General cleanup** - Remove all SESSION_LOG files from repo in one cleanup PR

---

## Key Commands for This Codebase

```bash
# API calls (no permission prompts)
bmx-api GET /books
bmx-api --prod GET /books/123
bmx-api POST /books '{"title":"..."}'

# Git operations (separate calls, no &&)
git status
git diff
git add .
git commit -m "message"

# Linting (separate calls)
poetry run ruff check backend/
poetry run ruff format --check backend/

# Testing
poetry run pytest backend/tests/test_specific.py -v
```

---

*Session log for continuity during chat compacting*
