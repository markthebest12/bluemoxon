# Session: Cold Start UX Improvement

**Date:** 2026-01-21
**Issue:** #1227
**Branch:** feat/cold-start-loading-ux
**PR:** #1228

## Problem

During Lambda cold start (~7 seconds), users experience jarring UX:
1. Navigation renders immediately with incomplete state
2. Acquisitions tab is missing initially (for admin users)
3. User has to reload multiple times to see correct navigation
4. Tab suddenly appearing after reload is clunky

## Root Cause

Race condition in auth initialization:
- `t=0ms`: App mounts, NavBar renders immediately
- `t=0ms`: NavBar reads `authStore.isAdmin` → `user.value` is null → returns false
- `t=100ms`: Route guard calls `authStore.checkAuth()` → calls `/users/me` API
- `t=7000ms`: Lambda cold start completes, role loads, tab appears

Key files:
- `frontend/src/components/layout/NavBar.vue` - No loading state check
- `frontend/src/stores/auth.ts` - Has `loading` ref but unused by NavBar
- `frontend/src/main.ts` - App mounts before auth completes
- `frontend/src/router/index.ts` - Auth check happens in route guard

## Design Decision

**Option A**: Loading Overlay

Show loading indicator while auth initializes. Caching was initially considered (Option C) but removed during code review as it added complexity without meaningful benefit - the overlay must wait for fresh auth regardless.

## Implementation

### Auth Store Changes (`frontend/src/stores/auth.ts`)

1. Added `authInitializing` ref - true until first auth check completes
2. Added `initializeAuth()` function:
   - Race condition guard prevents multiple concurrent calls
   - Calls `checkAuth()` and waits for completion
   - Sets `authInitializing` to false when done
3. `isAdmin`/`isEditor` computed only use verified `user.value?.role`

### App.vue Changes

1. Added `onMounted()` hook to call `authStore.initializeAuth()`
2. Added conditional rendering:
   - Shows loading overlay with BlueMoxon branding when `authInitializing` is true
   - Shows NavBar/RouterView when `authInitializing` is false

### Tests Added

- `src/stores/__tests__/auth.spec.ts`: 6 tests for cold start/auth initialization
- `src/__tests__/App.spec.ts`: 5 tests for loading overlay

## Progress

- [x] Created GitHub issue #1227
- [x] Explored codebase and identified root cause
- [x] Design approach selection (Option A)
- [x] Implementation with TDD
- [x] Code review: removed unused caching code, simplified to single flag
- [x] All 579 tests passing
- [x] PR #1228 to staging created
- [ ] Manual testing in staging
- [ ] PR to main
