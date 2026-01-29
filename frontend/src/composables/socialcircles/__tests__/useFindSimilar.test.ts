/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck - Test mocks don't need full type compliance
import { describe, it, expect } from "vitest";
import { ref } from "vue";
import { useFindSimilar } from "../useFindSimilar";
import type { ApiNode, ApiEdge } from "@/types/socialCircles";

// Helper to create minimal mock nodes
function createMockNode(id: string, name: string, type: string): ApiNode {
  return {
    id,
    entity_id: parseInt(id.replace(/\D/g, "") || "0"),
    name,
    type: type as ApiNode["type"],
    book_count: 0,
    book_ids: [],
  };
}

// Helper to create minimal mock edges
function createMockEdge(source: string, target: string): ApiEdge {
  return {
    id: `${source}-${target}`,
    source,
    target,
    type: "collaboration",
    strength: 1,
  };
}

const mockNodes: ApiNode[] = [
  createMockNode("1", "Author 1", "author"),
  createMockNode("2", "Author 2", "author"),
  createMockNode("3", "Author 3", "author"),
  createMockNode("p1", "Publisher 1", "publisher"),
  createMockNode("p2", "Publisher 2", "publisher"),
];

// Authors 1 and 2 share Publisher 1
// Authors 2 and 3 share Publisher 2
const mockEdges: ApiEdge[] = [
  createMockEdge("1", "p1"),
  createMockEdge("2", "p1"),
  createMockEdge("2", "p2"),
  createMockEdge("3", "p2"),
];

describe("useFindSimilar", () => {
  it("finds nodes with shared connections", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { findSimilar, similarNodes } = useFindSimilar(nodes, edges);
    findSimilar("1");
    expect(similarNodes.value.length).toBeGreaterThan(0);
    // Author 2 shares Publisher 1 with Author 1
    expect(similarNodes.value.some((s) => s.node.id === "2")).toBe(true);
  });

  it("sorts by shared connections descending", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { findSimilar, similarNodes } = useFindSimilar(nodes, edges);
    findSimilar("2"); // Author 2 has connections to p1 and p2
    // Should be sorted by sharedConnections
    for (let i = 1; i < similarNodes.value.length; i++) {
      expect(similarNodes.value[i - 1].sharedConnections).toBeGreaterThanOrEqual(
        similarNodes.value[i].sharedConnections
      );
    }
  });

  it("respects limit parameter", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { findSimilar, similarNodes } = useFindSimilar(nodes, edges);
    findSimilar("2", 1);
    expect(similarNodes.value.length).toBeLessThanOrEqual(1);
  });

  it("excludes the target node from results", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { findSimilar, similarNodes } = useFindSimilar(nodes, edges);
    findSimilar("1");
    expect(similarNodes.value.some((s) => s.node.id === "1")).toBe(false);
  });

  it("clear resets similarNodes", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { findSimilar, clear, similarNodes } = useFindSimilar(nodes, edges);
    findSimilar("1");
    expect(similarNodes.value.length).toBeGreaterThan(0);
    clear();
    expect(similarNodes.value).toEqual([]);
  });

  it("handles node with no connections", () => {
    const nodes = ref([...mockNodes, createMockNode("isolated", "Isolated", "author")]);
    const edges = ref(mockEdges);
    const { findSimilar, similarNodes } = useFindSimilar(nodes, edges);
    findSimilar("isolated");
    expect(similarNodes.value).toEqual([]);
  });

  it("exposes hasSimilarNodes computed property", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { findSimilar, clear, hasSimilarNodes } = useFindSimilar(nodes, edges);

    expect(hasSimilarNodes.value).toBe(false);
    findSimilar("1");
    expect(hasSimilarNodes.value).toBe(true);
    clear();
    expect(hasSimilarNodes.value).toBe(false);
  });

  it("exposes similarCount computed property", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { findSimilar, similarCount } = useFindSimilar(nodes, edges);

    expect(similarCount.value).toBe(0);
    findSimilar("1");
    expect(similarCount.value).toBeGreaterThan(0);
  });

  it("tracks currentTargetId", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { findSimilar, clear, currentTargetId } = useFindSimilar(nodes, edges);

    expect(currentTargetId.value).toBeNull();
    findSimilar("1");
    expect(currentTargetId.value).toBe("1");
    findSimilar("2");
    expect(currentTargetId.value).toBe("2");
    clear();
    expect(currentTargetId.value).toBeNull();
  });
});
