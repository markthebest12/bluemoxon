/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck - Test mocks don't need full type compliance
import { describe, it, expect } from "vitest";
import { ref } from "vue";
import { useNetworkStats } from "../useNetworkStats";

const mockNodes = [
  { id: "1", name: "Author 1", type: "author" },
  { id: "2", name: "Author 2", type: "author" },
  { id: "3", name: "Publisher 1", type: "publisher", book_count: 10 },
  { id: "4", name: "Binder 1", type: "binder" },
];

const mockEdges = [
  { source: "1", target: "3" },
  { source: "2", target: "3" },
  { source: "1", target: "4" },
];

describe("useNetworkStats", () => {
  it("counts total nodes correctly", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { stats } = useNetworkStats(nodes, edges);
    expect(stats.value.totalNodes).toBe(4);
  });

  it("counts total edges correctly", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { stats } = useNetworkStats(nodes, edges);
    expect(stats.value.totalEdges).toBe(3);
  });

  it("counts nodes by type", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { stats } = useNetworkStats(nodes, edges);
    expect(stats.value.nodesByType.author).toBe(2);
    expect(stats.value.nodesByType.publisher).toBe(1);
    expect(stats.value.nodesByType.binder).toBe(1);
  });

  it("finds most connected node", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { stats } = useNetworkStats(nodes, edges);
    // Node 1 has 2 connections, Node 3 has 2 connections
    expect(stats.value.mostConnected?.degree).toBe(2);
  });

  it("calculates average degree", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { stats } = useNetworkStats(nodes, edges);
    // avgDegree = 2 * edges / nodes = 6/4 = 1.5
    expect(stats.value.avgDegree).toBe(1.5);
  });

  it("handles empty graph", () => {
    const nodes = ref([]);
    const edges = ref([]);
    const { stats } = useNetworkStats(nodes, edges);
    expect(stats.value.totalNodes).toBe(0);
    expect(stats.value.totalEdges).toBe(0);
    expect(stats.value.mostConnected).toBeNull();
  });

  it("updates when nodes change", () => {
    const nodes = ref(mockNodes);
    const edges = ref(mockEdges);
    const { stats } = useNetworkStats(nodes, edges);
    expect(stats.value.totalNodes).toBe(4);
    nodes.value = [...nodes.value, { id: "5", name: "New", type: "author" }];
    expect(stats.value.totalNodes).toBe(5);
  });
});
