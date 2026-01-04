# Session Log: Analysis Model Default Fix + Discount Bug

**Date**: 2026-01-03 / 2026-01-04
**PRs**: #794 (merged), #795 (merged to production)
**Issues**: #796 (discount_pct recalculation - pending)

---

## CRITICAL SESSION RULES (MUST FOLLOW)

### 1. Superpowers Skills - USE AT ALL STAGES
**Invoke relevant skills BEFORE any response or action.** Even 1% chance = invoke.
- `superpowers:brainstorming` - Before any creative/feature work
- `superpowers:test-driven-development` - Before writing implementation code
- `superpowers:verification-before-completion` - Before claiming work is done
- `superpowers:systematic-debugging` - Before proposing fixes for any bug
- `superpowers:finishing-a-development-branch` - When completing work
- `superpowers:code-reviewer` - After significant code changes

**RED FLAGS - If you think these, STOP and invoke the skill:**
- "This is simple, I'll just..."
- "Let me quickly fix this..."
- "I'm confident this works..."

### 2. Bash Command Rules (AVOID PERMISSION PROMPTS)
**NEVER use:**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

### 3. PR Review Gates
- User reviews PR before staging merge
- User reviews staging->main PR before prod merge
- No auto-merging without explicit approval

---

## COMPLETED: Analysis Model Default Fix

### Problem
Books 578, 579, 581 failed analysis generation with Bedrock timeout (540s) using wrong model.

### Root Cause
**AcquisitionsView.vue bypassed the store and hardcoded `model: "sonnet"`**

### Solution Applied
Created `DEFAULT_ANALYSIS_MODEL = "opus"` constant in both frontend and backend, fixed ALL locations.

### Deployment Status
| Step | Status | Date |
|------|--------|------|
| PR #794 merged to staging | Done | 2026-01-04 |
| Staging deploy + smoke tests | Done | 2026-01-04 |
| Staging migration `7a6d67bc123e` | Done | 2026-01-04 |
| Staging verification (book 476) | Done | model: "opus" confirmed |
| PR #795 merged to main | Done | 2026-01-04 |
| Production deploy + smoke tests | Done | 2026-01-04 |
| Production migration | Done | 2026-01-04 |
| Production verification (book 581) | Done | model: "opus" confirmed |

### Verification Evidence
```json
// Staging - book 476 analysis job
{"model":"opus","status":"pending","book_id":476}

// Production - book 581 analysis job
{"model":"opus","status":"pending","book_id":581}
```

---

## PENDING: Stale discount_pct Bug (#796)

### Problem
Book 572 displays "-692% off" in Acquisitions view.

### Root Cause (Found via systematic-debugging skill)
- `discount_pct` is calculated once at acquisition based on `value_mid`
- When FMV is later updated, `discount_pct` is NOT recalculated
- Book 572: FMV was $53 at acquisition (wrong), now $950 (corrected)
- Calculation: `(53 - 420) / 53 * 100 = -692%` (stale)
- Should be: `(950 - 420) / 950 * 100 = 56%`

### Scope
29 books have stale discount_pct values (>5% difference)

Worst cases:
| Book | Current | Correct |
|------|---------|---------|
| 572 | -691.7% | 55.8% |
| 554 | -50.1% | 56.6% |
| 533 | 6.7% | -68.0% |
| 500 | 64.7% | 22.4% |
| 494 | 67.1% | 26.8% |

### Solution (Not Yet Implemented)
1. **One-time fix**: Add `/health/recalculate-discounts` endpoint
2. **Ongoing fix**: Recalculate discount_pct whenever `value_mid` is updated

### Files to Modify
- `app/api/v1/health.py` - Add maintenance endpoint
- `app/api/v1/books.py` - Recalculate on FMV update (lines 1484, 1678, 1786, 1895)
- `app/worker.py` - Recalculate when analysis updates FMV (line 300)
- `app/eval_worker.py` - Recalculate when eval runbook updates FMV (line 173)

### GitHub Issue
https://github.com/markthebest12/bluemoxon/issues/796

---

## Files Reference

### Constants (Single Source of Truth)
- `frontend/src/config.ts` - `DEFAULT_ANALYSIS_MODEL`
- `backend/app/constants.py` - `DEFAULT_ANALYSIS_MODEL`

### Intentional Sonnet Usage (DO NOT CHANGE)
- `services/fmv_lookup.py` - FMV lookup
- `services/eval_generation.py` - Eval runbooks
- `api/v1/books.py` - `extract_structured_data` calls

### Model IDs (from bedrock.py)
- opus: `us.anthropic.claude-opus-4-5-20251101-v1:0`
- sonnet: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

---

## Lessons Learned

1. **Always trace complete data flow** - First fix only covered store, not direct API calls
2. **Search ALL occurrences** before fixing - Use `grep` across entire codebase
3. **Use constants** - Prevents drift when updating for future models
4. **Add sync tests** - Catches frontend/backend constant mismatches
5. **Register migrations in health.py** - CI validation catches this
6. **Use systematic-debugging skill** - Found discount_pct root cause quickly
7. **Check data at API level first** - The -692% came from API, not frontend

---

## Related Issues

### Carrier API (Separate Project)
GitHub issues #780-792 created with `carrier-api` label. Not blocked by this fix.

### Books Affected by Analysis Fix
- Book 581: "A Naturalists Voyage / Journal of Researches"
- Book 578: "The Book of Snobs"
- Book 579: "The History of Pendennis..."
