/**
 * useNetworkData - Fetches and caches social circles data.
 *
 * Cache is instance-scoped to prevent data leakage across SPA navigation
 * and user sessions. Each composable instance maintains its own cache.
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
