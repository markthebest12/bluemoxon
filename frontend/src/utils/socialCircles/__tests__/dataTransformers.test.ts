import { describe, it, expect } from "vitest";
import {
  transformNode,
  transformEdge,
  transformToCytoscapeElements,
  getVisibleElementIds,
} from "../dataTransformers";
import type {
  ApiNode,
  ApiEdge,
  SocialCirclesResponse,
  NodeId,
  EdgeId,
  BookId,
} from "@/types/socialCircles";

// Helper to create typed IDs
const nodeId = (id: string) => id as NodeId;
const edgeId = (id: string) => id as EdgeId;
const bookId = (id: number) => id as BookId;

describe("dataTransformers", () => {
  describe("transformNode", () => {
    it("transforms author node with era to cytoscape format", () => {
      const node: ApiNode = {
        id: nodeId("author:42"),
        entity_id: 42,
        name: "Charles Dickens",
        type: "author",
        birth_year: 1812,
        death_year: 1870,
        era: "victorian",
        book_count: 10,
        book_ids: [bookId(1), bookId(2), bookId(3)],
      };

      const result = transformNode(node);

      expect(result.group).toBe("nodes");
      expect(result.data.id).toBe("author:42");
      expect(result.data.name).toBe("Charles Dickens");
      expect(result.data.type).toBe("author");
      expect(result.data.nodeColor).toBe("#254a3d"); // victorian author color
      expect(result.data.nodeShape).toBe("ellipse"); // author shape
      expect(result.data.nodeSize).toBeGreaterThan(20); // base + book scaling
    });

    it("transforms publisher node with tier to cytoscape format", () => {
      const node: ApiNode = {
        id: nodeId("publisher:7"),
        entity_id: 7,
        name: "Chapman & Hall",
        type: "publisher",
        founded_year: 1830,
        tier: "TIER_1",
        book_count: 25,
        book_ids: [bookId(10), bookId(11)],
      };

      const result = transformNode(node);

      expect(result.group).toBe("nodes");
      expect(result.data.id).toBe("publisher:7");
      expect(result.data.name).toBe("Chapman & Hall");
      expect(result.data.type).toBe("publisher");
      expect(result.data.nodeColor).toBe("#d4af37"); // tier1 publisher color (gold-light)
      expect(result.data.nodeShape).toBe("rectangle"); // publisher shape
    });

    it("transforms binder node to cytoscape format", () => {
      const node: ApiNode = {
        id: nodeId("binder:99"),
        entity_id: 99,
        name: "Riviere & Son",
        type: "binder",
        tier: "TIER_1",
        book_count: 5,
        book_ids: [bookId(20)],
      };

      const result = transformNode(node);

      expect(result.group).toBe("nodes");
      expect(result.data.id).toBe("binder:99");
      expect(result.data.nodeColor).toBe("#5c262e"); // tier1 binder color (burgundy-dark)
      expect(result.data.nodeShape).toBe("diamond"); // binder shape
    });

    it("uses default color for author without era", () => {
      const node: ApiNode = {
        id: nodeId("author:100"),
        entity_id: 100,
        name: "Unknown Author",
        type: "author",
        book_count: 1,
        book_ids: [],
      };

      const result = transformNode(node);

      expect(result.data.nodeColor).toBe("#2f5a4b"); // author:default color
    });

    it("uses default color for publisher without tier", () => {
      const node: ApiNode = {
        id: nodeId("publisher:200"),
        entity_id: 200,
        name: "Small Press",
        type: "publisher",
        tier: null,
        book_count: 2,
        book_ids: [],
      };

      const result = transformNode(node);

      expect(result.data.nodeColor).toBe("#c9a227"); // publisher:default color (gold)
    });

    it("preserves all original node data in result", () => {
      const node: ApiNode = {
        id: nodeId("author:50"),
        entity_id: 50,
        name: "Jane Austen",
        type: "author",
        birth_year: 1775,
        death_year: 1817,
        era: "romantic",
        book_count: 6,
        book_ids: [bookId(100), bookId(101)],
      };

      const result = transformNode(node);

      expect(result.data.entity_id).toBe(50);
      expect(result.data.birth_year).toBe(1775);
      expect(result.data.death_year).toBe(1817);
      expect(result.data.era).toBe("romantic");
      expect(result.data.book_count).toBe(6);
      expect(result.data.book_ids).toEqual([bookId(100), bookId(101)]);
    });

    it("handles pre_romantic era author", () => {
      const node: ApiNode = {
        id: nodeId("author:1"),
        entity_id: 1,
        name: "Samuel Johnson",
        type: "author",
        era: "pre_romantic",
        book_count: 3,
        book_ids: [],
      };

      const result = transformNode(node);

      expect(result.data.nodeColor).toBe("#6b3a4a"); // pre_romantic author color
    });

    it("handles tier2 publisher", () => {
      const node: ApiNode = {
        id: nodeId("publisher:300"),
        entity_id: 300,
        name: "Regional Press",
        type: "publisher",
        tier: "TIER_2",
        book_count: 4,
        book_ids: [],
      };

      const result = transformNode(node);

      expect(result.data.nodeColor).toBe("#b8956e"); // publisher:tier2 color (gold-muted)
    });
  });

  describe("transformEdge", () => {
    it("transforms publisher edge to cytoscape format", () => {
      const edge: ApiEdge = {
        id: edgeId("e:author:42:publisher:7"),
        source: nodeId("author:42"),
        target: nodeId("publisher:7"),
        type: "publisher",
        strength: 5,
        shared_book_ids: [bookId(1), bookId(2)],
      };

      const result = transformEdge(edge);

      expect(result.group).toBe("edges");
      expect(result.data.id).toBe("e:author:42:publisher:7");
      expect(result.data.source).toBe("author:42");
      expect(result.data.target).toBe("publisher:7");
      expect(result.data.edgeColor).toBe("#4ade80"); // publisher edge color (green)
      expect(result.data.edgeStyle).toBe("solid");
      expect(result.data.edgeOpacity).toBe(0.8);
      expect(result.data.edgeWidth).toBeGreaterThan(1);
    });

    it("transforms shared_publisher edge to cytoscape format", () => {
      const edge: ApiEdge = {
        id: edgeId("e:author:1:author:2"),
        source: nodeId("author:1"),
        target: nodeId("author:2"),
        type: "shared_publisher",
        strength: 3,
      };

      const result = transformEdge(edge);

      expect(result.data.edgeColor).toBe("#4ade80"); // shared_publisher color (green)
      expect(result.data.edgeStyle).toBe("solid");
      expect(result.data.edgeOpacity).toBe(0.6);
    });

    it("transforms binder edge to cytoscape format", () => {
      const edge: ApiEdge = {
        id: edgeId("e:author:10:binder:20"),
        source: nodeId("author:10"),
        target: nodeId("binder:20"),
        type: "binder",
        strength: 2,
      };

      const result = transformEdge(edge);

      expect(result.data.edgeColor).toBe("#a78bfa"); // binder edge color (purple)
      expect(result.data.edgeStyle).toBe("dashed");
      expect(result.data.edgeOpacity).toBe(0.5);
    });

    it("calculates edge width based on strength", () => {
      const weakEdge: ApiEdge = {
        id: edgeId("e:a:1:b:2"),
        source: nodeId("a:1"),
        target: nodeId("b:2"),
        type: "publisher",
        strength: 1,
      };

      const strongEdge: ApiEdge = {
        id: edgeId("e:a:3:b:4"),
        source: nodeId("a:3"),
        target: nodeId("b:4"),
        type: "publisher",
        strength: 10,
      };

      const weakResult = transformEdge(weakEdge);
      const strongResult = transformEdge(strongEdge);

      expect(strongResult.data.edgeWidth).toBeGreaterThan(weakResult.data.edgeWidth);
    });

    it("preserves all original edge data in result", () => {
      const edge: ApiEdge = {
        id: edgeId("e:author:5:publisher:10"),
        source: nodeId("author:5"),
        target: nodeId("publisher:10"),
        type: "publisher",
        strength: 7,
        evidence: "Published 3 novels together",
        shared_book_ids: [bookId(50), bookId(51), bookId(52)],
        start_year: 1840,
        end_year: 1860,
      };

      const result = transformEdge(edge);

      expect(result.data.evidence).toBe("Published 3 novels together");
      expect(result.data.shared_book_ids).toEqual([bookId(50), bookId(51), bookId(52)]);
      expect(result.data.start_year).toBe(1840);
      expect(result.data.end_year).toBe(1860);
    });
  });

  describe("transformToCytoscapeElements", () => {
    it("transforms complete API response to cytoscape elements", () => {
      const response: SocialCirclesResponse = {
        nodes: [
          {
            id: nodeId("author:1"),
            entity_id: 1,
            name: "Author One",
            type: "author",
            era: "victorian",
            book_count: 5,
            book_ids: [],
          },
          {
            id: nodeId("publisher:2"),
            entity_id: 2,
            name: "Publisher Two",
            type: "publisher",
            tier: "TIER_1",
            book_count: 10,
            book_ids: [],
          },
        ],
        edges: [
          {
            id: edgeId("e:author:1:publisher:2"),
            source: nodeId("author:1"),
            target: nodeId("publisher:2"),
            type: "publisher",
            strength: 5,
          },
        ],
        meta: {
          total_books: 15,
          total_authors: 1,
          total_publishers: 1,
          total_binders: 0,
          date_range: [1840, 1900],
          generated_at: "2024-01-15T10:00:00Z",
          truncated: false,
        },
      };

      const result = transformToCytoscapeElements(response);

      expect(result).toHaveLength(3); // 2 nodes + 1 edge
      expect(result.filter((el) => el.group === "nodes")).toHaveLength(2);
      expect(result.filter((el) => el.group === "edges")).toHaveLength(1);
    });

    it("handles empty response", () => {
      const response: SocialCirclesResponse = {
        nodes: [],
        edges: [],
        meta: {
          total_books: 0,
          total_authors: 0,
          total_publishers: 0,
          total_binders: 0,
          date_range: [1800, 1900],
          generated_at: "2024-01-15T10:00:00Z",
          truncated: false,
        },
      };

      const result = transformToCytoscapeElements(response);

      expect(result).toEqual([]);
    });

    it("places nodes before edges in result array", () => {
      const response: SocialCirclesResponse = {
        nodes: [
          {
            id: nodeId("author:1"),
            entity_id: 1,
            name: "Test",
            type: "author",
            book_count: 1,
            book_ids: [],
          },
        ],
        edges: [
          {
            id: edgeId("e:author:1:author:2"),
            source: nodeId("author:1"),
            target: nodeId("author:2"),
            type: "shared_publisher",
            strength: 1,
          },
        ],
        meta: {
          total_books: 1,
          total_authors: 1,
          total_publishers: 0,
          total_binders: 0,
          date_range: [1850, 1850],
          generated_at: "2024-01-15T10:00:00Z",
          truncated: false,
        },
      };

      const result = transformToCytoscapeElements(response);

      // First element should be node, second should be edge
      expect(result[0].group).toBe("nodes");
      expect(result[1].group).toBe("edges");
    });

    it("transforms multiple nodes of different types", () => {
      const response: SocialCirclesResponse = {
        nodes: [
          {
            id: nodeId("author:1"),
            entity_id: 1,
            name: "A",
            type: "author",
            book_count: 1,
            book_ids: [],
          },
          {
            id: nodeId("publisher:2"),
            entity_id: 2,
            name: "P",
            type: "publisher",
            book_count: 2,
            book_ids: [],
          },
          {
            id: nodeId("binder:3"),
            entity_id: 3,
            name: "B",
            type: "binder",
            book_count: 3,
            book_ids: [],
          },
        ],
        edges: [],
        meta: {
          total_books: 6,
          total_authors: 1,
          total_publishers: 1,
          total_binders: 1,
          date_range: [1800, 1900],
          generated_at: "2024-01-15T10:00:00Z",
          truncated: false,
        },
      };

      const result = transformToCytoscapeElements(response);
      const nodeTypes = result.map((el) => el.data.type);

      expect(nodeTypes).toContain("author");
      expect(nodeTypes).toContain("publisher");
      expect(nodeTypes).toContain("binder");
    });
  });

  describe("getVisibleElementIds", () => {
    // Create a mock Cytoscape Core object
    function createMockCy(
      nodes: Array<{ id: string; type: string }>,
      edges: Array<{ id: string; type: string; sourceId: string; targetId: string }>
    ) {
      const mockNodes = nodes.map((n) => ({
        id: () => n.id,
        data: (key: string) => (key === "type" ? n.type : undefined),
      }));

      const mockEdges = edges.map((e) => ({
        id: () => e.id,
        data: (key: string) => (key === "type" ? e.type : undefined),
        source: () => ({ id: () => e.sourceId }),
        target: () => ({ id: () => e.targetId }),
      }));

      return {
        nodes: () => ({
          forEach: (cb: (node: (typeof mockNodes)[0]) => void) => mockNodes.forEach(cb),
        }),
        edges: () => ({
          forEach: (cb: (edge: (typeof mockEdges)[0]) => void) => mockEdges.forEach(cb),
        }),
      } as unknown as import("cytoscape").Core;
    }

    it("returns all node types when all filters enabled", () => {
      const cy = createMockCy(
        [
          { id: "author:1", type: "author" },
          { id: "publisher:2", type: "publisher" },
          { id: "binder:3", type: "binder" },
        ],
        []
      );

      const result = getVisibleElementIds(cy, true, true, true, [
        "publisher",
        "shared_publisher",
        "binder",
      ]);

      expect(result.nodeIds.has("author:1")).toBe(true);
      expect(result.nodeIds.has("publisher:2")).toBe(true);
      expect(result.nodeIds.has("binder:3")).toBe(true);
    });

    it("excludes authors when showAuthors is false", () => {
      const cy = createMockCy(
        [
          { id: "author:1", type: "author" },
          { id: "publisher:2", type: "publisher" },
        ],
        []
      );

      const result = getVisibleElementIds(cy, false, true, true, ["publisher"]);

      expect(result.nodeIds.has("author:1")).toBe(false);
      expect(result.nodeIds.has("publisher:2")).toBe(true);
    });

    it("excludes publishers when showPublishers is false", () => {
      const cy = createMockCy(
        [
          { id: "author:1", type: "author" },
          { id: "publisher:2", type: "publisher" },
        ],
        []
      );

      const result = getVisibleElementIds(cy, true, false, true, ["publisher"]);

      expect(result.nodeIds.has("author:1")).toBe(true);
      expect(result.nodeIds.has("publisher:2")).toBe(false);
    });

    it("excludes binders when showBinders is false", () => {
      const cy = createMockCy([{ id: "binder:1", type: "binder" }], []);

      const result = getVisibleElementIds(cy, true, true, false, ["binder"]);

      expect(result.nodeIds.has("binder:1")).toBe(false);
    });

    it("includes edges only when both endpoints are visible", () => {
      const cy = createMockCy(
        [
          { id: "author:1", type: "author" },
          { id: "publisher:2", type: "publisher" },
        ],
        [{ id: "e:1", type: "publisher", sourceId: "author:1", targetId: "publisher:2" }]
      );

      const result = getVisibleElementIds(cy, true, true, true, ["publisher"]);

      expect(result.edgeIds.has("e:1")).toBe(true);
    });

    it("excludes edges when source node is hidden", () => {
      const cy = createMockCy(
        [
          { id: "author:1", type: "author" },
          { id: "publisher:2", type: "publisher" },
        ],
        [{ id: "e:1", type: "publisher", sourceId: "author:1", targetId: "publisher:2" }]
      );

      const result = getVisibleElementIds(cy, false, true, true, ["publisher"]);

      expect(result.edgeIds.has("e:1")).toBe(false);
    });

    it("excludes edges when target node is hidden", () => {
      const cy = createMockCy(
        [
          { id: "author:1", type: "author" },
          { id: "publisher:2", type: "publisher" },
        ],
        [{ id: "e:1", type: "publisher", sourceId: "author:1", targetId: "publisher:2" }]
      );

      const result = getVisibleElementIds(cy, true, false, true, ["publisher"]);

      expect(result.edgeIds.has("e:1")).toBe(false);
    });

    it("excludes edges when connection type not in filter", () => {
      const cy = createMockCy(
        [
          { id: "author:1", type: "author" },
          { id: "publisher:2", type: "publisher" },
        ],
        [{ id: "e:1", type: "publisher", sourceId: "author:1", targetId: "publisher:2" }]
      );

      const result = getVisibleElementIds(cy, true, true, true, ["shared_publisher", "binder"]);

      expect(result.edgeIds.has("e:1")).toBe(false);
    });

    it("handles empty graph", () => {
      const cy = createMockCy([], []);

      const result = getVisibleElementIds(cy, true, true, true, ["publisher"]);

      expect(result.nodeIds.size).toBe(0);
      expect(result.edgeIds.size).toBe(0);
    });

    it("handles graph with no edges", () => {
      const cy = createMockCy(
        [
          { id: "author:1", type: "author" },
          { id: "author:2", type: "author" },
        ],
        []
      );

      const result = getVisibleElementIds(cy, true, true, true, ["publisher"]);

      expect(result.nodeIds.size).toBe(2);
      expect(result.edgeIds.size).toBe(0);
    });

    it("handles multiple edge types correctly", () => {
      const cy = createMockCy(
        [
          { id: "author:1", type: "author" },
          { id: "author:2", type: "author" },
          { id: "publisher:3", type: "publisher" },
        ],
        [
          { id: "e:1", type: "publisher", sourceId: "author:1", targetId: "publisher:3" },
          { id: "e:2", type: "shared_publisher", sourceId: "author:1", targetId: "author:2" },
          { id: "e:3", type: "binder", sourceId: "author:2", targetId: "publisher:3" },
        ]
      );

      // Only show publisher and shared_publisher edges
      const result = getVisibleElementIds(cy, true, true, true, ["publisher", "shared_publisher"]);

      expect(result.edgeIds.has("e:1")).toBe(true);
      expect(result.edgeIds.has("e:2")).toBe(true);
      expect(result.edgeIds.has("e:3")).toBe(false);
    });
  });
});
