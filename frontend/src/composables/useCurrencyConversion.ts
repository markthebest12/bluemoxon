import { ref, computed, watch, onUnmounted, getCurrentInstance } from "vue";
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

// Fix 6: Track if rates came from DB (not float comparison)
let ratesLoadedFromDb = false;

// Fix 7: Circuit breaker - skip live fetch after repeated failures
const CIRCUIT_BREAKER_THRESHOLD = 3;
const CIRCUIT_BREAKER_RESET_MS = 60 * 1000; // 1 minute
let consecutiveFailures = 0;
let circuitBreakerTrippedAt: number | null = null;

// Fix 2: Watcher setup guard - only one watcher globally
let watcherSetup = false;
let watcherStopHandle: (() => void) | null = null;

// Fix 1 & 3: Shared abort controller for current request
let currentAbortController: AbortController | null = null;
let currentRequestId = 0;

function isCircuitBreakerOpen(): boolean {
  if (circuitBreakerTrippedAt === null) return false;
  if (Date.now() - circuitBreakerTrippedAt > CIRCUIT_BREAKER_RESET_MS) {
    // Reset circuit breaker after cooldown
    circuitBreakerTrippedAt = null;
    consecutiveFailures = 0;
    return false;
  }
  return true;
}

async function fetchLiveRate(
  currency: "GBP" | "EUR",
  signal?: AbortSignal
): Promise<number | null> {
  // Check cache first
  const cached = liveRateCache[currency];
  if (cached && Date.now() - cached.fetchedAt < LIVE_RATE_TTL_MS) {
    return cached.rate;
  }

  // Fix 7: Check circuit breaker
  if (isCircuitBreakerOpen()) {
    console.warn("[ExchangeRate] Circuit breaker open, skipping live fetch");
    return null;
  }

  // Fix 4: Faster retries - 2 retries max, shorter delays
  const maxRetries = 3; // Initial + 2 retries
  const delays = [0, 200, 500]; // Much faster: 0.7s total max wait

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    // Check if aborted before retry delay
    if (signal?.aborted) {
      return null;
    }

    if (attempt > 0) {
      await new Promise((resolve) => setTimeout(resolve, delays[attempt]));
    }

    // Check again after delay
    if (signal?.aborted) {
      return null;
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // 3s timeout

      // Abort if parent signal aborts
      const abortHandler = () => controller.abort();
      signal?.addEventListener("abort", abortHandler);

      const response = await fetch(`https://api.frankfurter.app/latest?from=${currency}&to=USD`, {
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      signal?.removeEventListener("abort", abortHandler);

      if (!response.ok) {
        console.warn(`[ExchangeRate] API returned ${response.status}`);
        continue; // Retry on non-OK response
      }

      const data = await response.json();
      const rate = data.rates?.USD;

      if (typeof rate === "number" && rate > 0 && isFinite(rate)) {
        // Success - reset circuit breaker
        consecutiveFailures = 0;
        circuitBreakerTrippedAt = null;
        // Update cache
        liveRateCache[currency] = { rate, fetchedAt: Date.now() };
        return rate;
      }

      console.warn("[ExchangeRate] Invalid rate in response:", data);
    } catch (error) {
      if (signal?.aborted) {
        return null; // Intentional abort, not a failure
      }
      const message = error instanceof Error ? error.message : "Unknown error";
      console.warn(`[ExchangeRate] Fetch attempt ${attempt + 1} failed: ${message}`);
    }
  }

  // All retries failed - update circuit breaker
  consecutiveFailures++;
  if (consecutiveFailures >= CIRCUIT_BREAKER_THRESHOLD) {
    circuitBreakerTrippedAt = Date.now();
    console.warn("[ExchangeRate] Circuit breaker tripped after repeated failures");
  }

  return null;
}

// Shared reactive state across all composable instances
const sharedExchangeRates = ref<ExchangeRates>(DEFAULT_RATES);
const sharedLoadingRates = ref(false);
// Fix 5: Loading state for live rate fetch
const sharedLoadingLiveRate = ref(false);
// Fix 2: Shared selected currency (prevents multiple watchers on different refs)
const sharedSelectedCurrency = ref<Currency>("USD");

// Fix 1: Abort current request and start new one
async function updateRateWithFallback(currency: "GBP" | "EUR"): Promise<void> {
  const { showWarning } = useToast();

  // Fix 1: Abort any in-flight request
  if (currentAbortController) {
    currentAbortController.abort();
  }
  currentAbortController = new AbortController();
  const myRequestId = ++currentRequestId;

  // Fix 5: Set loading state
  sharedLoadingLiveRate.value = true;

  try {
    // Try live rate first
    const liveRate = await fetchLiveRate(currency, currentAbortController.signal);

    // Fix 1: Check if this request is still current
    if (myRequestId !== currentRequestId) {
      return; // Stale request, discard result
    }

    if (liveRate !== null) {
      // Success - update exchange rates
      if (currency === "GBP") {
        sharedExchangeRates.value = { ...sharedExchangeRates.value, gbp_to_usd_rate: liveRate };
      } else {
        sharedExchangeRates.value = { ...sharedExchangeRates.value, eur_to_usd_rate: liveRate };
      }
      return;
    }

    // Live failed - check if we have DB-cached rates
    // Fix 6: Use boolean flag instead of float comparison
    if (ratesLoadedFromDb) {
      showWarning("Using cached exchange rate");
    } else {
      showWarning("Using estimated exchange rate");
    }
  } finally {
    // Fix 5: Clear loading state (only if still current request)
    if (myRequestId === currentRequestId) {
      sharedLoadingLiveRate.value = false;
    }
  }
}

// Fix 2: Setup watcher once globally (not per composable instance)
function setupCurrencyWatcher(): void {
  if (watcherSetup) return;
  watcherSetup = true;

  watcherStopHandle = watch(
    sharedSelectedCurrency,
    async (newCurrency) => {
      if (newCurrency === "GBP" || newCurrency === "EUR") {
        await updateRateWithFallback(newCurrency);
      }
    },
    { immediate: true } // Fix 11: Trigger on initial value if GBP/EUR
  );
}

export function useCurrencyConversion() {
  // Fix 2: Use shared selected currency
  const selectedCurrency = sharedSelectedCurrency;

  // Use shared refs for rates (prevents N components = N API calls)
  const exchangeRates = sharedExchangeRates;
  const loadingRates = sharedLoadingRates;
  const loadingLiveRate = sharedLoadingLiveRate;

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
        // Fix 6: Track that rates came from DB
        ratesLoadedFromDb = true;
      } catch (e) {
        console.error("Failed to load exchange rates:", e);
      } finally {
        loadingRates.value = false;
        ratesLoadPromise = null;
      }
    })();

    await ratesLoadPromise;
  }

  // Fix 2: Setup watcher (idempotent - only runs once)
  setupCurrencyWatcher();

  // Fix 3: Abort in-flight request on unmount (only in component context)
  if (getCurrentInstance()) {
    onUnmounted(() => {
      if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
      }
    });
  }

  return {
    selectedCurrency,
    exchangeRates,
    loadingRates,
    loadingLiveRate,
    currencySymbol,
    convertToUsd,
    loadExchangeRates,
    fetchLiveRate: (currency: "GBP" | "EUR") => fetchLiveRate(currency),
    updateRateWithFallback,
  };
}

// For testing: reset module state
export function _resetCurrencyCache(): void {
  cachedRates = null;
  ratesLoadPromise = null;
  sharedExchangeRates.value = DEFAULT_RATES;
  sharedLoadingRates.value = false;
  sharedLoadingLiveRate.value = false;
  sharedSelectedCurrency.value = "USD";
  liveRateCache.GBP = null;
  liveRateCache.EUR = null;
  ratesLoadedFromDb = false;
  consecutiveFailures = 0;
  circuitBreakerTrippedAt = null;
  // Stop existing watcher before resetting
  if (watcherStopHandle) {
    watcherStopHandle();
    watcherStopHandle = null;
  }
  watcherSetup = false;
  if (currentAbortController) {
    currentAbortController.abort();
  }
  currentAbortController = null;
  currentRequestId = 0;
}

// For testing: inspect live rate cache
export function _getLiveRateCache(): typeof liveRateCache {
  return liveRateCache;
}

// For testing: set ratesLoadedFromDb flag
export function _setRatesLoadedFromDb(loaded: boolean): void {
  ratesLoadedFromDb = loaded;
}
