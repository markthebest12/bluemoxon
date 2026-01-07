import { ref, computed } from "vue";
import { api } from "@/services/api";

export type Currency = "USD" | "GBP" | "EUR";

export interface ExchangeRates {
  gbp_to_usd_rate: number;
  eur_to_usd_rate: number;
}

// Module-level cache to prevent duplicate API calls across components
// Updated Jan 2026 - run scripts/update-exchange-rates.sh to update DB rates
const DEFAULT_RATES: ExchangeRates = { gbp_to_usd_rate: 1.35, eur_to_usd_rate: 1.17 };
let cachedRates: ExchangeRates | null = null;
let ratesLoadPromise: Promise<void> | null = null;

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

  /**
   * Fetch live exchange rate for a specific currency from frankfurter.app.
   * Falls back to backend rates if external API fails, then to defaults.
   */
  async function fetchLiveRate(currency: Currency): Promise<void> {
    // No conversion needed for USD
    if (currency === "USD") {
      return;
    }

    loadingRates.value = true;

    try {
      // Try frankfurter.app first (free, no auth)
      const response = await fetch(`https://api.frankfurter.app/latest?from=USD&to=${currency}`);

      if (response.ok) {
        const data = await response.json();
        const usdToCurrencyRate = data.rates[currency];

        if (usdToCurrencyRate) {
          // Invert rate: currency->USD = 1 / USD->currency
          const currencyToUsd = Math.round((1 / usdToCurrencyRate) * 10000) / 10000;

          // Update the specific rate
          if (currency === "GBP") {
            exchangeRates.value = {
              ...exchangeRates.value,
              gbp_to_usd_rate: currencyToUsd,
            };
          } else if (currency === "EUR") {
            exchangeRates.value = {
              ...exchangeRates.value,
              eur_to_usd_rate: currencyToUsd,
            };
          }

          loadingRates.value = false;
          return;
        }
      }

      throw new Error("Invalid response from frankfurter.app");
    } catch (e) {
      console.warn("Failed to fetch live rate, falling back to backend:", e);

      // Fallback to backend rates
      try {
        const res = await api.get("/admin/config");
        exchangeRates.value = res.data;
        cachedRates = res.data;
      } catch (backendError) {
        console.error("Backend fallback also failed, using defaults:", backendError);
        // Keep current rates (defaults or previously loaded)
      }
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
    fetchLiveRate,
  };
}

// For testing: reset module state
export function _resetCurrencyCache(): void {
  cachedRates = null;
  ratesLoadPromise = null;
  sharedExchangeRates.value = DEFAULT_RATES;
  sharedLoadingRates.value = false;
}
