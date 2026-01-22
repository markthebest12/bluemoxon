# Auth Retry on Cold Start Design

**Date:** 2026-01-22
**Issue:** Cold start causes incorrect viewer role until manual refresh

## Problem Statement

During Lambda cold start, the `/users/me` API call times out (5s timeout vs ~7s cold start). The current code treats timeout as "no data" and defaults to viewer role. The loading overlay clears, but the user is stuck with incorrect permissions until manual refresh.

## Solution Overview

Retry `/users/me` with exponential backoff until success or max attempts reached. The loading overlay stays visible throughout. On complete failure, show an error screen with retry option.

## Success Criteria

- Admin users see Acquisitions tab on first load without refresh
- User's name (not email) appears in dropdown on first load
- Loading overlay stays until real role is confirmed
- Graceful error handling if API is genuinely unavailable

## Technical Approach

The retry logic wraps only the `/users/me` call, not the entire `checkAuth()` function. This is because:

- Cognito auth (`getCurrentUser`) is fast and reliable
- MFA preference can fail gracefully (already handled)
- `/users/me` is the only call that must succeed for correct UI

### Retry Configuration

- Max attempts: 3
- Backoff: 2s, 4s, 8s (exponential)
- Total max wait: ~14 seconds + API response times
- No timeout per attempt (let the call complete or fail naturally)

### State Changes

- `authInitializing` stays `true` until `/users/me` succeeds or all retries exhausted
- New state: `authError` - set when all retries fail, triggers error screen
- Remove the 5s `withTimeout` wrapper for `/users/me` (it causes the problem)

### Error Screen

- Shows when `authError` is true
- Simple message: "Unable to connect. Please check your connection and try again."
- "Retry" button calls `initializeAuth()` again

## Implementation Details

### File: `frontend/src/stores/auth.ts`

1. Add `authError` ref (new state for error screen)
2. Create `fetchUserProfileWithRetry()` helper:
   - Calls `/users/me` up to 3 times
   - Waits 2s, 4s, 8s between attempts
   - Returns data on success, throws on complete failure
3. Modify `checkAuth()`:
   - Remove `withTimeout` wrapper from `/users/me`
   - Use `fetchUserProfileWithRetry()` instead
   - Keep `withTimeout` for MFA check (it can fail gracefully)
4. Modify `initializeAuth()`:
   - Set `authError = false` at start
   - Set `authError = true` if retry exhausted
   - Clear `authError` on successful auth

### File: `frontend/src/App.vue`

1. Add error screen template (shown when `authError` is true)
2. Priority: error screen > loading overlay > main content

### Tests to add

- Retry succeeds on 2nd attempt -> user gets correct role
- All retries fail -> `authError` is true
- Retry button clears error and retries
