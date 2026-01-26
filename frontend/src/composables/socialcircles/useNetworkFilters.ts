/**
 * useNetworkFilters - Manages filter state for the graph.
 */

import { ref, computed, readonly } from "vue";
import type { FilterState, ConnectionType, Era } from "@/types/socialCircles";
import { DEFAULT_FILTER_STATE } from "@/types/socialCircles";

export function useNetworkFilters() {
  const filters = ref<FilterState>({ ...DEFAULT_FILTER_STATE });

  // Computed helpers
  const hasActiveFilters = computed(() => {
    const f = filters.value;
    return (
      !f.showAuthors ||
      !f.showPublishers ||
      !f.showBinders ||
      f.connectionTypes.length < 3 ||
      f.tier1Only ||
      f.eras.length > 0 ||
      f.searchQuery !== ""
    );
  });

  const activeFilterCount = computed(() => {
    let count = 0;
    const f = filters.value;
    if (!f.showAuthors) count++;
    if (!f.showPublishers) count++;
    if (!f.showBinders) count++;
    if (f.connectionTypes.length < 3) count++;
    if (f.tier1Only) count++;
    if (f.eras.length > 0) count += f.eras.length;
    if (f.searchQuery) count++;
    return count;
  });

  // Actions
  function setShowAuthors(value: boolean) {
    filters.value.showAuthors = value;
  }

  function setShowPublishers(value: boolean) {
    filters.value.showPublishers = value;
  }

  function setShowBinders(value: boolean) {
    filters.value.showBinders = value;
  }

  function setConnectionTypes(types: ConnectionType[]) {
    filters.value.connectionTypes = types;
  }

  function toggleConnectionType(type: ConnectionType) {
    const types = filters.value.connectionTypes;
    const index = types.indexOf(type);
    if (index >= 0) {
      types.splice(index, 1);
    } else {
      types.push(type);
    }
  }

  function setTier1Only(value: boolean) {
    filters.value.tier1Only = value;
  }

  function setEras(eras: Era[]) {
    filters.value.eras = eras;
  }

  function toggleEra(era: Era) {
    const eras = filters.value.eras;
    const index = eras.indexOf(era);
    if (index >= 0) {
      eras.splice(index, 1);
    } else {
      eras.push(era);
    }
  }

  function setSearchQuery(query: string) {
    filters.value.searchQuery = query;
  }

  function resetFilters() {
    filters.value = { ...DEFAULT_FILTER_STATE };
  }

  return {
    filters: readonly(filters),
    hasActiveFilters,
    activeFilterCount,
    setShowAuthors,
    setShowPublishers,
    setShowBinders,
    setConnectionTypes,
    toggleConnectionType,
    setTier1Only,
    setEras,
    toggleEra,
    setSearchQuery,
    resetFilters,
  };
}
