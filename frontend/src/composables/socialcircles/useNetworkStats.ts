/**
 * useNetworkStats - Computes network statistics from nodes and edges.
 */

import { computed, type Ref } from "vue";
import type { ApiNode, ApiEdge, NodeType } from "@/types/socialCircles";
import { calculateGraphStats, findHubs } from "@/utils/socialCircles/graphAlgorithms";

export interface NetworkStats {
  totalNodes: number;
  totalEdges: number;
  nodesByType: { author: number; publisher: number; binder: number };
  mostConnected: { node: ApiNode; degree: number } | null;
  mostProlific: { node: ApiNode; bookCount: number } | null;
  avgDegree: number;
  density: number;
}

/**
 * Composable for computing network statistics from graph data.
 *
 * @param nodes - Reactive reference to the array of nodes
 * @param edges - Reactive reference to the array of edges
 * @returns Computed network statistics
 */
export function useNetworkStats(nodes: Ref<ApiNode[]>, edges: Ref<ApiEdge[]>) {
  const stats = computed<NetworkStats>(() => {
    const nodeList = nodes.value;
    const edgeList = edges.value;

    // Basic counts using existing utility
    const graphStats = calculateGraphStats(nodeList, edgeList);

    // Count nodes by type
    const nodesByType: { author: number; publisher: number; binder: number } = {
      author: 0,
      publisher: 0,
      binder: 0,
    };

    nodeList.forEach((node) => {
      const type = node.type as NodeType;
      if (type in nodesByType) {
        nodesByType[type]++;
      }
    });

    // Find most connected node using existing utility
    const hubs = findHubs(nodeList, edgeList, 1);
    const mostConnected = hubs.length > 0 ? hubs[0] : null;

    // Find most prolific publisher (highest book_count)
    let mostProlific: { node: ApiNode; bookCount: number } | null = null;

    const publishers = nodeList.filter((node) => node.type === "publisher");
    if (publishers.length > 0) {
      const sorted = [...publishers].sort((a, b) => b.book_count - a.book_count);
      if (sorted[0] && sorted[0].book_count > 0) {
        mostProlific = {
          node: sorted[0],
          bookCount: sorted[0].book_count,
        };
      }
    }

    return {
      totalNodes: graphStats.totalNodes,
      totalEdges: graphStats.totalEdges,
      nodesByType,
      mostConnected,
      mostProlific,
      avgDegree: graphStats.avgDegree,
      density: graphStats.density,
    };
  });

  return { stats };
}
