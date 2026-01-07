# Session: Parallelize Auth (#878)

**Date:** 2026-01-06
**Issue:** #878 - perf: [Quick Win] Parallelize /users/me with MFA preference check

## Goal

Parallelize the sequential API calls in `frontend/src/stores/auth.ts` checkAuth() to save ~500ms.

## Current State

In `checkAuth()` lines 82-118:
1. `api.get("/users/me")` - fetches role, names, mfa_exempt (~400-800ms)
2. `fetchMFAPreference()` - checks if TOTP enabled (~400-800ms, only if !mfa_exempt)

These are sequential but can run in parallel.

## Design Decision

**Approach:** Use Promise.all to parallelize both calls. Fetch MFA preference regardless of mfa_exempt status, but only use it if user is NOT exempt.

```typescript
// Parallel fetch
const [userResponse, mfaPreferenceResult] = await Promise.all([
  api.get("/users/me").catch(e => ({ error: e })),
  fetchMFAPreference().catch(() => null),
]);

// Process user data
if (!userResponse.error && userResponse.data) {
  // Apply role, names, mfa_exempt
}

// Conditionally use MFA preference
if (!isMfaExempt && mfaPreferenceResult) {
  // Check if TOTP enabled
}
```

## Implementation Plan

1. Write failing tests for parallel behavior
2. Refactor checkAuth() to use Promise.all
3. Ensure error handling preserved for both calls
4. Verify mfa_exempt logic still works

## Progress Log

- [x] Create feature branch `perf/parallelize-auth`
- [x] Write tests (TDD) - 5 tests for parallel behavior
- [x] Implement parallelization with Promise.all
- [x] Run lints and type-check - all pass
- [x] Full test suite: 288 tests pass
- [ ] Create PR to staging
- [ ] User review
- [ ] Merge to staging
- [ ] Validate in staging
- [ ] PR staging → main
- [ ] User review
- [ ] Merge to production
