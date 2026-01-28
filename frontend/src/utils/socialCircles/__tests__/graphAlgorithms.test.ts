import { describe, it, expect } from "vitest";
import {
  buildAdjacencyList,
  findShortestPath,
  degreesOfSeparation,
  calculateDegreeCentrality,
  findHubs,
  findSimilarNodes,
  calculateGraphStats,
} from "../graphAlgorithms";
import type { ApiNode, ApiEdge, NodeId, EdgeId, BookId } from "@/types/socialCircles";

// =============================================================================
// Test Fixtures
// =============================================================================

/** Helper to create typed NodeId */
function nodeId(id: string): NodeId {
  return id as NodeId;
}

/** Helper to create typed EdgeId */
function edgeId(id: string): EdgeId {
  return id as EdgeId;
}

/** Helper to create test nodes */
function createTestNode(
  id: string,
  name: string,
  type: "author" | "publisher" = "author"
): ApiNode {
  return {
    id: nodeId(id),
    entity_id: parseInt(id.split(":")[1] || "1", 10),
    name,
    type,
    book_count: 1,
    book_ids: [1 as BookId],
  };
}

/** Helper to create test edges */
function createTestEdge(source: string, target: string, strength = 1): ApiEdge {
  return {
    id: edgeId(`e:${source}:${target}`),
    source: nodeId(source),
    target: nodeId(target),
    type: "publisher",
    strength,
  };
}

// Linear graph: A -- B -- C -- D
const linearNodes: ApiNode[] = [
  createTestNode("author:1", "Alice"),
  createTestNode("author:2", "Bob"),
  createTestNode("author:3", "Charlie"),
  createTestNode("author:4", "Diana"),
];

const linearEdges: ApiEdge[] = [
  createTestEdge("author:1", "author:2"),
  createTestEdge("author:2", "author:3"),
  createTestEdge("author:3", "author:4"),
];

// Star graph: Hub connected to all spokes
//     B
//     |
// C - A - D
//     |
//     E
const starNodes: ApiNode[] = [
  createTestNode("author:1", "Hub"),
  createTestNode("author:2", "Spoke B"),
  createTestNode("author:3", "Spoke C"),
  createTestNode("author:4", "Spoke D"),
  createTestNode("author:5", "Spoke E"),
];

const starEdges: ApiEdge[] = [
  createTestEdge("author:1", "author:2"),
  createTestEdge("author:1", "author:3"),
  createTestEdge("author:1", "author:4"),
  createTestEdge("author:1", "author:5"),
];

// Triangle + isolated node
// A -- B
// |  /
// C        D (isolated)
const triangleNodes: ApiNode[] = [
  createTestNode("author:1", "A"),
  createTestNode("author:2", "B"),
  createTestNode("author:3", "C"),
  createTestNode("author:4", "D"), // isolated
];

const triangleEdges: ApiEdge[] = [
  createTestEdge("author:1", "author:2"),
  createTestEdge("author:2", "author:3"),
  createTestEdge("author:1", "author:3"),
];

// =============================================================================
// buildAdjacencyList Tests
// =============================================================================

describe("buildAdjacencyList", () => {
  it("creates bidirectional adjacency list", () => {
    const adjacency = buildAdjacencyList(linearEdges);

    // A-B connection should be bidirectional
    expect(adjacency.get(nodeId("author:1"))?.has(nodeId("author:2"))).toBe(true);
    expect(adjacency.get(nodeId("author:2"))?.has(nodeId("author:1"))).toBe(true);

    // B-C connection
    expect(adjacency.get(nodeId("author:2"))?.has(nodeId("author:3"))).toBe(true);
    expect(adjacency.get(nodeId("author:3"))?.has(nodeId("author:2"))).toBe(true);
  });

  it("handles empty edges", () => {
    const adjacency = buildAdjacencyList([]);
    expect(adjacency.size).toBe(0);
  });

  it("creates correct neighbor sets for star graph", () => {
    const adjacency = buildAdjacencyList(starEdges);

    // Hub should have 4 neighbors
    const hubNeighbors = adjacency.get(nodeId("author:1"));
    expect(hubNeighbors?.size).toBe(4);

    // Spokes should each have 1 neighbor (the hub)
    expect(adjacency.get(nodeId("author:2"))?.size).toBe(1);
    expect(adjacency.get(nodeId("author:3"))?.size).toBe(1);
    expect(adjacency.get(nodeId("author:4"))?.size).toBe(1);
    expect(adjacency.get(nodeId("author:5"))?.size).toBe(1);
  });

  it("handles single edge", () => {
    const singleEdge = [createTestEdge("author:1", "author:2")];
    const adjacency = buildAdjacencyList(singleEdge);

    expect(adjacency.size).toBe(2);
    expect(adjacency.get(nodeId("author:1"))?.has(nodeId("author:2"))).toBe(true);
    expect(adjacency.get(nodeId("author:2"))?.has(nodeId("author:1"))).toBe(true);
  });
});

