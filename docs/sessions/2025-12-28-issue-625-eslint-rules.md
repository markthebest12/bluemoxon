# Session: Issue #625 - Enable Stricter TypeScript-ESLint Rules

**Date:** 2025-12-28
**Issue:** https://github.com/bluemoxon/bluemoxon/issues/625

## CRITICAL SESSION RULES

### Superpowers Skills - MANDATORY
**Use Superpowers skills at ALL stages:**
- `superpowers:brainstorming` - Before any implementation
- `superpowers:systematic-debugging` - For any bug/issue
- `superpowers:verification-before-completion` - Before claiming done
- `superpowers:requesting-code-review` - After significant code changes

### Bash Command Rules - NEVER VIOLATE
**NEVER use (trigger permission prompts):**
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

## Background

With ESLint 9 migration complete (#567), enable stricter typescript-eslint rules to catch bugs earlier.

## Goals

1. Enable `no-floating-promises` (highest value - catches forgotten awaits)
2. Fix any violations found
3. Gradually enable additional rules
4. Document rule decisions

## Progress Log

### Session 1: Initial Implementation

**Brainstorming Complete - Decisions:**
1. **Scope:** High-value async rules only (no-floating-promises, no-misused-promises)
2. **Severity:** Both as "error" (blocks CI)
3. **Excluded:** require-await (lower value, for follow-up)

Design document: `docs/plans/2025-12-28-eslint-stricter-rules-design.md`

**Implementation:**
- `eslint.config.js` - Added type-aware rules configuration
- Fixed 34 violations across 18 files using `void` operator pattern
- All validations passed: lint, type-check, build

**PR #636 Created** targeting staging

---

### Session 2: Code Review Fixes (CURRENT)

**Code Review Feedback Received** - 6 issues identified:

#### CRITICAL Issues (Fixed ✅)
1. **AnalysisViewer.vue behavior regression** - `onComplete` changed from async/await to void, causing `generating.value = false` to run before `loadAnalysis()` completes
   - **Fix:** Restored async/await with try/finally block

2. **main.ts silent failure** - `void initApp()` swallows initialization errors
   - **Fix:** Added `.catch()` with error handler showing user-visible error message

#### HIGH Issues (Fixed ✅)
3. **useJobPolling.ts error swallowing** - setInterval callback used `void poll()`
   - **Fix:** Added explicit `.catch()` that logs and stops polling on error

4. **listings.ts error swallowing** - Same issue with extraction polling
   - **Fix:** Added explicit `.catch()` that logs error

5. **AdminView.vue clipboard** - `void navigator.clipboard.writeText()` silently fails
   - **Fix:** Added `.then()` with success feedback and error alert

#### MEDIUM Issues (Fixed ✅)
6. **ESLint config duplication** - Two similar blocks unexplained
   - **Fix:** Added comment explaining why separate blocks required (extraFileExtensions incompatibility)

### Files Modified in Session 2
- `src/components/books/AnalysisViewer.vue` - Restored async/await for onComplete
- `src/main.ts` - Added error handler with user-visible message
- `src/composables/useJobPolling.ts` - Added .catch() for polling errors
- `src/stores/listings.ts` - Added .catch() for extraction polling
- `src/views/AdminView.vue` - Added clipboard success/error handling
- `eslint.config.js` - Added explanatory comment for separate config blocks

---

## Next Steps

1. **Run verification** - `npm run lint`, `npm run type-check`, `npm run build`
2. **Push fixes to PR #636**
3. **Request re-review**
4. **After approval:** Merge to staging, validate, then PR staging → main

## Key Learnings

1. `void` is a linter silencer, not error handling - use `.catch()` for fire-and-forget calls that should log failures
2. Behavior changes (async→sync) are subtle bugs - always check if timing matters
3. App initialization errors should show user-visible feedback, not fail silently
4. Separate ESLint config blocks needed when parserOptions differ (extraFileExtensions)

