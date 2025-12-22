# Session: Spinner/Status Refresh Fix

**Date:** 2025-12-22
**Issue:** #554
**Status:** Design APPROVED - Ready for Implementation

---

## CRITICAL REMINDERS FOR CONTINUATION

### 1. Use Superpowers Skills at ALL Stages
- **Before debugging:** Use `superpowers:systematic-debugging` - NO fixes without root cause investigation
- **Before coding:** Use `superpowers:brainstorming` to refine approach
- **For implementation:** Use `superpowers:writing-plans` then `superpowers:executing-plans`
- **For parallel work:** Use `superpowers:dispatching-parallel-agents` for independent tasks
- **Before completing:** Use `superpowers:verification-before-completion` - evidence before assertions
- **For TDD:** Use `superpowers:test-driven-development` - write failing test first

### 2. Bash Command Formatting (CLAUDE.md)
**NEVER use these - they trigger permission prompts:**
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

## Problem Statement

Spinners and status indicators on the Acquisitions page get stuck for both eval runbook and analysis workflows. The only workaround is a manual browser refresh.

## Observed Symptoms

| Workflow | Symptom | After Browser Refresh |
|----------|---------|----------------------|
| **Eval Runbook** | Stuck on "Generating runbook..." forever | Shows "Eval Runbook" link (job completed) |
| **Analysis** | Cycles: Generate → Queued → Analyzing → Generate | Shows "View Analysis" link (job completed) |

**Key insight:** Both jobs complete successfully on backend (<1 min). Frontend fails to detect completion.

## Failed Fix Attempts (History)

| Issue | Date | Fix Attempted | Why It Failed |
|-------|------|---------------|---------------|
| #382 | Dec 18 | First report | N/A |
| #471 | Dec 19 | Added polling to BookDetailView | Helped BookDetailView, not Acquisitions |
| #499 | Dec 21 | Added `clearJob()` in catch blocks | Dual source of truth still causes issues |

## Root Cause Analysis

### Architecture Problems

1. **Two conflicting sources of truth:**
   - In-memory Maps: `activeAnalysisJobs`, `activeEvalRunbookJobs`
   - Backend fields: `book.analysis_job_status`, `book.eval_runbook_job_status`

2. **UI displays from BOTH sources with OR logic:**
   ```vue
   v-if="isAnalysisRunning(book.id) || book.analysis_job_status"
   ```

3. **Multiple overlapping polling mechanisms:**
   - `startJobPoller()` - polls individual job status (5s)
   - `jobCheckInterval` - checks for completed jobs (2s)
   - `syncBackendJobPolling()` - reconciles on mount/import

4. **Completion detection fails because:**
   - Poller detects completion but book's `has_analysis`/`has_eval_runbook` not updated
   - `acquisitionsStore.refreshBook()` may race with status updates
   - Vue reactivity with Maps is fragile

### Why Each Symptom Occurs

**Eval Runbook stuck:**
- Job completes, but neither `clearEvalRunbookJob()` triggers nor `has_eval_runbook` updates
- Spinner condition remains true

**Analysis reverts to button:**
- Job completes, `clearJob()` removes from Map
- But `has_analysis` not updated on book object
- No active job + no `has_analysis` = shows Generate button

---

## APPROVED DESIGN: `useJobPolling` Composable

### Core Concept

A single, reusable Vue composable that replaces ALL scattered polling logic. Components call it and react to state changes.

### Interface

```typescript
// Usage in component
const {
  isActive,      // boolean - is a job running?
  status,        // 'pending' | 'running' | 'completed' | 'failed' | null
  error,         // error message if failed
  start,         // (bookId) => start polling for a job
  stop,          // () => stop polling
} = useJobPolling('analysis')  // or 'eval-runbook'
```

### How It Works

```
User clicks "Generate"
    → Component calls API to start job
    → Component calls polling.start(bookId)
    → Composable polls /status endpoint every 3s
    → When status = 'completed':
        1. Stop polling
        2. Refetch book data (updates has_analysis/has_eval_runbook)
        3. Emit completion
    → Component reactively shows correct UI
```

### Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Source of truth** | Composable state only | Eliminates dual-source bugs |
| **Poll interval** | 3 seconds | Fast enough for <1min jobs |
| **On completion** | Refetch book data | Guarantees `has_*` flags update |
| **Scope** | Per-book, per-job-type | Multiple books can poll independently |
| **Cleanup** | Auto on unmount | No memory leaks |

### Files to Change

| File | Change |
|------|--------|
| `composables/useJobPolling.ts` | **NEW** - the composable |
| `stores/books.ts` | Remove polling logic, keep API methods only |
| `views/AcquisitionsView.vue` | Use composable, remove manual intervals |
| `views/BookDetailView.vue` | Use composable |
| `components/EditWatchlistModal.vue` | Use composable if needed |

### What to Remove

From `stores/books.ts`:
- `activeAnalysisJobs` Map
- `activeEvalRunbookJobs` Map
- `analysisJobPollers` Map
- `evalRunbookJobPollers` Map
- `startJobPoller()`, `stopJobPoller()`, `clearJob()`
- `startEvalRunbookJobPoller()`, `stopEvalRunbookJobPoller()`, `clearEvalRunbookJob()`
- `getActiveJob()`, `hasActiveJob()`
- `getActiveEvalRunbookJob()`, `hasActiveEvalRunbookJob()`

From `AcquisitionsView.vue`:
- `jobCheckInterval` (2s interval)
- `syncBackendJobPolling()`
- All the `getJobStatus()`, `isAnalysisRunning()` functions

---

## Implementation Plan

### Phase 1: Create Composable
1. Create `frontend/src/composables/useJobPolling.ts`
2. Write unit tests for the composable
3. Test in isolation

### Phase 2: Integrate in AcquisitionsView
1. Import and use composable for each book with active job
2. Update template to use composable state
3. Remove old polling code
4. Test manually

### Phase 3: Integrate in BookDetailView
1. Same pattern as AcquisitionsView
2. Remove old polling code

### Phase 4: Clean up books.ts store
1. Remove all polling-related code
2. Keep only API methods

### Phase 5: Test and Deploy
1. Test all scenarios on staging
2. Create PR
3. Deploy to production

---

## Related Files

- `frontend/src/stores/books.ts` - Current polling logic (to be simplified)
- `frontend/src/views/AcquisitionsView.vue` - Status display (to be updated)
- `frontend/src/views/BookDetailView.vue` - Similar polling pattern (to be updated)
- `backend/app/api/v1/books.py` - Status endpoints (no changes needed)

---

## Next Steps

1. Use `superpowers:writing-plans` to create detailed implementation tasks
2. Use `superpowers:test-driven-development` - write composable tests first
3. Implement composable
4. Integrate into views
5. Clean up old code
6. Test and deploy
