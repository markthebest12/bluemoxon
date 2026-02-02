/**
 * useHubMode - Progressive disclosure for social circles landing.
 *
 * Shows top N nodes by connection count (with type diversity),
 * supports expand-in-place and "show more" level transitions.
 */

import { computed, ref, type Ref } from "vue";
import type { ApiNode, ApiEdge, NodeId } from "@/types/socialCircles";

type HubLevel = "compact" | "medium" | "full";

const HUB_COUNTS: Record<HubLevel, number | null> = {
  compact: 25,
  medium: 50,
  full: null, // show all
};

// Type diversity ratio (proportional allocation)
const TYPE_RATIOS: Record<string, number> = {
  author: 0.6,
  publisher: 0.32,
  binder: 0.08,
};

const EXPAND_BATCH_SIZE = 10;

export function useHubMode(allNodes: Ref<ApiNode[]>, allEdges: Ref<ApiEdge[]>) {
  const hubLevel = ref<HubLevel>("compact");
  const expandedNodes = ref(new Set<NodeId>());
  const manuallyAddedNodes = ref(new Set<NodeId>());

  // Precompute edge count per node for hub ranking
  const edgeCountMap = computed(() => {
    const counts = new Map<NodeId, number>();
    for (const edge of allEdges.value) {
      counts.set(edge.source, (counts.get(edge.source) ?? 0) + 1);
      counts.set(edge.target, (counts.get(edge.target) ?? 0) + 1);
    }
    return counts;
  });

  // Select top N hubs with type diversity
  function selectHubs(count: number): Set<NodeId> {
    const byType = new Map<string, ApiNode[]>();
    for (const node of allNodes.value) {
      const list = byType.get(node.type) ?? [];
      list.push(node);
      byType.set(node.type, list);
    }

    // Sort each type by edge count descending
    const edgeCounts = edgeCountMap.value;
    for (const [, list] of byType) {
      list.sort((a, b) => (edgeCounts.get(b.id) ?? 0) - (edgeCounts.get(a.id) ?? 0));
    }

    const selected = new Set<NodeId>();

    // First pass: allocate by ratio
    for (const [type, ratio] of Object.entries(TYPE_RATIOS)) {
      const available = byType.get(type) ?? [];
      const quota = Math.round(count * ratio);
      for (let i = 0; i < Math.min(quota, available.length); i++) {
        selected.add(available[i].id);
      }
    }

    // Second pass: fill remaining slots from any type (by edge count)
    if (selected.size < count) {
      const allSorted = [...allNodes.value].sort(
        (a, b) => (edgeCounts.get(b.id) ?? 0) - (edgeCounts.get(a.id) ?? 0)
      );
      for (const node of allSorted) {
        if (selected.size >= count) break;
        selected.add(node.id);
      }
    }

    return selected;
  }

  // Hub node IDs based on current level
  const hubNodeIds = computed(() => {
    const limit = HUB_COUNTS[hubLevel.value];
    if (limit === null) {
      return new Set(allNodes.value.map((n) => n.id));
    }
    return selectHubs(limit);
  });

  // All visible node IDs = hubs + manually expanded
  const visibleNodeIds = computed(() => {
    const ids = new Set(hubNodeIds.value);
    for (const id of manuallyAddedNodes.value) {
      ids.add(id);
    }
    return ids;
  });

  // Visible nodes and edges
  const visibleNodes = computed(() => allNodes.value.filter((n) => visibleNodeIds.value.has(n.id)));

  const visibleEdges = computed(() =>
    allEdges.value.filter(
      (e) => visibleNodeIds.value.has(e.source) && visibleNodeIds.value.has(e.target)
    )
  );

  // Expand a node's neighborhood
  function expandNode(nodeId: NodeId) {
    const neighbors = allEdges.value
      .filter((e) => e.source === nodeId || e.target === nodeId)
      .map((e) => ({
        nodeId: e.source === nodeId ? e.target : e.source,
        strength: e.strength,
      }))
      .filter((n) => !visibleNodeIds.value.has(n.nodeId))
      .sort((a, b) => b.strength - a.strength)
      .slice(0, EXPAND_BATCH_SIZE);

    for (const n of neighbors) {
      manuallyAddedNodes.value.add(n.nodeId);
    }
    expandedNodes.value.add(nodeId);

    // Trigger reactivity
    manuallyAddedNodes.value = new Set(manuallyAddedNodes.value);
    expandedNodes.value = new Set(expandedNodes.value);
  }

  // Expand next batch for a node ("+N more")
  function expandMore(nodeId: NodeId) {
    expandNode(nodeId);
  }

  // Count hidden neighbors for "+N more" badge
  function hiddenNeighborCount(nodeId: NodeId): number {
    return allEdges.value
      .filter((e) => e.source === nodeId || e.target === nodeId)
      .map((e) => (e.source === nodeId ? e.target : e.source))
      .filter((id) => !visibleNodeIds.value.has(id)).length;
  }

  // Pre-computed map of hidden neighbor counts for all visible nodes — O(E) single pass
  const hiddenNeighborCounts = computed(() => {
    const counts = new Map<NodeId, number>();
    if (hubLevel.value === "full") return counts;
    const visible = visibleNodeIds.value;
    for (const edge of allEdges.value) {
      const srcVisible = visible.has(edge.source);
      const tgtVisible = visible.has(edge.target);
      if (srcVisible && !tgtVisible) {
        counts.set(edge.source, (counts.get(edge.source) ?? 0) + 1);
      }
      if (tgtVisible && !srcVisible) {
        counts.set(edge.target, (counts.get(edge.target) ?? 0) + 1);
      }
    }
    return counts;
  });

  function isExpanded(nodeId: NodeId): boolean {
    return expandedNodes.value.has(nodeId);
  }

  // "Show more" level transition
  function showMore() {
    if (hubLevel.value === "compact") {
      hubLevel.value = "medium";
    } else if (hubLevel.value === "medium") {
      hubLevel.value = "full";
    }
  }

  // "Show less" level transition (deterministic reversal)
  function showLess() {
    if (hubLevel.value === "full") {
      hubLevel.value = "medium";
    } else if (hubLevel.value === "medium") {
      hubLevel.value = "compact";
    }
    // Clear manually expanded nodes so user gets the exact hub set for this level
    manuallyAddedNodes.value = new Set();
    expandedNodes.value = new Set();
  }

  // Initialize (called on mount)
  function initializeHubs() {
    hubLevel.value = "compact";
    expandedNodes.value = new Set();
    manuallyAddedNodes.value = new Set();
  }

  // Status text for "Show more" button
  const statusText = computed(() => {
    const visible = visibleNodes.value.length;
    const total = allNodes.value.length;
    if (hubLevel.value === "full" && manuallyAddedNodes.value.size === 0) return null;
    return `Showing ${visible} of ${total}`;
  });

  const isFullyExpanded = computed(() => hubLevel.value === "full");

  const canShowLess = computed(() => hubLevel.value !== "compact");

  return {
    // State
    hubLevel,
    visibleNodes,
    visibleEdges,
    visibleNodeIds,
    statusText,
    isFullyExpanded,
    canShowLess,

    // Actions
    initializeHubs,
    expandNode,
    expandMore,
    showMore,
    showLess,
    hiddenNeighborCount,
    hiddenNeighborCounts,
    isExpanded,
  };
}
