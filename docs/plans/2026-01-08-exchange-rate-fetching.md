# Exchange Rate Fetching Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fetch live exchange rates from frankfurter.app when user selects GBP/EUR, with exponential backoff retry and fallback chain.

**Architecture:** When currency changes to GBP/EUR, fetch live rate with 3 retries (exponential backoff: 1s, 2s, 4s). On failure, fall back to DB cache, then hardcoded rates. Show warning toast on fallback. Cache successful rates for 15 minutes.

**Tech Stack:** Vue 3 composables, TypeScript, Vitest, native fetch API

**Design Doc:** `docs/plans/2026-01-08-exchange-rate-fetching-design.md`

---

## Task 1: Add Warning Toast Type

**Files:**
- Modify: `frontend/src/composables/useToast.ts`
- Modify: `frontend/src/composables/__tests__/useToast.spec.ts`

**Step 1: Write failing test for showWarning**

Add to `frontend/src/composables/__tests__/useToast.spec.ts` in the "showError" describe block area:

```typescript
describe("showWarning", () => {
  it("adds a warning toast", () => {
    const { showWarning, toasts, _reset } = useToast() as UseToastReturnDev;
    _reset();

    showWarning("Test warning");

    expect(toasts.value).toHaveLength(1);
    expect(toasts.value[0].type).toBe("warning");
    expect(toasts.value[0].message).toBe("Test warning");
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useToast.spec.ts
```

Expected: FAIL - "showWarning is not a function" or similar

**Step 3: Add warning type to Toast interface**

In `frontend/src/composables/useToast.ts`, change line 6:

```typescript
// Before
type: "error" | "success";

// After
type: "error" | "success" | "warning";
```

**Step 4: Add showWarning function**

In `frontend/src/composables/useToast.ts`, after the `showSuccess` function (around line 40):

```typescript
function showWarning(message: string): void {
  addToast("warning", message);
}
```

**Step 5: Update addToast parameter type**

In `frontend/src/composables/useToast.ts`, change line 42:

```typescript
// Before
function addToast(type: "error" | "success", message: string): void {

// After
function addToast(type: "error" | "success" | "warning", message: string): void {
```

**Step 6: Export showWarning in return types**

In `frontend/src/composables/useToast.ts`, add to UseToastReturn interface (around line 127):

```typescript
showWarning: (message: string) => void;
```

And add to the base object (around line 141):

```typescript
showWarning,
```

**Step 7: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useToast.spec.ts
```

Expected: PASS

**Step 8: Run all tests to verify no regressions**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run
```

Expected: All tests pass

