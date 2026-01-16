# Session: Listings Directory Cleanup Feature

**Date:** 2026-01-11
**GitHub Issue:** #1056
**Worktree:** `/Users/mark/projects/bluemoxon/.worktrees/feat-1056-listings-cleanup`
**Branch:** `feat/1056-listings-cleanup`
**Status:** Design phase

---

## CRITICAL INSTRUCTIONS FOR CONTINUATION

### MUST USE Superpowers Skills

**THIS IS NOT OPTIONAL. INVOKE BEFORE ANY ACTION.**

- `superpowers:using-superpowers` - ALWAYS at session start
- `superpowers:brainstorming` - Before any creative/design work
- `superpowers:test-driven-development` - Before writing implementation code
- `superpowers:systematic-debugging` - For any bugs or unexpected behavior
- `superpowers:verification-before-completion` - Before claiming work is done

### NEVER Use These (Permission Prompt Triggers)

```text
FORBIDDEN - will cause permission prompts:
- # comment lines before commands
- \ backslash line continuations
- $(...) or $((...)) command substitution
- || or && chaining
- ! in quoted strings (bash history expansion)
```

### ALWAYS Use

```text
REQUIRED patterns:
- Simple single-line commands only
- Separate sequential Bash tool calls instead of &&
- git -C <path> for git commands (not cd && git)
- bmx-api for all BlueMoxon API calls (no permission prompts)
```

### PR Review Requirements

1. **Before PR to staging:** User reviews changes
2. **Before PR to main:** User reviews promotion

---

## Problem Statement

The `listings/` S3 prefix accumulates orphaned images:

1. User pastes eBay URL -> scraper extracts images to `listings/{item_id}/`
2. User creates book -> images are COPIED to `books/`
3. Original `listings/` images are left behind (~100MB in prod, growing)

Current cleanup Lambda explicitly excludes `listings/` prefix.

---

## Implementation Options

### Option A: Age-based cleanup (simpler)

- Delete all `listings/*` objects older than 30 days
- Assumption: if not imported within 30 days, it's abandoned
- Pros: Simple, no DB queries needed
- Cons: Could delete listings still being evaluated

### Option B: Reference-based cleanup (safer)

- Query Books for `source_item_id` values
- Delete listings where item_id matches a Book (already imported)
- Keep listings with no Book match (might still be evaluating)
- Pros: Safer, won't delete active evaluations
- Cons: More complex, requires DB queries

### Option C: Hybrid approach

- Use both age AND reference checking
- Delete if: (older than X days) AND (has matching Book OR no activity)

---

## Acceptance Criteria

- [ ] New `listings` action in cleanup Lambda
- [ ] Configurable age threshold (default 30 days)
- [ ] Dry-run mode (report what would be deleted)
- [ ] Delete mode (actually remove files)
- [ ] Admin API endpoint support
- [ ] Unit tests for new function
- [ ] UI integration (if orphan cleanup panel exists)

---

## Files to Modify

- `backend/lambdas/cleanup/handler.py` - Add `cleanup_stale_listings()` function
- `backend/app/api/v1/admin.py` - Add listings action and parameters
- `frontend/src/components/admin/OrphanCleanupPanel.vue` - Add listings cleanup UI

---

## Progress Log

### 2026-01-11: Session Start

- Created worktree from staging
- Fetched issue #1056 requirements
- Starting design phase with brainstorming skill