// =============================================================================
// findShortestPath Tests
// =============================================================================

describe("findShortestPath", () => {
  it("returns single node path for same start and end", () => {
    const adjacency = buildAdjacencyList(linearEdges);
    const path = findShortestPath(adjacency, nodeId("author:1"), nodeId("author:1"));

    expect(path).toEqual([nodeId("author:1")]);
  });

  it("finds direct path between neighbors", () => {
    const adjacency = buildAdjacencyList(linearEdges);
    const path = findShortestPath(adjacency, nodeId("author:1"), nodeId("author:2"));

    expect(path).toEqual([nodeId("author:1"), nodeId("author:2")]);
  });

  it("finds multi-hop path", () => {
    const adjacency = buildAdjacencyList(linearEdges);
    const path = findShortestPath(adjacency, nodeId("author:1"), nodeId("author:4"));

    // A -> B -> C -> D
    expect(path).toEqual([
      nodeId("author:1"),
      nodeId("author:2"),
      nodeId("author:3"),
      nodeId("author:4"),
    ]);
  });

  it("returns null for disconnected nodes", () => {
    const adjacency = buildAdjacencyList(triangleEdges);
    // D is isolated
    const path = findShortestPath(adjacency, nodeId("author:1"), nodeId("author:4"));

    expect(path).toBeNull();
  });

  it("returns null when start node not in adjacency", () => {
    const adjacency = buildAdjacencyList(linearEdges);
    const path = findShortestPath(adjacency, nodeId("author:999"), nodeId("author:1"));

    expect(path).toBeNull();
  });

  it("returns null when end node not in adjacency", () => {
    const adjacency = buildAdjacencyList(linearEdges);
    const path = findShortestPath(adjacency, nodeId("author:1"), nodeId("author:999"));

    expect(path).toBeNull();
  });

  it("finds shortest path in triangle (multiple routes possible)", () => {
    const adjacency = buildAdjacencyList(triangleEdges);
    const path = findShortestPath(adjacency, nodeId("author:1"), nodeId("author:2"));

    // Direct path should be found
    expect(path).toHaveLength(2);
    expect(path?.[0]).toBe(nodeId("author:1"));
    expect(path?.[1]).toBe(nodeId("author:2"));
  });

  it("finds path through hub in star graph", () => {
    const adjacency = buildAdjacencyList(starEdges);
    // B to C must go through Hub
    const path = findShortestPath(adjacency, nodeId("author:2"), nodeId("author:3"));

    expect(path).toHaveLength(3);
    expect(path).toEqual([nodeId("author:2"), nodeId("author:1"), nodeId("author:3")]);
  });
});

// =============================================================================
// degreesOfSeparation Tests
// =============================================================================

