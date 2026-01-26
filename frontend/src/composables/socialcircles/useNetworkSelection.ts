/**
 * useNetworkSelection - Manages node/edge selection and highlighting.
 */

import { ref, computed, readonly } from "vue";
import type { NodeId, EdgeId, SelectionState, ApiNode, ApiEdge } from "@/types/socialCircles";
import { DEFAULT_SELECTION_STATE } from "@/types/socialCircles";

export function useNetworkSelection() {
  const selection = ref<SelectionState>({ ...DEFAULT_SELECTION_STATE });

  // Store nodes and edges for lookup
  const nodesMap = ref<Map<NodeId, ApiNode>>(new Map());
  const edgesMap = ref<Map<EdgeId, ApiEdge>>(new Map());

  // Computed
  const selectedNode = computed(() => {
    const id = selection.value.selectedNodeId;
    return id ? nodesMap.value.get(id) || null : null;
  });

  const isNodeSelected = computed(() => selection.value.selectedNodeId !== null);

  // Actions
  function setNodesAndEdges(nodes: ApiNode[], edges: ApiEdge[]) {
    nodesMap.value.clear();
    edgesMap.value.clear();
    nodes.forEach((n) => nodesMap.value.set(n.id, n));
    edges.forEach((e) => edgesMap.value.set(e.id, e));
  }

  function selectNode(nodeId: NodeId | null) {
    selection.value.selectedNodeId = nodeId;

    if (nodeId) {
      // Find connected nodes and edges
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
    } else {
      selection.value.highlightedNodeIds = new Set();
      selection.value.highlightedEdgeIds = new Set();
    }
  }

  function clearSelection() {
    selectNode(null);
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
    selectedNode,
    isNodeSelected,
    setNodesAndEdges,
    selectNode,
    clearSelection,
    setHoveredNode,
    setHoveredEdge,
    isNodeHighlighted,
    isEdgeHighlighted,
  };
}
