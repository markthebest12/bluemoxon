# Session: Enable Strict ESLint no-explicit-any Rule

**Date:** 2026-01-05
**Branch:** refactor/health-migrations (will need new branch for this work)
**Issue:** User requested enabling stricter ESLint rules

## Problem Statement

The frontend ESLint config had `@typescript-eslint/no-explicit-any: "off"` with comment "can tighten later". After running cleanly in pipelines for a while, user decided to enable strict mode.

## Initial State

- **Config:** `@typescript-eslint/no-explicit-any: "off"` in `frontend/eslint.config.js`
- **Violations:** 99 `any` type usages across 27 files
- **Pattern:** Most were catch blocks (`catch (e: any)`) and some were test mocks

## Changes Made

1. **ESLint config updated:**

   ```javascript
   // Disallow explicit any - use proper types instead
   "@typescript-eslint/no-explicit-any": "error",
   ```

2. **Files fixed by parallel agents:** Used 4 agents to fix files in parallel:
   - Agent 1: Store files (admin.ts, auth.ts, books.ts, evalRunbook.ts, listings.ts, acquisitions.ts)
   - Agent 2: Vue components (AcquireModal, AddToWatchlistModal, BookForm, etc.)
   - Agent 3: View files (AcquisitionsView, BookDetailView, LoginView, etc.)
   - Agent 4: Test files and ImportListingModal

3. **Fix patterns applied:**
   - `catch (e: any)` → `catch (e: unknown)` with type narrowing
   - For axios errors: `const err = e as { response?: { data?: { detail?: string } }; message?: string };`
   - For Error objects: `const message = e instanceof Error ? e.message : "Default message";`
   - Test mocks: `as unknown as TypeName` instead of `as any`
   - Created interfaces for typed data (SearchResult, BookImage, ListingData, etc.)

## Current Status (Last Updated: 2026-01-06 06:02 UTC)

- **Progress:** ✅ COMPLETE - Deployed to production
- **Branch:** `chore/eslint-strict-any` (merged to `staging`, then `main`)
- **PRs:**
  - #870 - Initial merge to staging (squash merged)
  - #872 - Promote staging to production (squash merged)
- **Commits:** 4 total
  1. `chore: Enable strict ESLint rules for TypeScript and Vue`
  2. `fix: address code review feedback for ESLint strict any`
  3. `fix: use error helpers consistently across all components`
  4. `style: fix prettier formatting in ImageCarousel and BookDetailView`
- **Staging Deploy:** ✅ Version `2026.01.06-d9f07af`
- **Production Deploy:** ✅ Version `2026.01.06-da06752`
- **Health Check:** ✅ All checks healthy (database, S3, Cognito, config)

## Code Review Feedback (ALL FIXED)

### P1 - HIGH: Inconsistent Error Handling ✅ FIXED

- Replaced all 23 inline error patterns with `getErrorMessage()` across 6 files
- Files updated: admin.ts, listings.ts, evalRunbook.ts, AdminConfigView.vue, AcquisitionsView.vue, BookDetailView.vue

### P1 - HIGH: Type Guard is Logically Broken ✅ FIXED

```typescript
// Before (broken - matched all Errors):
return typeof e === "object" && e !== null && ("response" in e || "message" in e);

// After (correct - only matches axios-like errors):
return typeof e === "object" && e !== null && "response" in e;
```

### P2 - MEDIUM: HTTP Status Checking Not Centralized ✅ FIXED

Added `getHttpStatus()` helper to `types/errors.ts`:

```typescript
export function getHttpStatus(e: unknown): number | undefined {
  if (typeof e === "object" && e !== null && "response" in e) {
    return (e as { response?: { status?: number } }).response?.status;
  }
  return undefined;
}
```

### P2 - MEDIUM: 15 Warnings Left Unfixed ✅ FIXED

- Added prop defaults in `withDefaults()` for 13 optional props across:
  - ArchiveStatusBadge.vue (1 prop)
  - ScoreCard.vue (5 props)
  - TrackingCard.vue (7 props)
