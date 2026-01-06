# Design: Extract Currency Conversion Composable

**Issue:** #851
**Date:** 2026-01-05
**Status:** Approved

## Problem

~30 lines of identical currency conversion logic duplicated across 4 components:
- `BookForm.vue`
- `AcquireModal.vue`
- `AddToWatchlistModal.vue`
- `EditWatchlistModal.vue`

## Solution

Create `useCurrencyConversion` composable.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Null handling | Return `null` | Preserves semantic difference between "no price" and "$0" |
| Rounding | Always 2 decimals | Consistent currency display, matches real-world precision |
| Loading state | Include `loadingRates` | Consistent API, components can ignore if not needed |

## API

```typescript
// frontend/src/composables/useCurrencyConversion.ts

export type Currency = "USD" | "GBP" | "EUR";

export interface ExchangeRates {
  gbp_to_usd_rate: number;
  eur_to_usd_rate: number;
}

export function useCurrencyConversion() {
  const selectedCurrency = ref<Currency>("USD");
  const exchangeRates = ref<ExchangeRates>({
    gbp_to_usd_rate: 1.28,
    eur_to_usd_rate: 1.1
  });
  const loadingRates = ref(false);

  const currencySymbol = computed(() => {
    switch (selectedCurrency.value) {
      case "GBP": return "£";
      case "EUR": return "€";
      default: return "$";
    }
  });

  function convertToUsd(amount: number | null | undefined): number | null {
    if (amount == null) return null;
    let result: number;
    switch (selectedCurrency.value) {
      case "GBP":
        result = amount * exchangeRates.value.gbp_to_usd_rate;
        break;
      case "EUR":
        result = amount * exchangeRates.value.eur_to_usd_rate;
        break;
      default:
        result = amount;
    }
    return Math.round(result * 100) / 100;
  }

  async function loadExchangeRates(): Promise<void> {
    loadingRates.value = true;
    try {
      const res = await api.get("/admin/config");
      exchangeRates.value = res.data;
    } catch (e) {
      console.error("Failed to load exchange rates:", e);
    } finally {
      loadingRates.value = false;
    }
  }

  return {
    selectedCurrency,
    exchangeRates,
    loadingRates,
    currencySymbol,
    convertToUsd,
    loadExchangeRates,
  };
}
```

## Component Usage

```typescript
// Before
type Currency = "USD" | "GBP" | "EUR";
const selectedCurrency = ref<Currency>("USD");
const exchangeRates = ref({ gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 });
const currencySymbol = computed(() => { /* ... */ });
async function loadExchangeRates() { /* ... */ }
const priceInUsd = computed(() => { /* ... */ });

// After
import { useCurrencyConversion } from "@/composables/useCurrencyConversion";

const { selectedCurrency, currencySymbol, convertToUsd, loadExchangeRates } = useCurrencyConversion();
const priceInUsd = computed(() => convertToUsd(form.value.purchase_price));
```

## Test Plan

```typescript
describe("useCurrencyConversion", () => {
  // Core conversion
  it("returns null for null/undefined input");
  it("returns amount unchanged for USD");
  it("converts GBP to USD using exchange rate");
  it("converts EUR to USD using exchange rate");
  it("rounds to 2 decimal places");

  // Symbol
  it("returns $ for USD");
  it("returns £ for GBP");
  it("returns € for EUR");

  // Rate loading
  it("loads rates from /admin/config");
  it("sets loadingRates during fetch");
  it("keeps fallback rates on error");
});
```

## Files to Modify

| File | Action |
|------|--------|
| `composables/useCurrencyConversion.ts` | Create |
| `composables/__tests__/useCurrencyConversion.spec.ts` | Create |
| `components/books/BookForm.vue` | Refactor |
| `components/AcquireModal.vue` | Refactor |
| `components/AddToWatchlistModal.vue` | Refactor |
| `components/EditWatchlistModal.vue` | Refactor |

## Impact

- Removes ~120 lines of duplicated code
- Single source of truth for currency logic
- Easier to add new currencies
- Testable in isolation
