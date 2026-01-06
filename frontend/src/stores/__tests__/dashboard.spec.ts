import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import type { DashboardStats } from "@/types/dashboard";

// Mock localStorage before importing the store
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    clear: () => {
      store = {};
    },
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
  };
})();

beforeAll(() => {
  Object.defineProperty(window, "localStorage", {
    value: localStorageMock,
    writable: true,
  });
});

// Mock api before importing the store
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import {
  useDashboardStore,
  CACHE_KEY,
  CACHE_VERSION,
  STALE_THRESHOLD,
  MAX_CACHE_AGE,
  invalidateDashboardCache,
} from "../dashboard";

const mockDashboardData: DashboardStats = {
  overview: {
    primary: { count: 10, volumes: 20, value_low: 1000, value_mid: 1500, value_high: 2000 },
    extended: { count: 1 },
    flagged: { count: 0 },
    total_items: 11,
    authenticated_bindings: 5,
    in_transit: 2,
    week_delta: { count: 3, volumes: 5, value_mid: 500, authenticated_bindings: 1 },
  },
  bindings: [],
  by_era: [],
  by_publisher: [],
  by_author: [],
  acquisitions_daily: [],
};

describe("dashboard store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("fetches fresh data when no cache exists", async () => {
    const { api } = await import("@/services/api");
    vi.mocked(api.get).mockResolvedValueOnce({ data: mockDashboardData });

    const store = useDashboardStore();

    expect(store.loading).toBe(true);
    await store.loadDashboard();

    expect(api.get).toHaveBeenCalledWith(
      expect.stringContaining("/stats/dashboard"),
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(store.data).toEqual(mockDashboardData);
    expect(store.loading).toBe(false);
  });

  it("uses cached data when fresh", async () => {
    const cached = {
      version: CACHE_VERSION,
      data: mockDashboardData,
      timestamp: Date.now(),
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(cached));

    const { api } = await import("@/services/api");
    const store = useDashboardStore();

    await store.loadDashboard();

    expect(api.get).not.toHaveBeenCalled();
    expect(store.data).toEqual(mockDashboardData);
    expect(store.loading).toBe(false);
  });

  it("fetches fresh data in background when cache is stale", async () => {
    vi.useFakeTimers();
    const now = Date.now();
    vi.setSystemTime(now);

    const staleTimestamp = now - STALE_THRESHOLD - 1000;
    const cached = {
      version: CACHE_VERSION,
      data: mockDashboardData,
      timestamp: staleTimestamp,
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(cached));

    const updatedData: DashboardStats = {
      ...mockDashboardData,
      overview: {
        ...mockDashboardData.overview,
        primary: { ...mockDashboardData.overview.primary, count: 15 },
      },
    };
    const { api } = await import("@/services/api");

    let resolveApi: (value: { data: DashboardStats }) => void;
    const apiPromise = new Promise<{ data: DashboardStats }>((resolve) => {
      resolveApi = resolve;
    });
    vi.mocked(api.get).mockReturnValueOnce(apiPromise);

    const store = useDashboardStore();

    await store.loadDashboard();

    expect(store.data?.overview.primary.count).toBe(10);
    expect(store.isStale).toBe(true);
    expect(api.get).toHaveBeenCalled();

    resolveApi!({ data: updatedData });
    await vi.runAllTimersAsync();

    expect(store.data?.overview.primary.count).toBe(15);
    expect(store.isStale).toBe(false);
  });

  it("invalidateCache clears localStorage and in-memory state", () => {
    localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ version: CACHE_VERSION, data: mockDashboardData, timestamp: Date.now() })
    );

    const store = useDashboardStore();
    store.data = mockDashboardData;
    store.invalidateCache();

    expect(localStorage.getItem(CACHE_KEY)).toBeNull();
    expect(store.data).toBeNull();
    expect(store.loading).toBe(true);
  });

  it("standalone invalidateDashboardCache clears localStorage", () => {
    localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ version: CACHE_VERSION, data: mockDashboardData, timestamp: Date.now() })
    );

    invalidateDashboardCache();

    expect(localStorage.getItem(CACHE_KEY)).toBeNull();
  });

  describe("cache version", () => {
    it("invalidates cache with wrong version", async () => {
      const cached = {
        version: 999, // Wrong version
        data: mockDashboardData,
        timestamp: Date.now(),
      };
      localStorage.setItem(CACHE_KEY, JSON.stringify(cached));

      const { api } = await import("@/services/api");
      vi.mocked(api.get).mockResolvedValueOnce({ data: mockDashboardData });

      const store = useDashboardStore();
      await store.loadDashboard();

      // Should have fetched because version was wrong
      expect(api.get).toHaveBeenCalled();
    });

    it("invalidates cache without version field", async () => {
      const cached = {
        data: mockDashboardData,
        timestamp: Date.now(),
        // Missing version field
      };
      localStorage.setItem(CACHE_KEY, JSON.stringify(cached));

      const { api } = await import("@/services/api");
      vi.mocked(api.get).mockResolvedValueOnce({ data: mockDashboardData });

      const store = useDashboardStore();
      await store.loadDashboard();

      // Should have fetched because version was missing
      expect(api.get).toHaveBeenCalled();
    });
  });

  describe("max cache age", () => {
    it("invalidates cache older than MAX_CACHE_AGE", async () => {
      vi.useFakeTimers();
      const now = Date.now();
      vi.setSystemTime(now);

      const oldTimestamp = now - MAX_CACHE_AGE - 1000; // 1 second past max age
      const cached = {
        version: CACHE_VERSION,
        data: mockDashboardData,
        timestamp: oldTimestamp,
      };
      localStorage.setItem(CACHE_KEY, JSON.stringify(cached));

      const { api } = await import("@/services/api");
      vi.mocked(api.get).mockResolvedValueOnce({ data: mockDashboardData });

      const store = useDashboardStore();
      await store.loadDashboard();

      // Should have fetched because cache is too old
      expect(api.get).toHaveBeenCalled();
    });
  });

  describe("request deduplication", () => {
    it("deduplicates concurrent requests", async () => {
      const { api } = await import("@/services/api");

      let resolveApi: (value: { data: DashboardStats }) => void;
      const apiPromise = new Promise<{ data: DashboardStats }>((resolve) => {
        resolveApi = resolve;
      });
      vi.mocked(api.get).mockReturnValue(apiPromise);

      const store = useDashboardStore();

      // Fire multiple concurrent requests
      const promise1 = store.loadDashboard();
      const promise2 = store.loadDashboard();
      const promise3 = store.loadDashboard();

      // Resolve the API call
      resolveApi!({ data: mockDashboardData });

      await Promise.all([promise1, promise2, promise3]);

      // Should have only made one API call
      expect(api.get).toHaveBeenCalledTimes(1);
    });
  });

  describe("cleanup", () => {
    it("cleanup aborts in-flight request", async () => {
      const { api } = await import("@/services/api");

      let capturedSignal: AbortSignal | undefined;
      vi.mocked(api.get).mockImplementation((_url, options) => {
        capturedSignal = options?.signal as AbortSignal | undefined;
        return new Promise(() => {}); // Never resolves
      });

      const store = useDashboardStore();

      // Start a request
      store.loadDashboard();

      // Verify signal was captured
      expect(capturedSignal).toBeDefined();
      expect(capturedSignal?.aborted).toBe(false);

      // Cleanup should abort
      store.cleanup();

      expect(capturedSignal?.aborted).toBe(true);
    });
  });

  describe("error handling", () => {
    it("sets error on fetch failure", async () => {
      const { api } = await import("@/services/api");
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

      const store = useDashboardStore();
      await store.loadDashboard();

      expect(store.error).toBe("Network error");
      expect(store.loading).toBe(false);
    });

    it("clears error on successful fetch", async () => {
      const { api } = await import("@/services/api");
      vi.mocked(api.get)
        .mockRejectedValueOnce(new Error("Network error"))
        .mockResolvedValueOnce({ data: mockDashboardData });

      const store = useDashboardStore();

      // First call fails
      await store.loadDashboard();
      expect(store.error).toBe("Network error");

      // Reset the pending request state so we can load again
      store.invalidateCache();

      // Second call succeeds
      await store.loadDashboard();
      expect(store.error).toBeNull();
    });
  });
});
