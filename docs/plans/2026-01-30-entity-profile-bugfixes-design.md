# Entity Profile Bug Fixes Design

## Issues

- #1558: `regenerateProfile` composable doesn't set `loadingState` on error
- #1551: No `AbortController` on `fetchProfile` — race condition on rapid navigation
- #1554: Missing `TimestampMixin` on `EntityProfile` model

## Fix 1: regenerateProfile error state (#1558)

**File:** `frontend/src/composables/entityprofile/useEntityProfile.ts`

The `catch` block in `regenerateProfile` sets `error.value` but never sets `loadingState.value = "error"`. The `hasError` computed stays `false` and error UI never renders.

**Change:** Add `loadingState.value = "error"` in the catch block.

## Fix 2: AbortController race condition (#1551)

**File:** `frontend/src/composables/entityprofile/useEntityProfile.ts`

`fetchProfile` fires an API request with no cancellation. Rapid navigation (Author A → Author B) can show stale data if Author A's response arrives second.

**Change:** Add an `AbortController` instance scoped to the composable. Abort previous request at the start of each `fetchProfile` call. Pass signal to `api.get`. Silently ignore aborted requests in the catch block.

## Fix 3: TimestampMixin on EntityProfile (#1554)

**Files:**
- `backend/app/models/entity_profile.py` — add `TimestampMixin`
- New Alembic migration — add `created_at` and `updated_at` columns, backfill `created_at` from `generated_at`

**Change:** Add `TimestampMixin` to the `EntityProfile` class. Create migration that adds the columns with server defaults and backfills `created_at = generated_at` for existing rows.

## Testing

- Fix 1: Unit test that `regenerateProfile` error sets `loadingState` to `"error"`
- Fix 2: Existing tests still pass; verify abort logic doesn't break happy path
- Fix 3: Backend test that `EntityProfile` has `created_at` and `updated_at` fields

## Branch

`fix/entity-profile-reliability` — single branch, all three fixes are entity-profile reliability.
