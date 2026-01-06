import { ref, computed } from "vue";
import { api } from "@/services/api";

export type Currency = "USD" | "GBP" | "EUR";

export interface ExchangeRates {
  gbp_to_usd_rate: number;
  eur_to_usd_rate: number;
}

export function useCurrencyConversion() {
  const selectedCurrency = ref<Currency>("USD");
  const exchangeRates = ref<ExchangeRates>({
    gbp_to_usd_rate: 1.28,
    eur_to_usd_rate: 1.1,
  });
  const loadingRates = ref(false);

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
