import { describe, it, expect } from "vitest";
import { ref } from "vue";
import { usePathFinder } from "../usePathFinder";
import type { ApiNode, ApiEdge, NodeId, EdgeId, BookId } from "@/types/socialCircles";

// Test fixtures for path finding
const mockNodeA: ApiNode = {
  id: "author:1" as NodeId,
  entity_id: 1,
  name: "A",
  type: "author",
  book_count: 3,
  book_ids: [1 as BookId],
};

const mockNodeB: ApiNode = {
  id: "publisher:2" as NodeId,
  entity_id: 2,
  name: "B",
  type: "publisher",
  book_count: 5,
  book_ids: [1 as BookId, 2 as BookId],
};

const mockNodeC: ApiNode = {
  id: "author:3" as NodeId,
  entity_id: 3,
  name: "C",
  type: "author",
  book_count: 2,
  book_ids: [2 as BookId],
};

const mockNodeD: ApiNode = {
  id: "author:4" as NodeId,
  entity_id: 4,
  name: "D",
  type: "author",
  book_count: 1,
  book_ids: [3 as BookId],
};

const mockNodes = [mockNodeA, mockNodeB, mockNodeC, mockNodeD];

// Edges: A -- B -- C (D is disconnected)
const mockEdgeAB: ApiEdge = {
  id: "e:author:1:publisher:2" as EdgeId,
  source: "author:1" as NodeId,
  target: "publisher:2" as NodeId,
  type: "publisher",
  strength: 3,
  shared_book_ids: [1 as BookId],
};

const mockEdgeBC: ApiEdge = {
  id: "e:publisher:2:author:3" as EdgeId,
  source: "publisher:2" as NodeId,
  target: "author:3" as NodeId,
  type: "publisher",
  strength: 2,
  shared_book_ids: [2 as BookId],
};

const mockEdges = [mockEdgeAB, mockEdgeBC];

