/**
 * useNetworkData - Fetches and caches social circles data.
 */

import { ref, readonly } from 'vue';
import type { SocialCirclesResponse, LoadingState, AppError } from '@/types/socialCircles';
import { API } from '@/constants/socialCircles';

// Module-level cache
let cachedData: SocialCirclesResponse | null = null;
let cacheTimestamp = 0;

export function useNetworkData() {
  const data = ref<SocialCirclesResponse | null>(null);
  const loadingState = ref<LoadingState>('idle');
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
      loadingState.value = 'success';
      return;
    }

    loadingState.value = 'loading';
    error.value = null;

    try {
      const params = new URLSearchParams({
        include_binders: String(includeBinders),
        min_book_count: String(minBookCount),
      });

      const response = await fetch(`${API.endpoint}?${params}`, {
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const json = await response.json();

      // Update cache
      cachedData = json;
      cacheTimestamp = now;

      data.value = json;
      loadingState.value = 'success';
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      error.value = {
        type: 'network',
        message,
        retryable: true,
      };
      loadingState.value = 'error';
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
