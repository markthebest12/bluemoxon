/**
 * usePathFinder - Composable for finding shortest paths between nodes.
 * Uses BFS algorithm to find the shortest path in an undirected graph.
 */

import { ref, computed, type Ref } from "vue";
import type { ApiNode, ApiEdge, NodeId } from "@/types/socialCircles";
import { buildAdjacencyList, findShortestPath } from "@/utils/socialCircles/graphAlgorithms";

/** Maximum number of results returned by node filter functions. */
export const MAX_FILTER_RESULTS = 20;

/**
 * Filter nodes by a search query string, returning at most MAX_FILTER_RESULTS.
 * When the query is empty, returns the first MAX_FILTER_RESULTS nodes.
 */
export function filterNodesByQuery(nodes: ApiNode[], query: string): ApiNode[] {
  const normalised = query.toLowerCase().trim();
  if (!normalised) return nodes.slice(0, MAX_FILTER_RESULTS);
  const results: ApiNode[] = [];
  for (const n of nodes) {
    if (n.name.toLowerCase().includes(normalised)) {
      results.push(n);
      if (results.length >= MAX_FILTER_RESULTS) break;
    }
  }
  return results;
}

export function usePathFinder(nodes: Ref<ApiNode[]>, edges: Ref<ApiEdge[]>) {
  const startNodeId = ref<NodeId | null>(null);
  const endNodeId = ref<NodeId | null>(null);
  const path = ref<NodeId[] | null>(null);
  const isCalculating = ref(false);
  const noPathFound = ref(false);

  // Computed: lookup maps for node details
  const nodesMap = computed(() => {
    const map = new Map<NodeId, ApiNode>();
    nodes.value.forEach((node) => map.set(node.id, node));
    return map;
  });

  // Computed: get start node details
  const startNode = computed(() => {
    return startNodeId.value ? nodesMap.value.get(startNodeId.value) || null : null;
  });

  // Computed: get end node details
  const endNode = computed(() => {
    return endNodeId.value ? nodesMap.value.get(endNodeId.value) || null : null;
  });

  // Computed: path length (degrees of separation)
  const pathLength = computed(() => {
    return path.value ? path.value.length - 1 : null;
  });

  // Computed: get full node details for path
  const pathNodes = computed(() => {
    if (!path.value) return null;
    return path.value
      .map((id) => nodesMap.value.get(id))
      .filter((node): node is ApiNode => node !== undefined);
  });

  // Computed: check if path finding is ready (both nodes selected)
  const isReady = computed(() => {
    return startNodeId.value !== null && endNodeId.value !== null;
  });

  // Computed: check if start and end are the same
  const isSameNode = computed(() => {
    return (
      startNodeId.value !== null &&
      endNodeId.value !== null &&
      startNodeId.value === endNodeId.value
    );
  });

  /**
   * Find the shortest path between start and end nodes.
   * Uses BFS algorithm via the graphAlgorithms utility.
   */
  function findPath(): void {
    if (!startNodeId.value || !endNodeId.value) return;

    isCalculating.value = true;
    noPathFound.value = false;
    path.value = null;

    // Build adjacency list from current edges
    const adjacency = buildAdjacencyList(edges.value);

    // Run BFS to find shortest path
    const result = findShortestPath(adjacency, startNodeId.value, endNodeId.value);

    if (result) {
      path.value = result;
    } else {
      noPathFound.value = true;
    }

    isCalculating.value = false;
  }

  /**
   * Set the start node for path finding.
   */
  function setStart(nodeId: NodeId | null): void {
    startNodeId.value = nodeId;
    // Clear previous path results when changing nodes
    path.value = null;
    noPathFound.value = false;
  }

  /**
   * Set the end node for path finding.
   */
  function setEnd(nodeId: NodeId | null): void {
    endNodeId.value = nodeId;
    // Clear previous path results when changing nodes
    path.value = null;
    noPathFound.value = false;
  }

  /**
   * Swap start and end nodes.
   */
  function swapNodes(): void {
    const temp = startNodeId.value;
    startNodeId.value = endNodeId.value;
    endNodeId.value = temp;
    // Clear path since direction changed (though result should be same for undirected)
    path.value = null;
    noPathFound.value = false;
  }

  /**
   * Clear all path finding state.
   */
  function clear(): void {
    startNodeId.value = null;
    endNodeId.value = null;
    path.value = null;
    noPathFound.value = false;
    isCalculating.value = false;
  }

  /**
   * Check if a node is part of the current path.
   */
  function isNodeInPath(nodeId: NodeId): boolean {
    return path.value?.includes(nodeId) ?? false;
  }

  /**
   * Get the edges that form the path.
   * Returns edge IDs for highlighting purposes.
   */
  function getPathEdgeIds(): string[] {
    if (!path.value || path.value.length < 2) return [];

    const edgeIds: string[] = [];
    const edgeMap = new Map<string, ApiEdge>();

    // Build a lookup for edges by their node pairs (both directions)
    edges.value.forEach((edge) => {
      const key1 = `${edge.source}-${edge.target}`;
      const key2 = `${edge.target}-${edge.source}`;
      edgeMap.set(key1, edge);
      edgeMap.set(key2, edge);
    });

    // Find edges connecting consecutive path nodes
    for (let i = 0; i < path.value.length - 1; i++) {
      const key = `${path.value[i]}-${path.value[i + 1]}`;
      const edge = edgeMap.get(key);
      if (edge) {
        edgeIds.push(edge.id);
      }
    }

    return edgeIds;
  }

  return {
    // State
    startNodeId,
    endNodeId,
    path,
    isCalculating,
    noPathFound,

    // Computed
    startNode,
    endNode,
    pathLength,
    pathNodes,
    isReady,
    isSameNode,

    // Actions
    findPath,
    setStart,
    setEnd,
    swapNodes,
    clear,
    isNodeInPath,
    getPathEdgeIds,
  };
}
