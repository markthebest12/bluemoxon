import { ref, computed, watch } from "vue";
import { api } from "@/services/api";
import { useToast } from "./useToast";

export type Currency = "USD" | "GBP" | "EUR";

export interface ExchangeRates {
  gbp_to_usd_rate: number;
  eur_to_usd_rate: number;
}

// Module-level cache to prevent duplicate API calls across components
// Fallback rates used only if DB lookup fails (DB is source of truth)
const DEFAULT_RATES: ExchangeRates = { gbp_to_usd_rate: 1.35, eur_to_usd_rate: 1.17 };
let cachedRates: ExchangeRates | null = null;
let ratesLoadPromise: Promise<void> | null = null;

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

async function fetchLiveRate(currency: "GBP" | "EUR"): Promise<number | null> {
  // Check cache first
  const cached = liveRateCache[currency];
  if (cached && Date.now() - cached.fetchedAt < LIVE_RATE_TTL_MS) {
    return cached.rate;
  }

  const maxRetries = 4; // Initial + 3 retries
  const delays = [0, 1000, 2000, 4000]; // Exponential backoff

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    if (attempt > 0) {
      await new Promise((resolve) => setTimeout(resolve, delays[attempt]));
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`https://api.frankfurter.app/latest?from=${currency}&to=USD`, {
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        continue; // Retry on non-OK response
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

  return null; // All retries failed
}

// Shared reactive state across all composable instances
const sharedExchangeRates = ref<ExchangeRates>(DEFAULT_RATES);
const sharedLoadingRates = ref(false);

export function useCurrencyConversion() {
  const selectedCurrency = ref<Currency>("USD");

  // Use shared refs for rates (prevents N components = N API calls)
  const exchangeRates = sharedExchangeRates;
  const loadingRates = sharedLoadingRates;

  const currencySymbol = computed(() => {
    switch (selectedCurrency.value) {
      case "GBP":
        return "£";
      case "EUR":
        return "€";
      default:
        return "$";
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
    // Return cached rates if already loaded
    if (cachedRates) {
      exchangeRates.value = cachedRates;
      return;
    }

    // If a load is already in progress, wait for it
    if (ratesLoadPromise) {
      await ratesLoadPromise;
      return;
    }

    // Start loading
    loadingRates.value = true;
    ratesLoadPromise = (async () => {
      try {
        const res = await api.get("/admin/config");
        cachedRates = res.data;
        exchangeRates.value = res.data;
      } catch (e) {
        console.error("Failed to load exchange rates:", e);
      } finally {
        loadingRates.value = false;
        ratesLoadPromise = null;
      }
    })();

    await ratesLoadPromise;
  }

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
    const currentRate =
      currency === "GBP"
        ? exchangeRates.value.gbp_to_usd_rate
        : exchangeRates.value.eur_to_usd_rate;
    const defaultRate =
      currency === "GBP" ? DEFAULT_RATES.gbp_to_usd_rate : DEFAULT_RATES.eur_to_usd_rate;

    if (currentRate !== defaultRate) {
      // Using DB cache
      showWarning("Using cached exchange rate");
    } else {
      // Using hardcoded fallback
      showWarning("Using estimated exchange rate");
    }
  }

  // Watch for currency changes and fetch live rates
  watch(selectedCurrency, async (newCurrency) => {
    if (newCurrency === "GBP" || newCurrency === "EUR") {
      await updateRateWithFallback(newCurrency);
    }
  });

  return {
    selectedCurrency,
    exchangeRates,
    loadingRates,
    currencySymbol,
    convertToUsd,
    loadExchangeRates,
    fetchLiveRate,
    updateRateWithFallback,
  };
}

// For testing: reset module state
export function _resetCurrencyCache(): void {
  cachedRates = null;
  ratesLoadPromise = null;
  sharedExchangeRates.value = DEFAULT_RATES;
  sharedLoadingRates.value = false;
  liveRateCache.GBP = null;
  liveRateCache.EUR = null;
}

// For testing: inspect live rate cache
export function _getLiveRateCache(): typeof liveRateCache {
  return liveRateCache;
}