describe("degreesOfSeparation", () => {
  it("returns 0 for same node", () => {
    const adjacency = buildAdjacencyList(linearEdges);
    const degrees = degreesOfSeparation(adjacency, nodeId("author:1"), nodeId("author:1"));

    expect(degrees).toBe(0);
  });

  it("returns 1 for direct neighbors", () => {
    const adjacency = buildAdjacencyList(linearEdges);
    const degrees = degreesOfSeparation(adjacency, nodeId("author:1"), nodeId("author:2"));

    expect(degrees).toBe(1);
  });

  it("returns 2 for two hops", () => {
    const adjacency = buildAdjacencyList(linearEdges);
    const degrees = degreesOfSeparation(adjacency, nodeId("author:1"), nodeId("author:3"));

    expect(degrees).toBe(2);
  });

  it("returns 3 for three hops", () => {
    const adjacency = buildAdjacencyList(linearEdges);
    const degrees = degreesOfSeparation(adjacency, nodeId("author:1"), nodeId("author:4"));

    expect(degrees).toBe(3);
  });

  it("returns -1 for disconnected nodes", () => {
    const adjacency = buildAdjacencyList(triangleEdges);
    const degrees = degreesOfSeparation(adjacency, nodeId("author:1"), nodeId("author:4"));

    expect(degrees).toBe(-1);
  });

  it("calculates Kevin Bacon number through hub", () => {
    const adjacency = buildAdjacencyList(starEdges);
    // Spoke to spoke = 2 hops through hub
    const degrees = degreesOfSeparation(adjacency, nodeId("author:2"), nodeId("author:5"));

    expect(degrees).toBe(2);
  });
});

// =============================================================================
// calculateDegreeCentrality Tests
// =============================================================================

describe("calculateDegreeCentrality", () => {
  it("initializes all nodes with 0 for empty edges", () => {
    const centrality = calculateDegreeCentrality(linearNodes, []);

    expect(centrality.get(nodeId("author:1"))).toBe(0);
    expect(centrality.get(nodeId("author:2"))).toBe(0);
    expect(centrality.get(nodeId("author:3"))).toBe(0);
    expect(centrality.get(nodeId("author:4"))).toBe(0);
  });

  it("calculates correct degree for linear graph", () => {
    const centrality = calculateDegreeCentrality(linearNodes, linearEdges);

    // End nodes have degree 1, middle nodes have degree 2
    expect(centrality.get(nodeId("author:1"))).toBe(1); // A
    expect(centrality.get(nodeId("author:2"))).toBe(2); // B
    expect(centrality.get(nodeId("author:3"))).toBe(2); // C
    expect(centrality.get(nodeId("author:4"))).toBe(1); // D
  });

  it("calculates correct degree for star graph", () => {
    const centrality = calculateDegreeCentrality(starNodes, starEdges);

    // Hub has degree 4, spokes have degree 1
    expect(centrality.get(nodeId("author:1"))).toBe(4); // Hub
    expect(centrality.get(nodeId("author:2"))).toBe(1); // Spoke
    expect(centrality.get(nodeId("author:3"))).toBe(1);
    expect(centrality.get(nodeId("author:4"))).toBe(1);
    expect(centrality.get(nodeId("author:5"))).toBe(1);
  });

  it("calculates correct degree for triangle", () => {
    const centrality = calculateDegreeCentrality(triangleNodes, triangleEdges);

    // All triangle nodes have degree 2, isolated has 0
    expect(centrality.get(nodeId("author:1"))).toBe(2);
    expect(centrality.get(nodeId("author:2"))).toBe(2);
    expect(centrality.get(nodeId("author:3"))).toBe(2);
    expect(centrality.get(nodeId("author:4"))).toBe(0); // Isolated
  });
});

// =============================================================================
// findHubs Tests
// =============================================================================

describe("findHubs", () => {
  it("returns empty array for empty graph", () => {
    const hubs = findHubs([], []);
    expect(hubs).toEqual([]);
  });

  it("finds hub in star graph", () => {
    const hubs = findHubs(starNodes, starEdges, 1);

    expect(hubs).toHaveLength(1);
    expect(hubs[0].node.name).toBe("Hub");
    expect(hubs[0].degree).toBe(4);
  });

  it("returns nodes sorted by degree descending", () => {
    const hubs = findHubs(linearNodes, linearEdges);

    // B and C have degree 2, A and D have degree 1
    expect(hubs[0].degree).toBeGreaterThanOrEqual(hubs[1].degree);
    expect(hubs[1].degree).toBeGreaterThanOrEqual(hubs[2].degree);
    expect(hubs[2].degree).toBeGreaterThanOrEqual(hubs[3].degree);
  });

  it("respects limit parameter", () => {
    const hubs = findHubs(starNodes, starEdges, 2);

    expect(hubs).toHaveLength(2);
  });

  it("returns all nodes if limit exceeds node count", () => {
    const hubs = findHubs(linearNodes, linearEdges, 100);

    expect(hubs).toHaveLength(4);
  });

  it("includes isolated nodes with degree 0", () => {
    const hubs = findHubs(triangleNodes, triangleEdges, 10);

    const isolatedHub = hubs.find((h) => h.node.name === "D");
    expect(isolatedHub).toBeDefined();
    expect(isolatedHub?.degree).toBe(0);
  });
});

