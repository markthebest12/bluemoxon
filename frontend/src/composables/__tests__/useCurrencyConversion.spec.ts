import { describe, it, expect, beforeEach, vi } from "vitest";
import { nextTick } from "vue";

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "@/services/api";

describe("useCurrencyConversion", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("currencySymbol", () => {
    it("returns $ for USD", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency, currencySymbol } = useCurrencyConversion();

      selectedCurrency.value = "USD";
      await nextTick();

      expect(currencySymbol.value).toBe("$");
    });

    it("returns £ for GBP", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency, currencySymbol } = useCurrencyConversion();

      selectedCurrency.value = "GBP";
      await nextTick();

      expect(currencySymbol.value).toBe("£");
    });

    it("returns € for EUR", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency, currencySymbol } = useCurrencyConversion();

      selectedCurrency.value = "EUR";
      await nextTick();

      expect(currencySymbol.value).toBe("€");
    });
  });

  describe("convertToUsd", () => {
    it("returns null for null input", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { convertToUsd } = useCurrencyConversion();

      expect(convertToUsd(null)).toBeNull();
    });

    it("returns null for undefined input", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { convertToUsd } = useCurrencyConversion();

      expect(convertToUsd(undefined)).toBeNull();
    });

    it("returns amount unchanged for USD", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency, convertToUsd } = useCurrencyConversion();

      selectedCurrency.value = "USD";

      expect(convertToUsd(100)).toBe(100);
    });

    it("converts GBP to USD using exchange rate", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency, exchangeRates, convertToUsd } = useCurrencyConversion();

      selectedCurrency.value = "GBP";
      exchangeRates.value = { gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 };

      // 100 GBP * 1.28 = 128 USD
      expect(convertToUsd(100)).toBe(128);
    });

    it("converts EUR to USD using exchange rate", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency, exchangeRates, convertToUsd } = useCurrencyConversion();

      selectedCurrency.value = "EUR";
      exchangeRates.value = { gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 };

      // 100 EUR * 1.1 = 110 USD
      expect(convertToUsd(100)).toBe(110);
    });

    it("rounds to 2 decimal places", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency, exchangeRates, convertToUsd } = useCurrencyConversion();

      selectedCurrency.value = "GBP";
      exchangeRates.value = { gbp_to_usd_rate: 1.287, eur_to_usd_rate: 1.1 };

      // 10.55 GBP * 1.287 = 13.57785 -> rounded to 13.58
      expect(convertToUsd(10.55)).toBe(13.58);
    });
  });

  describe("loadExchangeRates", () => {
    it("loads rates from /admin/config", async () => {
      const mockRates = { gbp_to_usd_rate: 1.30, eur_to_usd_rate: 1.15 };
      vi.mocked(api.get).mockResolvedValueOnce({ data: mockRates });

      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { exchangeRates, loadExchangeRates } = useCurrencyConversion();

      await loadExchangeRates();

      expect(api.get).toHaveBeenCalledWith("/admin/config");
      expect(exchangeRates.value).toEqual(mockRates);
    });

    it("sets loadingRates during fetch", async () => {
      let resolvePromise: (value: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      vi.mocked(api.get).mockReturnValueOnce(pendingPromise as Promise<{ data: unknown }>);

      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { loadingRates, loadExchangeRates } = useCurrencyConversion();

      expect(loadingRates.value).toBe(false);

      const loadPromise = loadExchangeRates();
      expect(loadingRates.value).toBe(true);

      resolvePromise!({ data: { gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 } });
      await loadPromise;

      expect(loadingRates.value).toBe(false);
    });

    it("keeps fallback rates on error", async () => {
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { exchangeRates, loadExchangeRates } = useCurrencyConversion();

      const originalRates = { ...exchangeRates.value };

      await loadExchangeRates();

      expect(exchangeRates.value).toEqual(originalRates);
    });

    it("sets loadingRates to false on error", async () => {
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { loadingRates, loadExchangeRates } = useCurrencyConversion();

      await loadExchangeRates();

      expect(loadingRates.value).toBe(false);
    });
  });

  describe("default values", () => {
    it("defaults selectedCurrency to USD", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency } = useCurrencyConversion();

      expect(selectedCurrency.value).toBe("USD");
    });

    it("has fallback exchange rates", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { exchangeRates } = useCurrencyConversion();

      expect(exchangeRates.value.gbp_to_usd_rate).toBe(1.28);
      expect(exchangeRates.value.eur_to_usd_rate).toBe(1.1);
    });
  });
});
