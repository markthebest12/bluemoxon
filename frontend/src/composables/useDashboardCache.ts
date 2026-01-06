import { ref } from "vue";
import { api } from "@/services/api";
import type { DashboardStats, CachedDashboard } from "@/types/dashboard";

export const CACHE_KEY = "bmx_dashboard_cache";
export const STALE_THRESHOLD = 5 * 60 * 1000; // 5 minutes

export function useDashboardCache() {
  const dashboardData = ref<DashboardStats | null>(null);
  const loading = ref(true);
  const isStale = ref(false);
  const error = ref<string | null>(null);

  function getFromCache(): CachedDashboard | null {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) return null;
      return JSON.parse(cached) as CachedDashboard;
    } catch {
      return null;
    }
  }

  function saveToCache(data: DashboardStats): void {
    const cached: CachedDashboard = {
      data,
      timestamp: Date.now(),
    };
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(cached));
    } catch (e) {
      console.warn("Failed to cache dashboard data:", e);
    }
  }

  async function fetchFresh(): Promise<void> {
    try {
      // Get today's date in browser timezone (YYYY-MM-DD format)
      const today = new Date().toLocaleDateString("en-CA");
      const response = await api.get(`/stats/dashboard?reference_date=${today}&days=30`);
      dashboardData.value = response.data;
      isStale.value = false;
      saveToCache(response.data);
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load dashboard";
      console.error("Failed to fetch dashboard:", e);
    } finally {
      loading.value = false;
    }
  }

  async function loadDashboard(): Promise<void> {
    error.value = null;

    // 1. Try cached data first
    const cached = getFromCache();
    if (cached) {
      dashboardData.value = cached.data;
      loading.value = false;

      // Check if cache is still fresh
      const age = Date.now() - cached.timestamp;
      if (age < STALE_THRESHOLD) {
        return; // Cache is fresh, no need to fetch
      }

      // Cache is stale, mark it and fetch in background
      isStale.value = true;
      void fetchFresh(); // Don't await - runs in background
      return;
    }

    // 2. No cache - fetch fresh (loading stays true)
    await fetchFresh();
  }

  function invalidateCache(): void {
    localStorage.removeItem(CACHE_KEY);
  }

  return {
    dashboardData,
    loading,
    isStale,
    error,
    loadDashboard,
    invalidateCache,
  };
}

// Standalone function for invalidation from other components
export function invalidateDashboardCache(): void {
  localStorage.removeItem(CACHE_KEY);
}
