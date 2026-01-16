# Issue 852: Fix Book Type and Remove `as any` Casts

**Date:** 2026-01-05
**Issue:** [#852](https://github.com/bluemoxon/bluemoxon/issues/852)
**Branch:** `refactor/issue-852-book-type-casts`

## Problem

`BookForm.vue:105-133` contained 8 consecutive `as any` casts in the `populateForm` function.

## Investigation Finding

The issue description claimed "the Book interface doesn't include these fields" - but **this was incorrect**. The `Book` interface in `stores/books.ts` already includes ALL the fields:

- `edition: string | null` (line 34)
- `binding_description: string | null` (line 40)
- `condition_grade: string | null` (line 41)
- `condition_notes: string | null` (line 42)
- `purchase_price: number | null` (line 46)
- `acquisition_cost: number | null` (line 47)
- `purchase_date: string | null` (line 48)
- `purchase_source: string | null` (line 49)
- `provenance: string | null` (line 54)

The `as any` casts were **unnecessary technical debt** from when the interface was incomplete.

## Solution

Simple cleanup - removed all 8 `as any` casts from `populateForm()` function in `BookForm.vue`.

Also fixed a subtle bug: changed `|| null` to `?? null` for numeric fields (`purchase_price`, `acquisition_cost`) to handle the case where value is `0` (which would be falsy with `||`).

## Verification

- [x] `npm run type-check` - PASSED
- [x] `npm run lint` - PASSED

## Files Changed

- `frontend/src/types/errors.ts` - **NEW** - Type guard and helper for axios-like errors
- `frontend/src/components/books/BookForm.vue`:
  - Removed 8 `(book as any)` casts in `populateForm()`
  - Changed `const data: any` → `Record<string, unknown>`
  - Changed `catch (e: any)` → `catch (e: unknown)` with proper type guard via `getErrorMessage()`

## PR

- **PR #868**: <https://github.com/markthebest12/bluemoxon/pull/868>
- **Status**: Ready for review before merging to staging