// =============================================================================
// findSimilarNodes Tests
// =============================================================================

describe("findSimilarNodes", () => {
  // Create a more complex graph for similarity testing
  // A -- B -- C
  // |    |    |
  // D -- E -- F
  // B and E share neighbors: A, C, D, F
  const gridNodes: ApiNode[] = [
    createTestNode("author:1", "A"),
    createTestNode("author:2", "B"),
    createTestNode("author:3", "C"),
    createTestNode("author:4", "D"),
    createTestNode("author:5", "E"),
    createTestNode("author:6", "F"),
  ];

  const gridEdges: ApiEdge[] = [
    createTestEdge("author:1", "author:2"), // A-B
    createTestEdge("author:2", "author:3"), // B-C
    createTestEdge("author:1", "author:4"), // A-D
    createTestEdge("author:4", "author:5"), // D-E
    createTestEdge("author:2", "author:5"), // B-E
    createTestEdge("author:5", "author:6"), // E-F
    createTestEdge("author:3", "author:6"), // C-F
  ];

  it("returns empty array for node not in graph", () => {
    const adjacency = buildAdjacencyList(gridEdges);
    const similar = findSimilarNodes(adjacency, gridNodes, nodeId("author:999"));

    expect(similar).toEqual([]);
  });

  it("finds nodes with shared connections", () => {
    const adjacency = buildAdjacencyList(gridEdges);
    // Find nodes similar to B (neighbors: A, C, E)
    const similar = findSimilarNodes(adjacency, gridNodes, nodeId("author:2"));

    expect(similar.length).toBeGreaterThan(0);
    // All returned nodes should have at least 1 shared connection
    similar.forEach((s) => {
      expect(s.sharedConnections).toBeGreaterThan(0);
    });
  });

  it("returns results sorted by shared connections descending", () => {
    const adjacency = buildAdjacencyList(gridEdges);
    const similar = findSimilarNodes(adjacency, gridNodes, nodeId("author:2"), 10);

    for (let i = 0; i < similar.length - 1; i++) {
      expect(similar[i].sharedConnections).toBeGreaterThanOrEqual(similar[i + 1].sharedConnections);
    }
  });

  it("respects limit parameter", () => {
    const adjacency = buildAdjacencyList(gridEdges);
    const similar = findSimilarNodes(adjacency, gridNodes, nodeId("author:2"), 2);

    expect(similar.length).toBeLessThanOrEqual(2);
  });

  it("does not include the target node itself", () => {
    const adjacency = buildAdjacencyList(gridEdges);
    const similar = findSimilarNodes(adjacency, gridNodes, nodeId("author:2"), 10);

    const selfIncluded = similar.find((s) => s.node.id === nodeId("author:2"));
    expect(selfIncluded).toBeUndefined();
  });

  it("returns empty array for isolated node", () => {
    const adjacency = buildAdjacencyList(triangleEdges);
    // D is isolated
    const similar = findSimilarNodes(adjacency, triangleNodes, nodeId("author:4"));

    expect(similar).toEqual([]);
  });

  it("excludes nodes with no shared connections", () => {
    // In star graph, spokes share no connections with each other
    // (they only connect to hub, not to each other)
    const adjacency = buildAdjacencyList(starEdges);
    // Spoke B's only neighbor is Hub. Other spokes' only neighbor is also Hub.
    // But spokes don't share Hub as a "shared neighbor" because they're not neighbors of each other
    const similar = findSimilarNodes(adjacency, starNodes, nodeId("author:2"), 10);

    // Only Hub shares connections with spoke B (the other spokes through hub)
    // But Hub is B's neighbor, not a "similar" node
    // Actually, C,D,E all have Hub as neighbor, and B also has Hub, so they share Hub
    // Wait - the algorithm looks for shared neighbors, not direct connections
    // B's neighbor is Hub (author:1). C,D,E neighbors are also Hub.
    // So C,D,E share Hub with B - they have 1 shared connection each
    expect(similar.length).toBe(3); // C, D, E all share Hub with B
    similar.forEach((s) => {
      expect(s.sharedConnections).toBe(1);
    });
  });
});