**Step 9: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates
git add frontend/src/composables/useToast.ts frontend/src/composables/__tests__/useToast.spec.ts
git commit -m "feat: add warning toast type for exchange rate fallback notifications"
```

---

## Task 2: Add Live Rate Cache Structure

**Files:**
- Modify: `frontend/src/composables/useCurrencyConversion.ts`
- Modify: `frontend/src/composables/__tests__/useCurrencyConversion.spec.ts`

**Step 1: Write failing test for cache structure**

Add new describe block to `frontend/src/composables/__tests__/useCurrencyConversion.spec.ts`:

```typescript
describe("live rate cache", () => {
  it("exposes liveRateCache with null initial values", async () => {
    const { useCurrencyConversion, _getLiveRateCache } = await import("../useCurrencyConversion");
    useCurrencyConversion();

    const cache = _getLiveRateCache();
    expect(cache.GBP).toBeNull();
    expect(cache.EUR).toBeNull();
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: FAIL - "_getLiveRateCache is not a function"

**Step 3: Add cache structure to useCurrencyConversion.ts**

After the `cachedRates` declaration (around line 14), add:

```typescript
interface LiveRateCacheEntry {
  rate: number;
  fetchedAt: number;
}

const liveRateCache: {
  GBP: LiveRateCacheEntry | null;
  EUR: LiveRateCacheEntry | null;
} = {
  GBP: null,
  EUR: null,
};

const LIVE_RATE_TTL_MS = 15 * 60 * 1000; // 15 minutes
```

**Step 4: Export test helper for cache inspection**

At the bottom of the file, add:

```typescript
// For testing: inspect live rate cache
export function _getLiveRateCache(): typeof liveRateCache {
  return liveRateCache;
}
```

**Step 5: Update _resetCurrencyCache to also reset live cache**

Modify the `_resetCurrencyCache` function:

```typescript
export function _resetCurrencyCache(): void {
  cachedRates = null;
  ratesLoadPromise = null;
  sharedExchangeRates.value = DEFAULT_RATES;
  sharedLoadingRates.value = false;
  liveRateCache.GBP = null;
  liveRateCache.EUR = null;
}
```

**Step 6: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: PASS

**Step 7: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates
git add frontend/src/composables/useCurrencyConversion.ts frontend/src/composables/__tests__/useCurrencyConversion.spec.ts
git commit -m "feat: add live rate cache structure with 15-minute TTL"
```

---

## Task 3: Implement fetchLiveRate with Retry Logic

**Files:**
- Modify: `frontend/src/composables/useCurrencyConversion.ts`
- Modify: `frontend/src/composables/__tests__/useCurrencyConversion.spec.ts`

**Step 1: Write failing test for successful fetch**

Add to the "live rate cache" describe block:

```typescript
it("fetchLiveRate returns rate from frankfurter API", async () => {
  const mockResponse = {
    amount: 1,
    base: "GBP",
    date: "2026-01-08",
    rates: { USD: 1.25 },
  };

  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResponse),
  }));

  const { useCurrencyConversion } = await import("../useCurrencyConversion");
  const { fetchLiveRate } = useCurrencyConversion();

  const rate = await fetchLiveRate("GBP");

  expect(rate).toBe(1.25);
  expect(fetch).toHaveBeenCalledWith(
    "https://api.frankfurter.app/latest?from=GBP&to=USD",
    expect.objectContaining({ signal: expect.any(AbortSignal) })
  );

  vi.unstubAllGlobals();
});
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: FAIL - "fetchLiveRate is not a function"

**Step 3: Implement fetchLiveRate function**

Add before the `useCurrencyConversion` function:

```typescript
async function fetchLiveRate(currency: "GBP" | "EUR"): Promise<number | null> {
  const maxRetries = 4; // Initial + 3 retries
  const delays = [0, 1000, 2000, 4000]; // Exponential backoff

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    if (attempt > 0) {
      await new Promise((resolve) => setTimeout(resolve, delays[attempt]));
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(
        `https://api.frankfurter.app/latest?from=${currency}&to=USD`,
        { signal: controller.signal }
      );

      clearTimeout(timeoutId);

      if (!response.ok) {
        continue; // Retry on non-OK response
      }

      const data = await response.json();
      const rate = data.rates?.USD;

      if (typeof rate === "number" && rate > 0) {
        return rate;
      }
    } catch {
      // Network error or timeout - will retry
    }
  }

  return null; // All retries failed
}
```

**Step 4: Export fetchLiveRate from the composable return**

In the return statement of `useCurrencyConversion`, add:

```typescript
fetchLiveRate,
```

**Step 5: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: PASS

**Step 6: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates
git add frontend/src/composables/useCurrencyConversion.ts frontend/src/composables/__tests__/useCurrencyConversion.spec.ts
git commit -m "feat: implement fetchLiveRate with 5s timeout per request"
```

---

## Task 4: Add Retry Logic Tests

**Files:**
- Modify: `frontend/src/composables/__tests__/useCurrencyConversion.spec.ts`

**Step 1: Write test for retry on failure then success**

Add to "live rate cache" describe block:

```typescript
it("retries up to 3 times on failure before succeeding", async () => {
  const mockResponse = {
    amount: 1,
    base: "GBP",
    date: "2026-01-08",
    rates: { USD: 1.25 },
  };

  const mockFetch = vi.fn()
    .mockRejectedValueOnce(new Error("Network error"))
    .mockRejectedValueOnce(new Error("Network error"))
    .mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

  vi.stubGlobal("fetch", mockFetch);

  const { useCurrencyConversion } = await import("../useCurrencyConversion");
  const { fetchLiveRate } = useCurrencyConversion();

  const rate = await fetchLiveRate("GBP");

  expect(rate).toBe(1.25);
  expect(mockFetch).toHaveBeenCalledTimes(3);

  vi.unstubAllGlobals();
});
```

