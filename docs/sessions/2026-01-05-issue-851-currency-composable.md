# Session: Issue #851 - Extract Currency Conversion Composable

**Date:** 2026-01-05
**Issue:** https://github.com/markthebest12/bluemoxon/issues/851

## Problem Statement

~30 lines of identical currency conversion logic duplicated across 4 components:
- `BookForm.vue`
- `AcquireModal.vue`
- `AddToWatchlistModal.vue`
- `EditWatchlistModal.vue`

## Solution

Create `useCurrencyConversion` composable to centralize:
- `exchangeRates` ref with fallback rates
- `currencySymbol` computed property
- `loadExchangeRates()` function
- `convertToUsd()` function

## Progress Log

### Session Start
- Fetched issue #851 details
- Identified 4 components with duplicated code
- Planning TDD approach

---

## Decisions Made

1. **Null handling:** Return `null` for null/undefined inputs (preserves semantic difference)
2. **Rounding:** Always round to 2 decimal places (consistent currency display)
3. **Loading state:** Include `loadingRates` ref (consistent API)

## Design Document

Written to: `docs/plans/2026-01-05-issue-851-currency-composable-design.md`

## Files to Change

| File | Action |
|------|--------|
| `composables/useCurrencyConversion.ts` | Create |
| `composables/__tests__/useCurrencyConversion.spec.ts` | Create |
| `components/books/BookForm.vue` | Refactor |
| `components/AcquireModal.vue` | Refactor |
| `components/AddToWatchlistModal.vue` | Refactor |
| `components/EditWatchlistModal.vue` | Refactor |

## PRs Created

(To be updated during implementation)