// =============================================================================
// calculateGraphStats Tests
// =============================================================================

describe("calculateGraphStats", () => {
  it("calculates correct stats for empty graph", () => {
    const stats = calculateGraphStats([], []);

    expect(stats.totalNodes).toBe(0);
    expect(stats.totalEdges).toBe(0);
    expect(stats.avgDegree).toBe(0);
    expect(stats.maxDegree).toBe(0);
    expect(stats.density).toBe(0);
  });

  it("calculates correct node and edge counts", () => {
    const stats = calculateGraphStats(linearNodes, linearEdges);

    expect(stats.totalNodes).toBe(4);
    expect(stats.totalEdges).toBe(3);
  });

  it("calculates correct average degree", () => {
    const stats = calculateGraphStats(linearNodes, linearEdges);

    // Degrees: A=1, B=2, C=2, D=1, sum=6, avg=1.5
    expect(stats.avgDegree).toBe(1.5);
  });

  it("calculates correct max degree", () => {
    const stats = calculateGraphStats(starNodes, starEdges);

    expect(stats.maxDegree).toBe(4); // Hub has degree 4
  });

  it("calculates density for complete triangle", () => {
    // Triangle has 3 nodes and 3 edges
    // Max possible edges = 3*2/2 = 3
    // Density = 3/3 = 1 (fully connected)
    const triangleOnlyNodes = triangleNodes.slice(0, 3); // Remove isolated node
    const stats = calculateGraphStats(triangleOnlyNodes, triangleEdges);

    expect(stats.density).toBe(1);
  });

  it("calculates density for star graph", () => {
    const stats = calculateGraphStats(starNodes, starEdges);

    // 5 nodes, 4 edges
    // Max possible edges = 5*4/2 = 10
    // Density = 4/10 = 0.4
    expect(stats.density).toBe(0.4);
  });

  it("calculates density for linear graph", () => {
    const stats = calculateGraphStats(linearNodes, linearEdges);

    // 4 nodes, 3 edges
    // Max possible edges = 4*3/2 = 6
    // Density = 3/6 = 0.5
    expect(stats.density).toBe(0.5);
  });

  it("handles graph with isolated nodes", () => {
    const stats = calculateGraphStats(triangleNodes, triangleEdges);

    // 4 nodes (including isolated), 3 edges
    expect(stats.totalNodes).toBe(4);
    expect(stats.totalEdges).toBe(3);
    // Avg degree: (2+2+2+0)/4 = 1.5
    expect(stats.avgDegree).toBe(1.5);
    // Max possible = 4*3/2 = 6, density = 3/6 = 0.5
    expect(stats.density).toBe(0.5);
  });

  it("returns properly rounded values", () => {
    // Create a graph that produces non-integer averages
    const nodes = [
      createTestNode("author:1", "A"),
      createTestNode("author:2", "B"),
      createTestNode("author:3", "C"),
    ];
    const edges = [createTestEdge("author:1", "author:2")];

    const stats = calculateGraphStats(nodes, edges);

    // Degrees: 1, 1, 0, avg = 2/3 = 0.666...
    // Should be rounded to 2 decimal places
    expect(stats.avgDegree).toBe(0.67);

    // Density = 1/3 = 0.333... rounded to 3 decimal places
    expect(stats.density).toBe(0.333);
  });

  it("handles single node graph", () => {
    const singleNode = [createTestNode("author:1", "Lonely")];
    const stats = calculateGraphStats(singleNode, []);

    expect(stats.totalNodes).toBe(1);
    expect(stats.totalEdges).toBe(0);
    expect(stats.avgDegree).toBe(0);
    expect(stats.maxDegree).toBe(0);
    // Max possible edges = 1*0/2 = 0, density = 0/0 which should be 0
    expect(stats.density).toBe(0);
  });
});
