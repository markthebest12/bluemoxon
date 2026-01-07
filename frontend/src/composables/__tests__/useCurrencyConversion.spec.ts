import { describe, it, expect, beforeEach, vi } from "vitest";
import { nextTick } from "vue";

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "@/services/api";
import { _resetCurrencyCache } from "../useCurrencyConversion";

describe("useCurrencyConversion", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    _resetCurrencyCache(); // Reset module-level cache between tests
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
      exchangeRates.value = { gbp_to_usd_rate: 1.35, eur_to_usd_rate: 1.17 };

      // 100 GBP * 1.35 = 135 USD
      expect(convertToUsd(100)).toBe(135);
    });

    it("converts EUR to USD using exchange rate", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency, exchangeRates, convertToUsd } = useCurrencyConversion();

      selectedCurrency.value = "EUR";
      exchangeRates.value = { gbp_to_usd_rate: 1.35, eur_to_usd_rate: 1.17 };

      // 100 EUR * 1.17 = 117 USD
      expect(convertToUsd(100)).toBe(117);
    });

    it("rounds to 2 decimal places", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency, exchangeRates, convertToUsd } = useCurrencyConversion();

      selectedCurrency.value = "GBP";
      exchangeRates.value = { gbp_to_usd_rate: 1.287, eur_to_usd_rate: 1.17 };

      // 10.55 GBP * 1.287 = 13.57785 -> rounded to 13.58
      expect(convertToUsd(10.55)).toBe(13.58);
    });

    it("rounds USD amounts to 2 decimal places", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency, convertToUsd } = useCurrencyConversion();

      selectedCurrency.value = "USD";

      // Edge case: 10.555 USD -> rounded to 10.56
      expect(convertToUsd(10.555)).toBe(10.56);
      // Edge case: 10.554 USD -> rounded to 10.55
      expect(convertToUsd(10.554)).toBe(10.55);
    });
  });

  describe("loadExchangeRates", () => {
    it("loads rates from /admin/config", async () => {
      const mockRates = { gbp_to_usd_rate: 1.3, eur_to_usd_rate: 1.15 };
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

      resolvePromise!({ data: { gbp_to_usd_rate: 1.35, eur_to_usd_rate: 1.17 } });
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

    it("caches rates and only makes one API call", async () => {
      const mockRates = { gbp_to_usd_rate: 1.3, eur_to_usd_rate: 1.15 };
      vi.mocked(api.get).mockResolvedValue({ data: mockRates });

      const { useCurrencyConversion } = await import("../useCurrencyConversion");

      // Simulate multiple components calling loadExchangeRates
      const instance1 = useCurrencyConversion();
      const instance2 = useCurrencyConversion();
      const instance3 = useCurrencyConversion();

      await instance1.loadExchangeRates();
      await instance2.loadExchangeRates();
      await instance3.loadExchangeRates();

      // Should only make ONE API call despite 3 calls
      expect(api.get).toHaveBeenCalledTimes(1);

      // All instances should have the cached rates
      expect(instance1.exchangeRates.value).toEqual(mockRates);
      expect(instance2.exchangeRates.value).toEqual(mockRates);
      expect(instance3.exchangeRates.value).toEqual(mockRates);
    });

    it("shares exchange rates across instances", async () => {
      const mockRates = { gbp_to_usd_rate: 1.3, eur_to_usd_rate: 1.15 };
      vi.mocked(api.get).mockResolvedValue({ data: mockRates });

      const { useCurrencyConversion } = await import("../useCurrencyConversion");

      const instance1 = useCurrencyConversion();
      const instance2 = useCurrencyConversion();

      // Load rates via instance1
      await instance1.loadExchangeRates();

      // instance2 should see the same rates (shared state)
      expect(instance2.exchangeRates.value).toEqual(mockRates);
    });
  });

  describe("default values", () => {
    it("defaults selectedCurrency to USD", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { selectedCurrency } = useCurrencyConversion();

      expect(selectedCurrency.value).toBe("USD");
    });

    it("has fallback exchange rates matching DEFAULT_RATES", async () => {
      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { exchangeRates } = useCurrencyConversion();

      // These must match DEFAULT_RATES in useCurrencyConversion.ts
      expect(exchangeRates.value.gbp_to_usd_rate).toBe(1.35);
      expect(exchangeRates.value.eur_to_usd_rate).toBe(1.17);
    });
  });
});
