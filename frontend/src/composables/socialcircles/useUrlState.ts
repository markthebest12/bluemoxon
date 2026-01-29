/**
 * useUrlState - Syncs filter/selection state to URL for shareable links.
 */

import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import type { FilterState, NodeId, Era, ConnectionType } from "@/types/socialCircles";
import { ALL_CONNECTION_TYPES, ANIMATION } from "@/constants/socialCircles";

export function useUrlState() {
  const router = useRouter();
  const route = useRoute();

  const isInitialized = ref(false);
  let updateTimeout: ReturnType<typeof setTimeout> | null = null;

  // Parse URL params to filter state
  function parseUrlToFilters(): Partial<FilterState> {
    const query = route.query;
    const filters: Partial<FilterState> = {};

    if (query.authors === "false") filters.showAuthors = false;
    if (query.publishers === "false") filters.showPublishers = false;
    if (query.binders === "false") filters.showBinders = false;
    if (query.tier1 === "true") filters.tier1Only = true;
    if (query.search) filters.searchQuery = String(query.search);

    if (query.connections) {
      const types = String(query.connections).split(",") as ConnectionType[];
      filters.connectionTypes = types.filter((t) =>
        (ALL_CONNECTION_TYPES as readonly string[]).includes(t)
      );
    }

    if (query.eras) {
      const eras = String(query.eras).split(",") as Era[];
      filters.eras = eras.filter((e) =>
        ["pre_romantic", "romantic", "victorian", "edwardian", "post_1910"].includes(e)
      );
    }

    return filters;
  }

  // Parse selected node from URL
  function parseSelectedNode(): NodeId | null {
    const selected = route.query.selected;
    if (selected && typeof selected === "string") {
      return selected as NodeId;
    }
    return null;
  }

  // Parse timeline year from URL
  function parseTimelineYear(): number | null {
    const year = route.query.year;
    if (year) {
      const parsed = parseInt(String(year), 10);
      if (!isNaN(parsed)) return parsed;
    }
    return null;
  }

  // Update URL from state (debounced)
  // Skips URL updates during playback to avoid history spam
  // Uses history.replaceState() instead of router.replace() to avoid triggering
  // router's afterEach scroll behavior (#1406)
  function updateUrl(params: {
    filters?: FilterState;
    selectedNode?: NodeId | null;
    year?: number;
    isPlaying?: boolean;
  }) {
    // Skip URL updates during timeline playback to avoid history spam
    // Clear any pending update to prevent it firing during playback
    if (params.isPlaying) {
      if (updateTimeout) clearTimeout(updateTimeout);
      return;
    }

    if (updateTimeout) clearTimeout(updateTimeout);

    updateTimeout = setTimeout(() => {
      const query: Record<string, string> = {};

      if (params.filters) {
        const f = params.filters;
        if (!f.showAuthors) query.authors = "false";
        if (!f.showPublishers) query.publishers = "false";
        if (!f.showBinders) query.binders = "false";
        if (f.tier1Only) query.tier1 = "true";
        if (f.searchQuery) query.search = f.searchQuery;
        if (f.connectionTypes.length < ALL_CONNECTION_TYPES.length) {
          query.connections = f.connectionTypes.join(",");
        }
        if (f.eras.length > 0) {
          query.eras = f.eras.join(",");
        }
      }

      if (params.selectedNode) {
        query.selected = params.selectedNode;
      }

      if (params.year != null) {
        query.year = String(params.year);
      }

      // Build URL with query params, using current path
      const searchParams = new URLSearchParams(query);
      const newUrl = `${window.location.pathname}${searchParams.toString() ? "?" + searchParams.toString() : ""}`;

      // Use history.replaceState to update URL without triggering router navigation
      // This avoids the afterEach scroll-to-top behavior
      window.history.replaceState(window.history.state, "", newUrl);
    }, ANIMATION.debounceUrl);
  }

  // Initialize from URL on mount (waits for router to be ready)
  async function initialize(): Promise<{
    filters: Partial<FilterState>;
    selectedNode: NodeId | null;
    year: number | null;
  }> {
    // Wait for Vue Router to finish initial navigation
    await router.isReady();

    isInitialized.value = true;
    return {
      filters: parseUrlToFilters(),
      selectedNode: parseSelectedNode(),
      year: parseTimelineYear(),
    };
  }

  return {
    isInitialized,
    initialize,
    parseUrlToFilters,
    parseSelectedNode,
    parseTimelineYear,
    updateUrl,
  };
}
