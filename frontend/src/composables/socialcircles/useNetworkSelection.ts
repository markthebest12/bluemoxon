/**
 * useNetworkSelection - Manages node/edge selection and highlighting.
 * Enhanced with toggle behavior: clicking same item closes panel but keeps highlight.
 */

import { ref, computed, readonly } from "vue";
import type { NodeId, EdgeId, SelectionState, ApiNode, ApiEdge } from "@/types/socialCircles";
import { DEFAULT_SELECTION_STATE } from "@/types/socialCircles";

export function useNetworkSelection() {
  const selection = ref<SelectionState>({ ...DEFAULT_SELECTION_STATE });
  const isPanelOpen = ref(false);

  // Store nodes and edges for lookup
  const nodesMap = ref<Map<NodeId, ApiNode>>(new Map());
  const edgesMap = ref<Map<EdgeId, ApiEdge>>(new Map());

  // Computed
  const selectedNode = computed(() => {
    const id = selection.value.selectedNodeId;
    return id ? nodesMap.value.get(id) || null : null;
  });

  const selectedEdge = computed(() => {
    const id = selection.value.selectedEdgeId;
    return id ? edgesMap.value.get(id) || null : null;
  });

  const isNodeSelected = computed(() => selection.value.selectedNodeId !== null);
  const isEdgeSelected = computed(() => selection.value.selectedEdgeId !== null);

  // Computed arrays for highlighted elements (ensures proper reactivity)
  const highlightedNodeIds = computed(() => Array.from(selection.value.highlightedNodeIds));
  const highlightedEdgeIds = computed(() => Array.from(selection.value.highlightedEdgeIds));

  // Actions
  function setNodesAndEdges(nodes: ApiNode[], edges: ApiEdge[]) {
    nodesMap.value.clear();
    edgesMap.value.clear();
    nodes.forEach((n) => nodesMap.value.set(n.id, n));
    edges.forEach((e) => edgesMap.value.set(e.id, e));
  }

  function updateHighlightsForNode(nodeId: NodeId) {
    const connectedNodeIds = new Set<NodeId>();
    const connectedEdgeIds = new Set<EdgeId>();

    edgesMap.value.forEach((edge, edgeId) => {
      if (edge.source === nodeId || edge.target === nodeId) {
        connectedEdgeIds.add(edgeId);
        connectedNodeIds.add(edge.source as NodeId);
        connectedNodeIds.add(edge.target as NodeId);
      }
    });

    selection.value.highlightedNodeIds = connectedNodeIds;
    selection.value.highlightedEdgeIds = connectedEdgeIds;
  }

  function selectNode(nodeId: NodeId | null) {
    selection.value.selectedEdgeId = null; // Clear edge selection

    if (nodeId) {
      selection.value.selectedNodeId = nodeId;
      updateHighlightsForNode(nodeId);
      isPanelOpen.value = true;
    } else {
      selection.value.selectedNodeId = null;
      selection.value.highlightedNodeIds = new Set();
      selection.value.highlightedEdgeIds = new Set();
      isPanelOpen.value = false;
    }
  }

  /**
   * Toggle selection: if same node clicked, close panel but keep highlight.
   * If different node, switch selection and open panel.
   */
  function toggleSelectNode(nodeId: NodeId) {
    if (selection.value.selectedNodeId === nodeId) {
      // Same node - toggle panel open/closed, keep highlight
      isPanelOpen.value = !isPanelOpen.value;
    } else {
      // Different node - switch selection and open
      selectNode(nodeId);
    }
  }

  function selectEdge(edgeId: EdgeId | null) {
    selection.value.selectedNodeId = null; // Clear node selection

    if (edgeId) {
      const edge = edgesMap.value.get(edgeId);
      if (edge) {
        selection.value.selectedEdgeId = edgeId;
        const connectedNodeIds = new Set<NodeId>([edge.source as NodeId, edge.target as NodeId]);
        const connectedEdgeIds = new Set<EdgeId>([edgeId]);

        selection.value.highlightedNodeIds = connectedNodeIds;
        selection.value.highlightedEdgeIds = connectedEdgeIds;
        isPanelOpen.value = true;
      }
    } else {
      selection.value.selectedEdgeId = null;
      selection.value.highlightedNodeIds = new Set();
      selection.value.highlightedEdgeIds = new Set();
      isPanelOpen.value = false;
    }
  }

  /**
   * Toggle edge selection: if same edge clicked, close panel but keep highlight.
   */
  function toggleSelectEdge(edgeId: EdgeId) {
    if (selection.value.selectedEdgeId === edgeId) {
      isPanelOpen.value = !isPanelOpen.value;
    } else {
      selectEdge(edgeId);
    }
  }

  function clearSelection() {
    selection.value.selectedNodeId = null;
    selection.value.selectedEdgeId = null;
    selection.value.highlightedNodeIds = new Set();
    selection.value.highlightedEdgeIds = new Set();
    isPanelOpen.value = false;
  }

  /**
   * Close panel only (keep selection highlighted for reference).
   */
  function closePanel() {
    isPanelOpen.value = false;
  }

  function setHoveredNode(nodeId: NodeId | null) {
    selection.value.hoveredNodeId = nodeId;
  }

  function setHoveredEdge(edgeId: EdgeId | null) {
    selection.value.hoveredEdgeId = edgeId;
  }

  function isNodeHighlighted(nodeId: NodeId): boolean {
    return selection.value.highlightedNodeIds.has(nodeId);
  }

  function isEdgeHighlighted(edgeId: EdgeId): boolean {
    return selection.value.highlightedEdgeIds.has(edgeId);
  }

  return {
    selection: readonly(selection),
    isPanelOpen: readonly(isPanelOpen),
    selectedNode,
    selectedEdge,
    isNodeSelected,
    isEdgeSelected,
    highlightedNodeIds,
    highlightedEdgeIds,
    setNodesAndEdges,
    selectNode,
    toggleSelectNode,
    selectEdge,
    toggleSelectEdge,
    clearSelection,
    closePanel,
    setHoveredNode,
    setHoveredEdge,
    isNodeHighlighted,
    isEdgeHighlighted,
  };
}