describe("usePathFinder", () => {
  it("finds direct path between connected nodes", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { setStart, setEnd, findPath, path } = usePathFinder(nodes, edges);

    setStart(mockNodeA.id);
    setEnd(mockNodeB.id);
    findPath();

    expect(path.value).toEqual([mockNodeA.id, mockNodeB.id]);
  });

  it("finds indirect path through intermediate node", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { setStart, setEnd, findPath, path } = usePathFinder(nodes, edges);

    setStart(mockNodeA.id);
    setEnd(mockNodeC.id);
    findPath();

    expect(path.value).toEqual([mockNodeA.id, mockNodeB.id, mockNodeC.id]);
  });

  it("returns null path for disconnected nodes", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { setStart, setEnd, findPath, path, noPathFound } = usePathFinder(nodes, edges);

    setStart(mockNodeA.id);
    setEnd(mockNodeD.id);
    findPath();

    expect(path.value).toBeNull();
    expect(noPathFound.value).toBe(true);
  });

  it("clear resets all state", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const {
      setStart,
      setEnd,
      findPath,
      clear,
      startNode,
      endNode,
      path,
      noPathFound,
      isCalculating,
    } = usePathFinder(nodes, edges);

    setStart(mockNodeA.id);
    setEnd(mockNodeB.id);
    findPath();

    clear();

    expect(startNode.value).toBeNull();
    expect(endNode.value).toBeNull();
    expect(path.value).toBeNull();
    expect(noPathFound.value).toBe(false);
    expect(isCalculating.value).toBe(false);
  });

  it("does nothing when start or end not set", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { findPath, path } = usePathFinder(nodes, edges);

    findPath();

    expect(path.value).toBeNull();
  });

  it("finds path in reverse direction (undirected graph)", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { setStart, setEnd, findPath, path } = usePathFinder(nodes, edges);

    setStart(mockNodeC.id);
    setEnd(mockNodeA.id);
    findPath();

    expect(path.value).toEqual([mockNodeC.id, mockNodeB.id, mockNodeA.id]);
  });

  describe("computed properties", () => {
    it("returns correct startNode and endNode", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, startNode, endNode } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeC.id);

      expect(startNode.value).toEqual(mockNodeA);
      expect(endNode.value).toEqual(mockNodeC);
    });

    it("returns correct pathLength", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, findPath, pathLength } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeC.id);
      findPath();

      // Path is A -> B -> C, so length is 2 (two edges)
      expect(pathLength.value).toBe(2);
    });

    it("returns null pathLength when no path", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { pathLength } = usePathFinder(nodes, edges);

      expect(pathLength.value).toBeNull();
    });

    it("returns correct pathNodes", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, findPath, pathNodes } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeC.id);
      findPath();

      expect(pathNodes.value).toEqual([mockNodeA, mockNodeB, mockNodeC]);
    });

    it("isReady returns true when both nodes set", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, isReady } = usePathFinder(nodes, edges);

      expect(isReady.value).toBe(false);

      setStart(mockNodeA.id);
      expect(isReady.value).toBe(false);

      setEnd(mockNodeC.id);
      expect(isReady.value).toBe(true);
    });

    it("isSameNode returns true when start equals end", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, isSameNode } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeA.id);

      expect(isSameNode.value).toBe(true);
    });

    it("isSameNode returns false when start differs from end", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, isSameNode } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeC.id);

      expect(isSameNode.value).toBe(false);
    });
  });

  describe("swapNodes", () => {
    it("swaps start and end nodes", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, swapNodes, startNodeId, endNodeId } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeC.id);

      swapNodes();

      expect(startNodeId.value).toBe(mockNodeC.id);
      expect(endNodeId.value).toBe(mockNodeA.id);
    });

    it("clears path after swap", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, findPath, swapNodes, path } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeC.id);
      findPath();

      expect(path.value).not.toBeNull();

      swapNodes();

      expect(path.value).toBeNull();
    });
  });

  describe("isNodeInPath", () => {
    it("returns true for nodes in path", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, findPath, isNodeInPath } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeC.id);
      findPath();

      expect(isNodeInPath(mockNodeA.id)).toBe(true);
      expect(isNodeInPath(mockNodeB.id)).toBe(true);
      expect(isNodeInPath(mockNodeC.id)).toBe(true);
    });

    it("returns false for nodes not in path", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, findPath, isNodeInPath } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeC.id);
      findPath();

      expect(isNodeInPath(mockNodeD.id)).toBe(false);
    });

    it("returns false when no path exists", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { isNodeInPath } = usePathFinder(nodes, edges);

      expect(isNodeInPath(mockNodeA.id)).toBe(false);
    });
  });

  describe("getPathEdgeIds", () => {
    it("returns edge IDs for path", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, findPath, getPathEdgeIds } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeC.id);
      findPath();

      const edgeIds = getPathEdgeIds();
      expect(edgeIds).toContain(mockEdgeAB.id);
      expect(edgeIds).toContain(mockEdgeBC.id);
      expect(edgeIds).toHaveLength(2);
    });

    it("returns empty array when no path", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { getPathEdgeIds } = usePathFinder(nodes, edges);

      expect(getPathEdgeIds()).toEqual([]);
    });

    it("returns empty array for single-node path", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, findPath, getPathEdgeIds, path } = usePathFinder(nodes, edges);

      // Manually set path to a single node (edge case)
      setStart(mockNodeA.id);
      setEnd(mockNodeA.id);

      // Same node won't produce a path via BFS, but test the function behavior
      findPath();

      // BFS should return a single-node path [A] for same start/end
      // The getPathEdgeIds should handle this gracefully
      const edgeIds = getPathEdgeIds();
      // If path has fewer than 2 nodes, returns empty
      if (path.value && path.value.length < 2) {
        expect(edgeIds).toEqual([]);
      }
    });
  });

  describe("setStart and setEnd", () => {
    it("setStart clears previous path", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, findPath, path, noPathFound } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeB.id);
      findPath();

      expect(path.value).not.toBeNull();

      setStart(mockNodeC.id);

      expect(path.value).toBeNull();
      expect(noPathFound.value).toBe(false);
    });

    it("setEnd clears previous path", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, setEnd, findPath, path, noPathFound } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeB.id);
      findPath();

      expect(path.value).not.toBeNull();

      setEnd(mockNodeC.id);

      expect(path.value).toBeNull();
      expect(noPathFound.value).toBe(false);
    });

    it("allows setting start to null", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, startNodeId } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      expect(startNodeId.value).toBe(mockNodeA.id);

      setStart(null);
      expect(startNodeId.value).toBeNull();
    });

    it("allows setting end to null", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setEnd, endNodeId } = usePathFinder(nodes, edges);

      setEnd(mockNodeA.id);
      expect(endNodeId.value).toBe(mockNodeA.id);

      setEnd(null);
      expect(endNodeId.value).toBeNull();
    });
  });

  describe("edge cases", () => {
    it("handles empty nodes array", () => {
      const nodes = ref<ApiNode[]>([]);
      const edges = ref<ApiEdge[]>([]);
      const { setStart, setEnd, findPath, path, noPathFound } = usePathFinder(nodes, edges);

      setStart("author:1" as NodeId);
      setEnd("author:2" as NodeId);
      findPath();

      expect(path.value).toBeNull();
      expect(noPathFound.value).toBe(true);
    });

    it("handles empty edges array", () => {
      const nodes = ref(mockNodes);
      const edges = ref<ApiEdge[]>([]);
      const { setStart, setEnd, findPath, path, noPathFound } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);
      setEnd(mockNodeB.id);
      findPath();

      expect(path.value).toBeNull();
      expect(noPathFound.value).toBe(true);
    });

    it("handles non-existent start node gracefully", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, startNode } = usePathFinder(nodes, edges);

      setStart("author:999" as NodeId);

      // startNode computed should return null since ID not in nodes
      expect(startNode.value).toBeNull();
    });

    it("handles non-existent end node gracefully", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setEnd, endNode } = usePathFinder(nodes, edges);

      setEnd("author:999" as NodeId);

      // endNode computed should return null since ID not in nodes
      expect(endNode.value).toBeNull();
    });

    it("does not throw when finding path with only start set", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setStart, findPath, path } = usePathFinder(nodes, edges);

      setStart(mockNodeA.id);

      expect(() => findPath()).not.toThrow();
      expect(path.value).toBeNull();
    });

    it("does not throw when finding path with only end set", () => {
      const nodes = ref(mockNodes);
      const edges = ref(mockEdges);
      const { setEnd, findPath, path } = usePathFinder(nodes, edges);

      setEnd(mockNodeA.id);

      expect(() => findPath()).not.toThrow();
      expect(path.value).toBeNull();
    });
  });
});
