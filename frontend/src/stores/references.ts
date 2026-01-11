import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";
import { handleApiError } from "@/utils/errorHandler";

export interface Author {
  id: number;
  name: string;
}

export interface Publisher {
  id: number;
  name: string;
  tier: string | null;
  book_count: number;
}

export interface Binder {
  id: number;
  name: string;
  full_name: string | null;
  authentication_markers: string | null;
  book_count: number;
}

// Cache configuration
const CACHE_KEY = "bmx_references_cache";
const CACHE_VERSION = 1;
const STALE_THRESHOLD = 30 * 60 * 1000; // 30 minutes (references change less often than dashboard)
const MAX_CACHE_AGE = 24 * 60 * 60 * 1000; // 24 hours hard TTL

interface CachedReferences {
  version: number;
  timestamp: number;
  authors: Author[];
  publishers: Publisher[];
  binders: Binder[];
}

export const useReferencesStore = defineStore("references", () => {
  const authors = ref<Author[]>([]);
  const publishers = ref<Publisher[]>([]);
  const binders = ref<Binder[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const isStale = ref(false);

  // Request deduplication
  let pendingRequest: Promise<void> | null = null;

  // Computed
  const hasData = computed(
    () => authors.value.length > 0 || publishers.value.length > 0 || binders.value.length > 0
  );

  function getFromCache(): CachedReferences | null {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (!cached) return null;

      const parsed = JSON.parse(cached) as CachedReferences;

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

  function saveToCache(): void {
    const cached: CachedReferences = {
      version: CACHE_VERSION,
      timestamp: Date.now(),
      authors: authors.value,
      publishers: publishers.value,
      binders: binders.value,
    };
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(cached));
    } catch (e) {
      console.warn("Failed to cache reference data:", e);
    }
  }

  async function fetchAuthors() {
    try {
      const response = await api.get("/authors");
      authors.value = response.data;
    } catch (e) {
      handleApiError(e, "Loading authors");
      throw e; // Re-throw so fetchAll knows it failed
    }
  }

  async function fetchPublishers() {
    try {
      const response = await api.get("/publishers");
      publishers.value = response.data;
    } catch (e) {
      handleApiError(e, "Loading publishers");
      throw e;
    }
  }

  async function fetchBinders() {
    try {
      const response = await api.get("/binders");
      binders.value = response.data;
    } catch (e) {
      handleApiError(e, "Loading binders");
      throw e;
    }
  }

  async function fetchFresh(): Promise<void> {
    try {
      await Promise.all([fetchAuthors(), fetchPublishers(), fetchBinders()]);
      isStale.value = false;
      error.value = null;
      saveToCache();
    } catch (_e) {
      error.value = "Failed to load reference data";
      // Don't throw - we may have partial data from cache
    } finally {
      loading.value = false;
    }
  }

  async function fetchAll() {
    // Request deduplication: return existing promise if in flight
    if (pendingRequest) {
      return pendingRequest;
    }

    error.value = null;

    // 1. Try cached data first
    const cached = getFromCache();
    if (cached) {
      authors.value = cached.authors;
      publishers.value = cached.publishers;
      binders.value = cached.binders;
      loading.value = false;

      // Check if cache is still fresh
      const age = Date.now() - cached.timestamp;
      if (age < STALE_THRESHOLD) {
        console.log("[References] Using fresh cache");
        return; // Cache is fresh, no need to fetch
      }

      // Cache is stale, mark it and fetch in background
      console.log("[References] Cache stale, refreshing in background");
      isStale.value = true;
      pendingRequest = fetchFresh().finally(() => {
        pendingRequest = null;
      });

      return;
    }

    // 2. No cache - fetch fresh (loading stays true)
    console.log("[References] No cache, fetching fresh");
    loading.value = true;
    pendingRequest = fetchFresh().finally(() => {
      pendingRequest = null;
    });

    return pendingRequest;
  }

  function invalidateCache(): void {
    localStorage.removeItem(CACHE_KEY);
    authors.value = [];
    publishers.value = [];
    binders.value = [];
    isStale.value = false;
    error.value = null;
  }

  async function createAuthor(name: string, force?: boolean): Promise<Author> {
    const url = force ? "/authors?force=true" : "/authors";
    const response = await api.post(url, { name: name.trim() });
    authors.value.push(response.data);
    saveToCache(); // Update cache with new data
    return response.data;
  }

  async function createPublisher(name: string, force?: boolean): Promise<Publisher> {
    const url = force ? "/publishers?force=true" : "/publishers";
    const response = await api.post(url, { name: name.trim() });
    publishers.value.push(response.data);
    saveToCache();
    return response.data;
  }

  async function createBinder(name: string, force?: boolean): Promise<Binder> {
    const url = force ? "/binders?force=true" : "/binders";
    const response = await api.post(url, { name: name.trim() });
    binders.value.push(response.data);
    saveToCache();
    return response.data;
  }

  return {
    // State
    authors,
    publishers,
    binders,
    loading,
    error,
    isStale,

    // Computed
    hasData,

    // Actions
    fetchAuthors,
    fetchPublishers,
    fetchBinders,
    fetchAll,
    createAuthor,
    createPublisher,
    createBinder,
    invalidateCache,
  };
});

// Standalone function for invalidation from other stores
export function invalidateReferencesCache(): void {
  localStorage.removeItem(CACHE_KEY);
}