**Step 2: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: PASS (implementation already handles this)

**Step 3: Write test for all retries failing**

Add to "live rate cache" describe block:

```typescript
it("returns null after all retries fail", async () => {
  const mockFetch = vi.fn().mockRejectedValue(new Error("Network error"));
  vi.stubGlobal("fetch", mockFetch);

  const { useCurrencyConversion } = await import("../useCurrencyConversion");
  const { fetchLiveRate } = useCurrencyConversion();

  const rate = await fetchLiveRate("EUR");

  expect(rate).toBeNull();
  expect(mockFetch).toHaveBeenCalledTimes(4); // Initial + 3 retries

  vi.unstubAllGlobals();
});
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates
git add frontend/src/composables/__tests__/useCurrencyConversion.spec.ts
git commit -m "test: add retry logic tests for fetchLiveRate"
```

---

## Task 5: Add Cache Hit/Expiry Logic

**Files:**
- Modify: `frontend/src/composables/useCurrencyConversion.ts`
- Modify: `frontend/src/composables/__tests__/useCurrencyConversion.spec.ts`

**Step 1: Write test for cache hit within TTL**

Add to "live rate cache" describe block:

```typescript
it("returns cached rate without fetching if within TTL", async () => {
  const mockFetch = vi.fn();
  vi.stubGlobal("fetch", mockFetch);

  const { useCurrencyConversion, _getLiveRateCache } = await import("../useCurrencyConversion");
  const { fetchLiveRate } = useCurrencyConversion();

  // Manually set cache
  const cache = _getLiveRateCache();
  cache.GBP = { rate: 1.30, fetchedAt: Date.now() };

  const rate = await fetchLiveRate("GBP");

  expect(rate).toBe(1.30);
  expect(mockFetch).not.toHaveBeenCalled();

  vi.unstubAllGlobals();
});
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: FAIL - fetch is still called

**Step 3: Add cache check to fetchLiveRate**

Update `fetchLiveRate` to check cache first:

```typescript
async function fetchLiveRate(currency: "GBP" | "EUR"): Promise<number | null> {
  // Check cache first
  const cached = liveRateCache[currency];
  if (cached && Date.now() - cached.fetchedAt < LIVE_RATE_TTL_MS) {
    return cached.rate;
  }

  const maxRetries = 4;
  const delays = [0, 1000, 2000, 4000];

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    if (attempt > 0) {
      await new Promise((resolve) => setTimeout(resolve, delays[attempt]));
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(
        `https://api.frankfurter.app/latest?from=${currency}&to=USD`,
        { signal: controller.signal }
      );

      clearTimeout(timeoutId);

      if (!response.ok) {
        continue;
      }

      const data = await response.json();
      const rate = data.rates?.USD;

      if (typeof rate === "number" && rate > 0) {
        // Update cache
        liveRateCache[currency] = { rate, fetchedAt: Date.now() };
        return rate;
      }
    } catch {
      // Network error or timeout - will retry
    }
  }

  return null;
}
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: PASS

**Step 5: Write test for cache expiry**

Add to "live rate cache" describe block:

```typescript
it("fetches new rate when cache is expired", async () => {
  const mockResponse = {
    amount: 1,
    base: "GBP",
    date: "2026-01-08",
    rates: { USD: 1.28 },
  };

  const mockFetch = vi.fn().mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResponse),
  });
  vi.stubGlobal("fetch", mockFetch);

  const { useCurrencyConversion, _getLiveRateCache } = await import("../useCurrencyConversion");
  const { fetchLiveRate } = useCurrencyConversion();

  // Set expired cache (16 minutes ago)
  const cache = _getLiveRateCache();
  cache.GBP = { rate: 1.30, fetchedAt: Date.now() - 16 * 60 * 1000 };

  const rate = await fetchLiveRate("GBP");

  expect(rate).toBe(1.28); // New rate from API
  expect(mockFetch).toHaveBeenCalledTimes(1);

  vi.unstubAllGlobals();
});
```

