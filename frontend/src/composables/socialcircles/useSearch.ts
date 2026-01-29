/**
 * useSearch - Composable for searching nodes with fuzzy matching.
 *
 * Provides a search interface with debounced query updates, grouped results
 * by node type, and keyboard navigation state management.
 *
 * @example
 * ```ts
 * const nodes = ref<ApiNode[]>([...]);
 * const { query, results, groupedResults, activeIndex, selectResult, navigateUp, navigateDown, clearSearch } = useSearch(nodes);
 *
 * // Bind query to input
 * <input v-model="query" @keydown.up="navigateUp" @keydown.down="navigateDown" />
 *
 * // Display grouped results
 * <div v-for="group in groupedResults" :key="group.type">
 *   <h3>{{ group.label }}</h3>
 *   <div v-for="node in group.nodes" :key="node.id">{{ node.name }}</div>
 * </div>
 * ```
 */

import { ref, computed, watch, onUnmounted, type Ref } from "vue";
import type { ApiNode, NodeType } from "@/types/socialCircles";

/** Maximum number of search results to return */
const MAX_RESULTS = 10;

/** Debounce delay in milliseconds for search query changes */
const DEBOUNCE_MS = 150;

/** Grouped search results by node type */
export interface GroupedResults {
  type: NodeType | "unknown";
  label: string;
  nodes: ApiNode[];
}

/** Human-readable labels for node types */
const NODE_TYPE_LABELS: Record<NodeType | "unknown", string> = {
  author: "Authors",
  publisher: "Publishers",
  binder: "Binders",
  unknown: "Other",
};

/**
 * Composable for searching nodes with fuzzy matching.
 *
 * @param nodes - Reactive reference to the array of nodes to search
 * @returns Search state and navigation methods
 */
export function useSearch(nodes: Ref<ApiNode[]>) {
  const query = ref("");
  const debouncedQuery = ref("");
  const activeIndex = ref(0);

  // Debounce the query to avoid excessive filtering on rapid typing
  let debounceTimeout: ReturnType<typeof setTimeout> | undefined;

  watch(query, (newQuery) => {
    if (debounceTimeout) clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      debouncedQuery.value = newQuery;
    }, DEBOUNCE_MS);
  });

  /**
   * Filtered search results based on debounced query.
   * Uses case-insensitive includes matching.
   */
  const results = computed<ApiNode[]>(() => {
    const q = debouncedQuery.value.trim().toLowerCase();
    if (!q) return [];

    return nodes.value.filter((n) => n.name.toLowerCase().includes(q)).slice(0, MAX_RESULTS);
  });

  /**
   * Search results grouped by node type for organized display.
   */
  const groupedResults = computed<GroupedResults[]>(() => {
    const groups: Partial<Record<NodeType | "unknown", ApiNode[]>> = {};

    for (const node of results.value) {
      const type: NodeType | "unknown" = node.type || "unknown";
      if (!groups[type]) groups[type] = [];
      groups[type]!.push(node);
    }

    // Convert to array with proper labels, maintaining consistent order
    const typeOrder: (NodeType | "unknown")[] = ["author", "publisher", "binder", "unknown"];

    return typeOrder
      .filter((type) => groups[type]?.length)
      .map((type) => ({
        type,
        label: NODE_TYPE_LABELS[type],
        nodes: groups[type]!,
      }));
  });

  /**
   * Select a result by its index in the flat results array.
   *
   * @param index - Index in the results array
   * @returns The selected node or null if index is out of bounds
   */
  function selectResult(index: number): ApiNode | null {
    return results.value[index] || null;
  }

  /**
   * Navigate to the previous result in the list.
   */
  function navigateUp(): void {
    if (activeIndex.value > 0) {
      activeIndex.value--;
    }
  }

  /**
   * Navigate to the next result in the list.
   */
  function navigateDown(): void {
    if (activeIndex.value < results.value.length - 1) {
      activeIndex.value++;
    }
  }

  /**
   * Clear the search query and reset navigation state.
   */
  function clearSearch(): void {
    query.value = "";
    debouncedQuery.value = "";
    activeIndex.value = 0;
    if (debounceTimeout) {
      clearTimeout(debounceTimeout);
      debounceTimeout = undefined;
    }
  }

  // Reset active index when results change
  watch(results, () => {
    activeIndex.value = 0;
  });

  // Cleanup debounce timeout on unmount to prevent memory leak
  onUnmounted(() => {
    if (debounceTimeout) {
      clearTimeout(debounceTimeout);
      debounceTimeout = undefined;
    }
  });

  return {
    query,
    results,
    groupedResults,
    activeIndex,
    selectResult,
    navigateUp,
    navigateDown,
    clearSearch,
  };
}
