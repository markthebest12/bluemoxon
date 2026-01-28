/**
 * useNetworkData - Fetches and caches social circles network data.
 *
 * ## Cache Behavior
 *
 * This composable uses **instance-scoped caching**:
 * - Each component instance gets its own cache
 * - Navigating away destroys the cache
 * - Returning to the page triggers a fresh fetch
 *
 * This is intentional for several reasons:
 * 1. **Prevents stale data** - Network data can change frequently as books
 *    are added/removed, so fresh fetches ensure accuracy
 * 2. **Avoids complex invalidation** - No need to track user/auth changes
 *    or coordinate cache invalidation across components
 * 3. **Memory management** - Cache is automatically cleaned up when component
 *    unmounts, preventing memory leaks in long-running sessions
 * 4. **Simplicity** - The 5-minute TTL is sufficient for within-session use;
 *    cross-navigation caching adds complexity without significant benefit
 *    given typical user navigation patterns
 *
 * If cross-navigation caching is needed in the future, consider:
 * - Pinia store for reactive state management with devtools support
 * - Module-level cache with auth-aware invalidation hooks
 * - Service worker caching for offline support
 *
 * @example
 * ```ts
 * const { data, loadingState, error, fetchData, clearCache } = useNetworkData();
 *
 * onMounted(() => {
 *   fetchData(); // Uses cache if valid, otherwise fetches
 * });
 *
 * // Force refresh after data mutation
 * await saveChanges();
 * fetchData({ forceRefresh: true });
 * ```
 */

import { ref, readonly } from "vue";
import type { SocialCirclesResponse, LoadingState, AppError } from "@/types/socialCircles";
import { API } from "@/constants/socialCircles";
import { api } from "@/services/api";

export function useNetworkData() {
  // Instance-scoped cache (prevents cross-session data leakage)
  let cachedData: SocialCirclesResponse | null = null;
  let cacheTimestamp = 0;

  const data = ref<SocialCirclesResponse | null>(null);
  const loadingState = ref<LoadingState>("idle");
  const error = ref<AppError | null>(null);

  async function fetchData(
    options: {
      includeBinders?: boolean;
      minBookCount?: number;
      forceRefresh?: boolean;
    } = {}
  ) {
    const { includeBinders = true, minBookCount = 1, forceRefresh = false } = options;

    // Check cache
    const now = Date.now();
    if (!forceRefresh && cachedData && now - cacheTimestamp < API.cacheTtlMs) {
      data.value = cachedData;
      loadingState.value = "success";
      return;
    }

    loadingState.value = "loading";
    error.value = null;

    try {
      const response = await api.get<SocialCirclesResponse>(API.endpoint, {
        params: {
          include_binders: includeBinders,
          min_book_count: minBookCount,
        },
      });

      const json = response.data;

      // Update cache
      cachedData = json;
      cacheTimestamp = now;

      data.value = json;
      loadingState.value = "success";
    } catch (e) {
      const message = e instanceof Error ? e.message : "Unknown error";
      error.value = {
        type: "network",
        message,
        retryable: true,
      };
      loadingState.value = "error";
    }
  }

  function clearCache() {
    cachedData = null;
    cacheTimestamp = 0;
  }

  return {
    data: readonly(data),
    loadingState: readonly(loadingState),
    error: readonly(error),
    fetchData,
    clearCache,
  };
}
