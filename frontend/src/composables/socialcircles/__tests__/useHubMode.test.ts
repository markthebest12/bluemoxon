import { describe, it, expect } from "vitest";
import { ref } from "vue";
import { useHubMode } from "../useHubMode";
import type { ApiNode, ApiEdge, NodeId, EdgeId, BookId } from "@/types/socialCircles";

function makeNode(id: string, type: "author" | "publisher" | "binder", edgeCount = 0): ApiNode {
  return {
    id: id as NodeId,
    entity_id: parseInt(id.split(":")[1]),
    name: `Node ${id}`,
    type,
    book_count: 1,
    book_ids: [1 as BookId],
  };
}

function makeEdge(source: string, target: string, strength = 5): ApiEdge {
  return {
    id: `e:${source}:${target}` as EdgeId,
    source: source as NodeId,
    target: target as NodeId,
    type: "publisher",
    strength,
  };
}

describe("useHubMode", () => {
  it("selects top nodes by type with diversity ratio", () => {
    const nodes = ref<ApiNode[]>([
      // 20 authors, 10 publishers, 5 binders
      ...Array.from({ length: 20 }, (_, i) => makeNode(`author:${i}`, "author")),
      ...Array.from({ length: 10 }, (_, i) => makeNode(`publisher:${i}`, "publisher")),
      ...Array.from({ length: 5 }, (_, i) => makeNode(`binder:${i}`, "binder")),
    ]);
    const edges = ref<ApiEdge[]>(
      // Give each node varying edge counts by creating edges
      Array.from({ length: 20 }, (_, i) =>
        makeEdge(`author:${i}`, `publisher:${i % 10}`, 10 - (i % 10)),
      ),
    );

    const hub = useHubMode(nodes, edges);
    const visible = hub.visibleNodes.value;

    // Should have at most 25 nodes
    expect(visible.length).toBeLessThanOrEqual(25);
    // Should include authors, publishers, and binders
    expect(visible.some((n) => n.type === "author")).toBe(true);
    expect(visible.some((n) => n.type === "publisher")).toBe(true);
  });

  it("expands a node adding up to 10 neighbors", () => {
    const hub_node = makeNode("author:0", "author");
    // 25 publisher neighbors — enough that some stay hidden at compact level
    const neighbors = Array.from({ length: 25 }, (_, i) =>
      makeNode(`publisher:${i}`, "publisher"),
    );
    // Extra authors to fill hub slots
    const extraAuthors = Array.from({ length: 20 }, (_, i) =>
      makeNode(`author:${i + 1}`, "author"),
    );
    const nodes = ref<ApiNode[]>([hub_node, ...neighbors, ...extraAuthors]);
    const edges = ref<ApiEdge[]>(
      neighbors.map((n, i) => makeEdge("author:0", n.id, 25 - i)),
    );

    const hub = useHubMode(nodes, edges);
    // Start with hub visible
    hub.initializeHubs();

    const beforeCount = hub.visibleNodes.value.length;
    hub.expandNode("author:0" as NodeId);
    const afterCount = hub.visibleNodes.value.length;

    // Should add up to 10 neighbors
    expect(afterCount - beforeCount).toBeLessThanOrEqual(10);
    expect(afterCount).toBeGreaterThan(beforeCount);
    expect(hub.isExpanded("author:0" as NodeId)).toBe(true);
  });

  it("reports remaining hidden neighbors count", () => {
    const hub_node = makeNode("author:0", "author");
    // 25 publisher neighbors so some remain hidden after hub selection + expand
    const neighbors = Array.from({ length: 25 }, (_, i) =>
      makeNode(`publisher:${i}`, "publisher"),
    );
    // 20 extra authors to fill hub slots (so not all publishers become hubs)
    const extraAuthors = Array.from({ length: 20 }, (_, i) =>
      makeNode(`author:${i + 1}`, "author"),
    );
    const nodes = ref<ApiNode[]>([hub_node, ...neighbors, ...extraAuthors]);
    const edges = ref<ApiEdge[]>(
      neighbors.map((n, i) => makeEdge("author:0", n.id, 25 - i)),
    );

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();

    // Some publishers should be hidden (not selected as hubs)
    const hiddenBefore = hub.hiddenNeighborCount("author:0" as NodeId);
    expect(hiddenBefore).toBeGreaterThan(10); // more than EXPAND_BATCH_SIZE

    hub.expandNode("author:0" as NodeId);

    // After expanding 10, some should still be hidden
    const remaining = hub.hiddenNeighborCount("author:0" as NodeId);
    expect(remaining).toBe(hiddenBefore - 10); // expanded 10 of the hidden ones
  });

  it("transitions hub levels: compact → medium → full", () => {
    const nodes = ref<ApiNode[]>(
      Array.from({ length: 100 }, (_, i) => makeNode(`author:${i}`, "author")),
    );
    const edges = ref<ApiEdge[]>([]);

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();

    expect(hub.hubLevel.value).toBe("compact");
    expect(hub.visibleNodes.value.length).toBeLessThanOrEqual(25);

    hub.showMore();
    expect(hub.hubLevel.value).toBe("medium");
    expect(hub.visibleNodes.value.length).toBeLessThanOrEqual(50);

    hub.showMore();
    expect(hub.hubLevel.value).toBe("full");
    expect(hub.visibleNodes.value.length).toBe(100);
  });

  it("does not duplicate already-visible nodes on expand", () => {
    const nodes = ref<ApiNode[]>([
      makeNode("author:0", "author"),
      makeNode("author:1", "author"),
      makeNode("publisher:0", "publisher"),
    ]);
    const edges = ref<ApiEdge[]>([
      makeEdge("author:0", "publisher:0"),
      makeEdge("author:1", "publisher:0"),
    ]);

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();

    // Both authors and publisher should be hubs in a 3-node graph
    const before = hub.visibleNodes.value.length;
    hub.expandNode("author:0" as NodeId);
    const after = hub.visibleNodes.value.length;

    // publisher:0 was already visible — no duplicate
    expect(after).toBe(before);
  });

  it("edges are filtered to only visible endpoints", () => {
    const nodes = ref<ApiNode[]>([
      makeNode("author:0", "author"),
      makeNode("publisher:0", "publisher"),
      makeNode("publisher:1", "publisher"),
    ]);
    const edges = ref<ApiEdge[]>([
      makeEdge("author:0", "publisher:0"),
      makeEdge("author:0", "publisher:1"),
    ]);

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();

    // Only edges where both endpoints are visible should appear
    for (const edge of hub.visibleEdges.value) {
      const nodeIds = new Set(hub.visibleNodes.value.map((n) => n.id));
      expect(nodeIds.has(edge.source)).toBe(true);
      expect(nodeIds.has(edge.target)).toBe(true);
    }
  });
});
