/**
 * Graph algorithms for social circles analysis.
 * Shortest path, centrality calculations, etc.
 */

import type { ApiNode, ApiEdge, NodeId } from "@/types/socialCircles";

/**
 * Build adjacency list from edges.
 */
export function buildAdjacencyList(edges: ApiEdge[]): Map<NodeId, Set<NodeId>> {
  const adjacency = new Map<NodeId, Set<NodeId>>();

  edges.forEach((edge) => {
    const source = edge.source as NodeId;
    const target = edge.target as NodeId;

    if (!adjacency.has(source)) {
      adjacency.set(source, new Set());
    }
    if (!adjacency.has(target)) {
      adjacency.set(target, new Set());
    }

    adjacency.get(source)!.add(target);
    adjacency.get(target)!.add(source);
  });

  return adjacency;
}

/**
 * Find shortest path between two nodes using BFS.
 * Returns the path as array of node IDs, or null if no path exists.
 */
export function findShortestPath(
  adjacency: Map<NodeId, Set<NodeId>>,
  startId: NodeId,
  endId: NodeId
): NodeId[] | null {
  if (startId === endId) return [startId];

  const visited = new Set<NodeId>();
  const queue: { nodeId: NodeId; path: NodeId[] }[] = [{ nodeId: startId, path: [startId] }];

  while (queue.length > 0) {
    const { nodeId, path } = queue.shift()!;

    if (visited.has(nodeId)) continue;
    visited.add(nodeId);

    const neighbors = adjacency.get(nodeId);
    if (!neighbors) continue;

    for (const neighbor of neighbors) {
      if (neighbor === endId) {
        return [...path, neighbor];
      }

      if (!visited.has(neighbor)) {
        queue.push({ nodeId: neighbor, path: [...path, neighbor] });
      }
    }
  }

  return null; // No path found
}

/**
 * Calculate degrees of separation between two nodes.
 * Returns -1 if no connection exists.
 */
export function degreesOfSeparation(
  adjacency: Map<NodeId, Set<NodeId>>,
  startId: NodeId,
  endId: NodeId
): number {
  const path = findShortestPath(adjacency, startId, endId);
  return path ? path.length - 1 : -1;
}

/**
 * Calculate degree centrality for all nodes.
 * Higher degree = more connected.
 */
export function calculateDegreeCentrality(nodes: ApiNode[], edges: ApiEdge[]): Map<NodeId, number> {
  const centrality = new Map<NodeId, number>();

  // Initialize all nodes with 0
  nodes.forEach((node) => {
    centrality.set(node.id, 0);
  });

  // Count edges for each node
  edges.forEach((edge) => {
    const source = edge.source as NodeId;
    const target = edge.target as NodeId;

    centrality.set(source, (centrality.get(source) || 0) + 1);
    centrality.set(target, (centrality.get(target) || 0) + 1);
  });

  return centrality;
}

/**
 * Find the most connected nodes (hubs).
 */
export function findHubs(
  nodes: ApiNode[],
  edges: ApiEdge[],
  limit = 10
): { node: ApiNode; degree: number }[] {
  const centrality = calculateDegreeCentrality(nodes, edges);

  const nodesWithDegree = nodes.map((node) => ({
    node,
    degree: centrality.get(node.id) || 0,
  }));

  return nodesWithDegree.sort((a, b) => b.degree - a.degree).slice(0, limit);
}

/**
 * Find nodes similar to a given node (share many connections).
 */
export function findSimilarNodes(
  adjacency: Map<NodeId, Set<NodeId>>,
  nodes: ApiNode[],
  targetId: NodeId,
  limit = 5
): { node: ApiNode; sharedConnections: number }[] {
  const targetNeighbors = adjacency.get(targetId);
  if (!targetNeighbors) return [];

  const similarities: { nodeId: NodeId; shared: number }[] = [];

  adjacency.forEach((neighbors, nodeId) => {
    if (nodeId === targetId) return;

    // Count shared neighbors
    let sharedCount = 0;
    neighbors.forEach((n) => {
      if (targetNeighbors.has(n)) sharedCount++;
    });

    if (sharedCount > 0) {
      similarities.push({ nodeId, shared: sharedCount });
    }
  });

  // Sort by shared connections
  similarities.sort((a, b) => b.shared - a.shared);

  // Map back to nodes
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return similarities
    .slice(0, limit)
    .map((s) => ({
      node: nodeMap.get(s.nodeId)!,
      sharedConnections: s.shared,
    }))
    .filter((s) => s.node);
}

/**
 * Calculate graph statistics.
 */
export function calculateGraphStats(
  nodes: ApiNode[],
  edges: ApiEdge[]
): {
  totalNodes: number;
  totalEdges: number;
  avgDegree: number;
  maxDegree: number;
  density: number;
} {
  const centrality = calculateDegreeCentrality(nodes, edges);
  const degrees = Array.from(centrality.values());

  const totalNodes = nodes.length;
  const totalEdges = edges.length;
  const avgDegree = degrees.length > 0 ? degrees.reduce((a, b) => a + b, 0) / degrees.length : 0;
  const maxDegree = degrees.length > 0 ? Math.max(...degrees) : 0;

  // Graph density = 2E / N(N-1) for undirected graph
  const maxPossibleEdges = (totalNodes * (totalNodes - 1)) / 2;
  const density = maxPossibleEdges > 0 ? totalEdges / maxPossibleEdges : 0;

  return {
    totalNodes,
    totalEdges,
    avgDegree: Math.round(avgDegree * 100) / 100,
    maxDegree,
    density: Math.round(density * 1000) / 1000,
  };
}
