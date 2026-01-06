import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";

// Mock localStorage before importing the composable
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

// Set up mocks before module import
beforeAll(() => {
  Object.defineProperty(window, "localStorage", {
    value: localStorageMock,
    writable: true,
  });
});

// Mock api before importing the composable
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { useDashboardCache, CACHE_KEY, STALE_THRESHOLD } from "../useDashboardCache";
import type { DashboardStats } from "@/types/dashboard";

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

describe("useDashboardCache", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("fetches fresh data when no cache exists", async () => {
    const { api } = await import("@/services/api");
    vi.mocked(api.get).mockResolvedValueOnce({ data: mockDashboardData });

    const { dashboardData, loading, loadDashboard } = useDashboardCache();

    expect(loading.value).toBe(true);
    await loadDashboard();

    expect(api.get).toHaveBeenCalledWith(expect.stringContaining("/stats/dashboard"));
    expect(dashboardData.value).toEqual(mockDashboardData);
    expect(loading.value).toBe(false);
  });

  it("uses cached data when fresh", async () => {
    const cached = {
      data: mockDashboardData,
      timestamp: Date.now(),
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(cached));

    const { api } = await import("@/services/api");
    const { dashboardData, loading, loadDashboard } = useDashboardCache();

    await loadDashboard();

    expect(api.get).not.toHaveBeenCalled();
    expect(dashboardData.value).toEqual(mockDashboardData);
    expect(loading.value).toBe(false);
  });

  it("fetches fresh data in background when cache is stale", async () => {
    vi.useFakeTimers();
    const now = Date.now();
    vi.setSystemTime(now);

    const staleTimestamp = now - STALE_THRESHOLD - 1000; // 1 second past stale
    const cached = {
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

    // Create a deferred promise that we control
    let resolveApi: (value: { data: DashboardStats }) => void;
    const apiPromise = new Promise<{ data: DashboardStats }>((resolve) => {
      resolveApi = resolve;
    });
    vi.mocked(api.get).mockReturnValueOnce(apiPromise);

    const { dashboardData, isStale, loadDashboard } = useDashboardCache();

    await loadDashboard();

    // Should show cached data immediately (before background fetch resolves)
    expect(dashboardData.value?.overview.primary.count).toBe(10);
    expect(isStale.value).toBe(true);

    // Should have started background fetch
    expect(api.get).toHaveBeenCalled();

    // Now resolve the background fetch
    resolveApi!({ data: updatedData });
    await vi.runAllTimersAsync();

    // After background fetch completes, data should be updated
    expect(dashboardData.value?.overview.primary.count).toBe(15);
    expect(isStale.value).toBe(false);
  });

  it("invalidateCache clears localStorage", () => {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ data: mockDashboardData, timestamp: Date.now() }));

    const { invalidateCache } = useDashboardCache();
    invalidateCache();

    expect(localStorage.getItem(CACHE_KEY)).toBeNull();
  });
});