- Added eslint-disable-next-line for 2 v-html usages in AnalysisViewer.vue with explanation

### P2 - MEDIUM: Test Mocks Are Type-Safety Theater

**Deferred:** Would require significant refactor of test utilities. Current pattern works and tests pass.

### P3 - LOW: Interface Scattering ✅ FIXED (partial)

- Consolidated duplicate `BookImage` interface to `types/books.ts`
- Updated BookDetailView.vue and ImageCarousel.vue to import from shared location
- Remaining interfaces (ExtractedOrderData, SearchResult) are component-specific

---

## CRITICAL REMINDERS FOR CONTINUATION

### 1. Superpowers Skills - MANDATORY

**ALWAYS invoke relevant skills BEFORE any action:**

- `superpowers:brainstorming` - Before any creative/feature work
- `superpowers:systematic-debugging` - Before fixing any bug
- `superpowers:test-driven-development` - Before implementing features
- `superpowers:verification-before-completion` - Before claiming work is done

If there's even a 1% chance a skill applies, INVOKE IT FIRST.

### 2. Bash Command Rules - NEVER USE THESE

These trigger permission prompts and break auto-approve:

```bash
# BAD - NEVER use:
# This is a comment before command
command1 \
  --with-continuation
$(command substitution)
command1 && command2
command1 || command2
--password 'Test1234!'  # ! gets corrupted
```

### 3. Bash Command Rules - ALWAYS USE THESE

```bash
# GOOD - Always use:
command1 --single-line
# Then make separate Bash tool call for:
command2 --single-line

# Use bmx-api for all BlueMoxon API calls:
bmx-api GET /books
bmx-api --prod GET /books/123
```

### 4. File Paths

- Session log: `/Users/mark/projects/bluemoxon/docs/sessions/2026-01-05-eslint-strict-any.md`
- ESLint config: `/Users/mark/projects/bluemoxon/frontend/eslint.config.js`
- Working directory: `/Users/mark/projects/bluemoxon/frontend`

---

## Files Changed Summary

| File | Errors Fixed |
|------|-------------|
| `eslint.config.js` | Rule changed to "error" |
| **Stores** | |
| `stores/admin.ts` | 12 catch blocks |
| `stores/auth.ts` | 6 catch blocks |
| `stores/books.ts` | 6 catch blocks |
| `stores/evalRunbook.ts` | 4 catch blocks |
| `stores/acquisitions.ts` | 1 catch block |
| `stores/listings.ts` | 2 catch blocks |
| **Components** | |
| `components/AddToWatchlistModal.vue` | 4 catch blocks |
| `components/AddTrackingModal.vue` | 1 catch block |
| `components/EditWatchlistModal.vue` | 1 catch block |
| `components/NotificationPreferences.vue` | 2 catch blocks |
| `components/PasteOrderModal.vue` | 1 catch block |
| `components/ImportListingModal.vue` | 6 errors |
| `components/books/AnalysisViewer.vue` | 4 catch blocks |
| `components/books/BookForm.vue` | 11 errors |
| `components/books/EvalRunbookModal.vue` | 1 catch block |
| `components/books/ImageReorderModal.vue` | 1 catch block |
| `components/books/ImageUploadModal.vue` | 1 catch block |
| **Views** | |
| `views/AcquisitionsView.vue` | 1 catch block |
| `views/BookDetailView.vue` | 7 errors |
| `views/LoginView.vue` | 4 catch blocks |
| `views/ProfileView.vue` | 2 catch blocks |
| `views/SearchView.vue` | 2 errors (interface + param) |
| **Tests** | |
| `__tests__/TrackingCard.spec.ts` | 5 errors |
| `__tests__/acquisitions.spec.ts` | 17 errors |
| `__tests__/books-generate.spec.ts` | 1 error |
| `__tests__/useJobPolling.test.ts` | 1 error |
| `e2e/performance.spec.ts` | 1 error |
