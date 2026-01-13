# Session Log: Sync Script Review Before Staging Refresh

**Date:** 2026-01-11
**Goal:** Review changes since Jan 9 that impact prod-to-staging sync, add Redis cache flush

---

## CRITICAL REMINDERS

### 1. ALWAYS Use Superpowers Skills

**Invoke relevant skills BEFORE any action.** Even 1% chance a skill applies = invoke it.

Key skills for this project:
- `superpowers:using-superpowers` - Meta skill, use at session start
- `superpowers:brainstorming` - Before design/planning work
- `superpowers:writing-plans` - Create implementation plans
- `superpowers:subagent-driven-development` - Execute plans with fresh subagent per task
- `superpowers:systematic-debugging` - Before ANY bug fix attempt
- `superpowers:requesting-code-review` - After completing tasks, before merge
- `superpowers:receiving-code-review` - When receiving feedback, verify before implementing
- `superpowers:verification-before-completion` - Before claiming work is done
- `superpowers:test-driven-development` - Before writing implementation code

### 2. Bash Command Rules - NEVER Use Complex Syntax

**NEVER use (triggers permission prompts):**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

---

## Session Summary

### Original Problem
ElastiCache (Redis) was added to production (#1002) since the last sync script run (Jan 9). After syncing the database from prod to staging, the staging Redis cache would contain stale data, causing dashboard stats to show incorrect values for up to 5 minutes (cache TTL).

### Work Completed

#### 1. Redis Cache Flush Implementation (PR #1054)
- Implemented Redis cache flush in sync script
- 7 tasks completed via `superpowers:subagent-driven-development`
- PR created and CI passed

#### 2. Code Review Feedback (Critical)
Received detailed code review identifying fundamental issues:

| Issue | Severity | Finding |
|-------|----------|---------|
| Network Access | P0 | ElastiCache security group only allows Lambda - developer machines blocked |
| Missing AUTH | P0 | Would need auth even if network allowed |
| FLUSHALL scope | P1 | Verified OK - Redis only used for dashboard stats |
| timeout on macOS | P1 | macOS needs `gtimeout` from coreutils |
| URL parsing | P2 | Fragile but works for current format |
| Silent failures | P2 | Everything returns 0 on failure |

#### 3. YAGNI Decision
Used `superpowers:brainstorming` to evaluate options:
- **Option A:** Add API endpoint for cache flush (complexity)
- **Option B:** Document expected behavior, skip implementation (YAGNI)

**Chose B** - The 5-minute stale window is acceptable and self-corrects.

#### 4. Final Changes (PR #1055 - MERGED)
- Documented expected cache staleness in sync script header
- Added S3 exclusions for non-image prefixes:
  - `lambda/` - Lambda deployment packages
  - `deploy/` - Lambda deployment packages
  - `data-import/` - One-time import files
  - `listings/` - Transient scraper staging area
- Documented no `--delete` flag behavior

#### 5. New Issue Created
- **#1056** - feat: Add listings/ directory cleanup to maintenance Lambda

### Closed Items
- **PR #1054** - Closed (YAGNI - architectural blockers)
- **Issue #1053** - Closed (by design - cache staleness acceptable)

---

## Current State

### Sync Script Status: Ready
- PR #1055 merged to staging
- S3 exclusions added
- Cache staleness documented
- Dry-run tested successfully

### Environment Versions
- Prod: `2026.01.11-d688bcd`
- Staging: `2026.01.11-588327b`
- Mismatch is documentation-only commits, no schema changes

### Dry-Run Results
```
Production:  status=healthy schema_validated=true books=208
Staging:     status=healthy schema_validated=true books=163
S3 objects to sync: ~5157 (after exclusions)
```

---

## Next Steps

1. **Run actual sync** (when ready):
   ```bash
   ./scripts/sync-prod-to-staging.sh --db-only --yes
   ```
   Or with images:
   ```bash
   ./scripts/sync-prod-to-staging.sh --yes
   ```

2. **After sync completes:**
   - Verify staging API health: `curl -s https://staging.api.bluemoxon.com/api/v1/health/deep | jq`
   - Dashboard stats will be stale for ~5 minutes (expected)

3. **Promote sync script to production** (after staging validation):
   ```bash
   gh pr create --base main --head staging --title "chore: Promote staging to production"
   ```

---

## Files Modified This Session

| File | Change |
|------|--------|
| `scripts/sync-prod-to-staging.sh` | Added S3 exclusions, documented cache staleness |

---

## Related Issues/PRs

- **#1053** - Closed (Redis cache flush - by design)
- **#1054** - Closed (PR for Redis flush - YAGNI)
- **#1055** - Merged (S3 exclusions + cache docs)
- **#1056** - Open (listings/ cleanup enhancement)
- **#1002** - ElastiCache implementation (context)

---

## Skills Used This Session

1. `superpowers:using-superpowers` - Meta skill at start
2. `superpowers:brainstorming` - Requirements exploration, YAGNI decision
3. `superpowers:writing-plans` - Created implementation plan
4. `superpowers:subagent-driven-development` - Executed plan with subagents
5. `superpowers:receiving-code-review` - Evaluated P0/P1/P2 feedback technically
