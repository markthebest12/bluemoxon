import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";
import type { DashboardStats, CachedDashboard } from "@/types/dashboard";

export const CACHE_KEY = "bmx_dashboard_cache";
export const CACHE_VERSION = 2; // v2: Added days field to cache
export const STALE_THRESHOLD = 5 * 60 * 1000; // 5 minutes
export const MAX_CACHE_AGE = 24 * 60 * 60 * 1000; // 24 hours hard TTL

export const useDashboardStore = defineStore("dashboard", () => {
  // Shared state (singleton via Pinia)
  const data = ref<DashboardStats | null>(null);
  const loading = ref(true);
  const isStale = ref(false);
  const error = ref<string | null>(null);
  // Default to 90 days (3 months) for better trend visibility
  // Changed from 30 days in PR #1099 to show more acquisition history
  const selectedDays = ref(90);

  // Request deduplication
  let pendingRequest: Promise<void> | null = null;
  let abortController: AbortController | null = null;

  // Computed
  const hasData = computed(() => data.value !== null);
  const hasError = computed(() => error.value !== null);

  function getFromCache(): CachedDashboard | null {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) return null;

      const parsed = JSON.parse(cached) as CachedDashboard;

      // Schema version check
      if (parsed.version !== CACHE_VERSION) {
        localStorage.removeItem(CACHE_KEY);
        return null;
      }

      // Max age check (24hr hard TTL)
      const age = Date.now() - parsed.timestamp;
      if (age > MAX_CACHE_AGE) {
        localStorage.removeItem(CACHE_KEY);
        return null;
      }

      return parsed;
    } catch {
      localStorage.removeItem(CACHE_KEY);
      return null;
    }
  }

  function saveToCache(stats: DashboardStats): void {
    const cached: CachedDashboard = {
      version: CACHE_VERSION,
      data: stats,
      timestamp: Date.now(),
      days: selectedDays.value,
    };
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(cached));
    } catch (e) {
      console.warn("Failed to cache dashboard data:", e);
    }
  }

  async function fetchFresh(signal?: AbortSignal): Promise<void> {
    try {
      // Get today's date in browser timezone (YYYY-MM-DD format)
      const today = new Date().toLocaleDateString("en-CA");
      const response = await api.get(
        `/stats/dashboard?reference_date=${today}&days=${selectedDays.value}`,
        {
          signal,
        }
      );

      // Check if request was aborted
      if (signal?.aborted) return;

      data.value = response.data;
      isStale.value = false;
      error.value = null;
      saveToCache(response.data);
    } catch (e) {
      // Don't set error if request was aborted
      if (e instanceof Error && e.name === "CanceledError") return;
      if (signal?.aborted) return;

      error.value = e instanceof Error ? e.message : "Failed to load dashboard";
      console.error("Failed to fetch dashboard:", e);
    } finally {
      if (!signal?.aborted) {
        loading.value = false;
      }
    }
  }

  async function loadDashboard(): Promise<void> {
    // Request deduplication: return existing promise if in flight
    if (pendingRequest) {
      return pendingRequest;
    }

    error.value = null;

    // 1. Try cached data first
    const cached = getFromCache();
    if (cached && cached.days === selectedDays.value) {
      data.value = cached.data;
      loading.value = false;

      // Check if cache is still fresh
      const age = Date.now() - cached.timestamp;
      if (age < STALE_THRESHOLD) {
        return; // Cache is fresh, no need to fetch
      }

      // Cache is stale, mark it and fetch in background
      isStale.value = true;

      // Create abort controller for cleanup
      abortController = new AbortController();
      pendingRequest = fetchFresh(abortController.signal).finally(() => {
        pendingRequest = null;
        abortController = null;
      });

      return;
    }

    // 2. No cache - fetch fresh (loading stays true)
    abortController = new AbortController();
    pendingRequest = fetchFresh(abortController.signal).finally(() => {
      pendingRequest = null;
      abortController = null;
    });

    return pendingRequest;
  }

  function invalidateCache(): void {
    localStorage.removeItem(CACHE_KEY);
    // Also clear in-memory state
    data.value = null;
    isStale.value = false;
    error.value = null;
    loading.value = true;
  }

  function cleanup(): void {
    // Cancel any in-flight request
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    pendingRequest = null;
  }

  async function setDays(days: number): Promise<void> {
    cleanup(); // Abort any in-flight request first
    selectedDays.value = days;
    // Clear localStorage but keep showing current data (stale-while-revalidate)
    localStorage.removeItem(CACHE_KEY);
    isStale.value = true;
    loading.value = true;
    error.value = null;
    // Fetch fresh data - loadDashboard will see no cache and fetch
    await loadDashboard();
  }

  return {
    // State
    data,
    loading,
    isStale,
    error,
    selectedDays,

    // Computed
    hasData,
    hasError,

    // Actions
    loadDashboard,
    invalidateCache,
    cleanup,
    setDays,
  };
});

// Standalone function for invalidation from other stores (like auth)
export function invalidateDashboardCache(): void {
  localStorage.removeItem(CACHE_KEY);
}
