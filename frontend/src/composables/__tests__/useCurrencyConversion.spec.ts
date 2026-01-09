import { describe, it, expect, beforeEach, vi } from "vitest";
import { nextTick } from "vue";

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "@/services/api";
import { _resetCurrencyCache, _getLiveRateCache } from "../useCurrencyConversion";

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

  describe("live rate cache", () => {
    it("exposes liveRateCache with null initial values", async () => {
      const { useCurrencyConversion, _getLiveRateCache } = await import("../useCurrencyConversion");
      useCurrencyConversion();
      const cache = _getLiveRateCache();
      expect(cache.GBP).toBeNull();
      expect(cache.EUR).toBeNull();
    });

    it("fetchLiveRate returns rate from frankfurter API", async () => {
      const mockResponse = {
        amount: 1,
        base: "GBP",
        date: "2026-01-08",
        rates: { USD: 1.25 },
      };

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockResponse),
        })
      );

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

    it("returns cached rate without fetching if within TTL", async () => {
      const mockFetch = vi.fn();
      vi.stubGlobal("fetch", mockFetch);

      const { useCurrencyConversion, _getLiveRateCache } = await import("../useCurrencyConversion");
      const { fetchLiveRate } = useCurrencyConversion();

      // Manually set cache
      const cache = _getLiveRateCache();
      cache.GBP = { rate: 1.3, fetchedAt: Date.now() };

      const rate = await fetchLiveRate("GBP");

      expect(rate).toBe(1.3);
      expect(mockFetch).not.toHaveBeenCalled();

      vi.unstubAllGlobals();
    });

    it("retries up to 3 times on failure before succeeding", async () => {
      const mockResponse = {
        amount: 1,
        base: "GBP",
        date: "2026-01-08",
        rates: { USD: 1.25 },
      };

      const mockFetch = vi
        .fn()
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

    it("returns null after all retries fail", { timeout: 15000 }, async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error("Network error"));
      vi.stubGlobal("fetch", mockFetch);

      const { useCurrencyConversion } = await import("../useCurrencyConversion");
      const { fetchLiveRate } = useCurrencyConversion();

      const rate = await fetchLiveRate("EUR");

      expect(rate).toBeNull();
      expect(mockFetch).toHaveBeenCalledTimes(3); // Initial + 2 retries

      vi.unstubAllGlobals();
    });

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
      cache.GBP = { rate: 1.3, fetchedAt: Date.now() - 16 * 60 * 1000 };

      const rate = await fetchLiveRate("GBP");

      expect(rate).toBe(1.28); // New rate from API
      expect(mockFetch).toHaveBeenCalledTimes(1);

      vi.unstubAllGlobals();
    });

    it("falls back to DB cache and shows warning toast when live fetch fails", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));

      const mockShowWarning = vi.fn();
      const toastModule = await import("../useToast");
      vi.spyOn(toastModule, "useToast").mockReturnValue({
        showWarning: mockShowWarning,
        showError: vi.fn(),
        showSuccess: vi.fn(),
        dismiss: vi.fn(),
        pauseTimer: vi.fn(),
        resumeTimer: vi.fn(),
        toasts: { value: [] } as never,
      });

      const { useCurrencyConversion, _resetCurrencyCache, _setRatesLoadedFromDb } =
        await import("../useCurrencyConversion");
      _resetCurrencyCache();
      const { exchangeRates, updateRateWithFallback } = useCurrencyConversion();

      // Simulate DB-cached rates
      exchangeRates.value = { gbp_to_usd_rate: 1.32, eur_to_usd_rate: 1.18 };
      _setRatesLoadedFromDb(true);

      await updateRateWithFallback("GBP");

      expect(exchangeRates.value.gbp_to_usd_rate).toBe(1.32); // Uses DB cache
      expect(mockShowWarning).toHaveBeenCalledWith("Using cached exchange rate");

      vi.unstubAllGlobals();
      vi.restoreAllMocks();
    }, 15000);

    it("shows 'estimated' warning when falling back to hardcoded rates", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));

      const mockShowWarning = vi.fn();
      const toastModule = await import("../useToast");
      vi.spyOn(toastModule, "useToast").mockReturnValue({
        showWarning: mockShowWarning,
        showError: vi.fn(),
        showSuccess: vi.fn(),
        dismiss: vi.fn(),
        pauseTimer: vi.fn(),
        resumeTimer: vi.fn(),
        toasts: { value: [] } as never,
      });

      const { useCurrencyConversion, _resetCurrencyCache } =
        await import("../useCurrencyConversion");
      _resetCurrencyCache(); // Reset to default rates
      const { updateRateWithFallback } = useCurrencyConversion();

      await updateRateWithFallback("EUR");

      expect(mockShowWarning).toHaveBeenCalledWith("Using estimated exchange rate");

      vi.unstubAllGlobals();
      vi.restoreAllMocks();
    }, 15000);
  });

  describe("currency change watcher", () => {
    it("fetches live rate when currency changes to GBP", async () => {
      const mockResponse = {
        amount: 1,
        base: "GBP",
        date: "2026-01-08",
        rates: { USD: 1.27 },
      };

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockResponse),
        })
      );

      const { useCurrencyConversion, _resetCurrencyCache } =
        await import("../useCurrencyConversion");
      _resetCurrencyCache();
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

      const { useCurrencyConversion, _resetCurrencyCache } =
        await import("../useCurrencyConversion");
      _resetCurrencyCache();
      const { selectedCurrency } = useCurrencyConversion();

      selectedCurrency.value = "USD";
      await nextTick();
      await new Promise((r) => setTimeout(r, 100));

      expect(mockFetch).not.toHaveBeenCalled();

      vi.unstubAllGlobals();
    });
  });
});
