import { ref, computed } from "vue";
import { api } from "@/services/api";

export type Currency = "USD" | "GBP" | "EUR";

export interface ExchangeRates {
  gbp_to_usd_rate: number;
  eur_to_usd_rate: number;
}

// Module-level cache to prevent duplicate API calls across components
const DEFAULT_RATES: ExchangeRates = { gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 };
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

  return {
    selectedCurrency,
    exchangeRates,
    loadingRates,
    currencySymbol,
    convertToUsd,
    loadExchangeRates,
  };
}

// For testing: reset module state
export function _resetCurrencyCache(): void {
  cachedRates = null;
  ratesLoadPromise = null;
  sharedExchangeRates.value = DEFAULT_RATES;
  sharedLoadingRates.value = false;
}