**Step 6: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: PASS

**Step 7: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates
git add frontend/src/composables/useCurrencyConversion.ts frontend/src/composables/__tests__/useCurrencyConversion.spec.ts
git commit -m "feat: add 15-minute cache TTL for live exchange rates"
```

---

## Task 6: Implement Fallback Chain with Toast

**Files:**
- Modify: `frontend/src/composables/useCurrencyConversion.ts`
- Modify: `frontend/src/composables/__tests__/useCurrencyConversion.spec.ts`

**Step 1: Write test for fallback to DB cache with toast**

Add to "live rate cache" describe block:

```typescript
it("falls back to DB cache and shows warning toast when live fetch fails", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));

  // Mock toast
  const mockShowWarning = vi.fn();
  vi.mock("@/composables/useToast", () => ({
    useToast: () => ({ showWarning: mockShowWarning }),
  }));

  const { useCurrencyConversion } = await import("../useCurrencyConversion");
  const { exchangeRates, updateRateWithFallback } = useCurrencyConversion();

  // Set DB-cached rates
  exchangeRates.value = { gbp_to_usd_rate: 1.32, eur_to_usd_rate: 1.18 };

  await updateRateWithFallback("GBP");

  expect(exchangeRates.value.gbp_to_usd_rate).toBe(1.32); // Uses DB cache
  expect(mockShowWarning).toHaveBeenCalledWith("Using cached exchange rate");

  vi.unstubAllGlobals();
  vi.unmock("@/composables/useToast");
});
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: FAIL - "updateRateWithFallback is not a function"

**Step 3: Import useToast in useCurrencyConversion.ts**

Add at the top of the file:

```typescript
import { useToast } from "./useToast";
```

**Step 4: Implement updateRateWithFallback**

Add inside the `useCurrencyConversion` function, after `loadExchangeRates`:

```typescript
async function updateRateWithFallback(currency: "GBP" | "EUR"): Promise<void> {
  const { showWarning } = useToast();

  // Try live rate first
  const liveRate = await fetchLiveRate(currency);

  if (liveRate !== null) {
    // Success - update exchange rates
    if (currency === "GBP") {
      exchangeRates.value = { ...exchangeRates.value, gbp_to_usd_rate: liveRate };
    } else {
      exchangeRates.value = { ...exchangeRates.value, eur_to_usd_rate: liveRate };
    }
    return;
  }

  // Live failed - check if we have DB-cached rates (not default)
  const currentRate = currency === "GBP"
    ? exchangeRates.value.gbp_to_usd_rate
    : exchangeRates.value.eur_to_usd_rate;
  const defaultRate = currency === "GBP"
    ? DEFAULT_RATES.gbp_to_usd_rate
    : DEFAULT_RATES.eur_to_usd_rate;

  if (currentRate !== defaultRate) {
    // Using DB cache
    showWarning("Using cached exchange rate");
  } else {
    // Using hardcoded fallback
    showWarning("Using estimated exchange rate");
  }
}
```

**Step 5: Export updateRateWithFallback from the return**

Add to the return statement:

```typescript
updateRateWithFallback,
```

**Step 6: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: PASS

**Step 7: Write test for fallback to hardcoded with different toast**

Add to "live rate cache" describe block:

```typescript
it("shows 'estimated' warning when falling back to hardcoded rates", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));

  const mockShowWarning = vi.fn();
  vi.mock("@/composables/useToast", () => ({
    useToast: () => ({ showWarning: mockShowWarning }),
  }));

  const { useCurrencyConversion, _resetCurrencyCache } = await import("../useCurrencyConversion");
  _resetCurrencyCache(); // Reset to default rates
  const { updateRateWithFallback } = useCurrencyConversion();

  await updateRateWithFallback("EUR");

  expect(mockShowWarning).toHaveBeenCalledWith("Using estimated exchange rate");

  vi.unstubAllGlobals();
  vi.unmock("@/composables/useToast");
});
```

**Step 8: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: PASS

