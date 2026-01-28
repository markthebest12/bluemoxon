/**
 * useFindSimilar - Find nodes similar to a selected node based on shared connections.
 * Uses the Jaccard-style similarity from graphAlgorithms.
 */

import { ref, computed, type Ref } from "vue";
import type { ApiNode, ApiEdge, NodeId } from "@/types/socialCircles";
import { buildAdjacencyList, findSimilarNodes } from "@/utils/socialCircles/graphAlgorithms";

export interface SimilarNode {
  node: ApiNode;
  sharedConnections: number;
}

export function useFindSimilar(nodes: Ref<ApiNode[]>, edges: Ref<ApiEdge[]>) {
  const similarNodes = ref<SimilarNode[]>([]);
  const currentTargetId = ref<NodeId | null>(null);

  // Computed adjacency list that updates when edges change
  const adjacency = computed(() => buildAdjacencyList(edges.value));

  /**
   * Find nodes similar to the given node based on shared connections.
   * @param nodeId - The target node to find similar nodes for
   * @param limit - Maximum number of similar nodes to return (default: 5)
   */
  function findSimilar(nodeId: NodeId, limit: number = 5): void {
    currentTargetId.value = nodeId;

    // Use the existing graph algorithm
    const results = findSimilarNodes(adjacency.value, nodes.value, nodeId, limit);

    similarNodes.value = results;
  }

  /**
   * Clear the similar nodes list.
   */
  function clear(): void {
    similarNodes.value = [];
    currentTargetId.value = null;
  }

  /**
   * Check if there are any similar nodes found.
   */
  const hasSimilarNodes = computed(() => similarNodes.value.length > 0);

  /**
   * Get the total count of similar nodes.
   */
  const similarCount = computed(() => similarNodes.value.length);

  return {
    similarNodes,
    currentTargetId,
    hasSimilarNodes,
    similarCount,
    findSimilar,
    clear,
  };
}
