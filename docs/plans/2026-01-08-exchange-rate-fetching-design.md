# Design: Real-time Exchange Rate Fetching

**Issue:** #898
**Date:** 2026-01-08
**Status:** Approved

## Overview

Add real-time exchange rate fetching from frankfurter.app when user selects GBP or EUR currency, with fallback chain and retry logic.

## Architecture

### Trigger

When `selectedCurrency` changes to GBP or EUR, fetch live rate from frankfurter.app.

### Fallback Chain

```
Live API (frankfurter.app)
    ↓ (if fails after retries)
DB Cache (/admin/config)
    ↓ (if fails)
Hardcoded DEFAULT_RATES
```

### Caching

15-minute TTL per currency. Stored in module-level cache.

### User Feedback

Toast notification when falling back:

- "Using cached exchange rate" (DB cache used)
- "Using estimated exchange rate" (hardcoded used)

## Implementation Details

### New Function

```typescript
async function fetchLiveRate(currency: 'GBP' | 'EUR'): Promise<number | null>
```

### Retry Logic

- Exponential backoff: attempts at 0s, 1s, 2s, 4s (total ~7s max)
- Uses `fetch()` with AbortController for timeout (5s per request)
- Returns `null` on complete failure, triggering fallback

### Cache Structure

```typescript
const liveRateCache = {
  GBP: { rate: number, fetchedAt: number } | null,
  EUR: { rate: number, fetchedAt: number } | null
}
```

### Currency Change Watch

- `watch(selectedCurrency, ...)` inside the composable
- Only triggers fetch for GBP/EUR, not USD
- Shows loading state during fetch

## Error Handling

| Situation | Toast Message | Type |
|-----------|---------------|------|
| Live API fails, DB cache works | "Using cached exchange rate" | warning |
| Live API + DB fail, hardcoded used | "Using estimated exchange rate" | warning |

No toast when:

- Live API succeeds (happy path)
- Cache hit within 15 minutes (no fetch needed)

## Testing Strategy

1. **Happy path** - Mock fetch returns rate, verify cache updated
2. **Retry logic** - Mock fetch fails twice then succeeds, verify 3 attempts made
3. **Fallback to DB** - Mock fetch fails all retries, verify DB cache used + toast
4. **Fallback to hardcoded** - Mock both fetch and DB fail, verify DEFAULT_RATES used + toast
5. **Cache TTL** - Verify fresh cache skips fetch, expired cache triggers fetch
6. **USD no-op** - Verify switching to USD doesn't trigger any fetch

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/composables/useCurrencyConversion.ts` | Add `fetchLiveRate()`, cache structure, watch for currency changes |
| `frontend/src/composables/__tests__/useCurrencyConversion.spec.ts` | Add tests for retry, fallback, caching |

## API Reference

- Endpoint: `https://api.frankfurter.app/latest?from=GBP&to=USD`
- Free, no API key required
- Response: `{"amount":1,"base":"GBP","date":"2026-01-06","rates":{"USD":1.2513}}`