**Step 9: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates
git add frontend/src/composables/useCurrencyConversion.ts frontend/src/composables/__tests__/useCurrencyConversion.spec.ts
git commit -m "feat: implement fallback chain with warning toast notifications"
```

---

## Task 7: Wire Up Currency Change Watch

**Files:**
- Modify: `frontend/src/composables/useCurrencyConversion.ts`
- Modify: `frontend/src/composables/__tests__/useCurrencyConversion.spec.ts`

**Step 1: Write test for auto-fetch on currency change**

Add new describe block:

```typescript
describe("currency change watcher", () => {
  it("fetches live rate when currency changes to GBP", async () => {
    const mockResponse = {
      amount: 1,
      base: "GBP",
      date: "2026-01-08",
      rates: { USD: 1.27 },
    };

    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    }));

    const { useCurrencyConversion } = await import("../useCurrencyConversion");
    const { selectedCurrency, exchangeRates } = useCurrencyConversion();

    selectedCurrency.value = "GBP";
    await nextTick();
    await new Promise((r) => setTimeout(r, 100)); // Wait for async fetch

    expect(exchangeRates.value.gbp_to_usd_rate).toBe(1.27);

    vi.unstubAllGlobals();
  });

  it("does not fetch when currency changes to USD", async () => {
    const mockFetch = vi.fn();
    vi.stubGlobal("fetch", mockFetch);

    const { useCurrencyConversion } = await import("../useCurrencyConversion");
    const { selectedCurrency } = useCurrencyConversion();

    selectedCurrency.value = "USD";
    await nextTick();

    expect(mockFetch).not.toHaveBeenCalled();

    vi.unstubAllGlobals();
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: FAIL - exchangeRates not updated on currency change

**Step 3: Add watch import**

Update the import at the top of `useCurrencyConversion.ts`:

```typescript
import { ref, computed, watch } from "vue";
```

**Step 4: Add watcher inside useCurrencyConversion**

Add at the end of the `useCurrencyConversion` function, before the return statement:

```typescript
// Watch for currency changes and fetch live rates
watch(selectedCurrency, async (newCurrency) => {
  if (newCurrency === "GBP" || newCurrency === "EUR") {
    await updateRateWithFallback(newCurrency);
  }
});
```

**Step 5: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run src/composables/__tests__/useCurrencyConversion.spec.ts
```

Expected: PASS

**Step 6: Run all tests**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run
```

Expected: All tests pass

**Step 7: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates
git add frontend/src/composables/useCurrencyConversion.ts frontend/src/composables/__tests__/useCurrencyConversion.spec.ts
git commit -m "feat: auto-fetch live rates on currency selection change"
```

---

## Task 8: Final Validation and Lint

**Step 1: Run type check**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run type-check
```

Expected: No errors

**Step 2: Run linter**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run lint
```

Expected: No errors

**Step 3: Run formatter**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run format
```

**Step 4: Run all tests one final time**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates/frontend
npm run test -- --run
```

Expected: All tests pass

**Step 5: Commit any format changes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates
git add -A
git diff --cached --quiet || git commit -m "style: apply prettier formatting"
```

---

## Task 9: Create PR to Staging

**Step 1: Push branch**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-898-exchange-rates
git push -u origin feat/898-exchange-rate-fetching
```

**Step 2: Create PR**

```bash
gh pr create --base staging --title "feat: Add real-time exchange rate fetching (#898)" --body "$(cat <<'EOF'
## Summary
- Fetches live exchange rates from frankfurter.app when user selects GBP/EUR
- Exponential backoff retry: 3 retries at 1s, 2s, 4s delays
- Fallback chain: Live API → DB cache → Hardcoded rates
- Warning toast on fallback ("Using cached/estimated exchange rate")
- 15-minute cache TTL to avoid excessive API calls

## Test Plan
- [ ] CI passes
- [ ] Manual test: Select GBP, verify rate updates
- [ ] Manual test: Disable network, verify fallback toast appears
- [ ] Manual test: Verify cache prevents refetch within 15 minutes

Closes #898
EOF
)"
```

**Step 3: Watch CI**

```bash
gh pr checks --watch
```

---

## Post-Implementation

After PR is merged to staging:
1. Test on staging.app.bluemoxon.com
2. Create PR from staging → main
3. Watch deploy workflow after merge
