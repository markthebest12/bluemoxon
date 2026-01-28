import { describe, it, expect, beforeEach } from "vitest";
import { useNetworkSelection } from "../useNetworkSelection";
import { mockNodes, mockEdges, mockAuthor1, mockPublisher1, mockEdge1 } from "./fixtures";
import type { NodeId, EdgeId } from "@/types/socialCircles";

describe("useNetworkSelection toggle behavior", () => {
  let selection: ReturnType<typeof useNetworkSelection>;

  beforeEach(() => {
    selection = useNetworkSelection();
    selection.setNodesAndEdges(mockNodes, mockEdges);
  });

  describe("isPanelOpen state", () => {
    it("starts with isPanelOpen as false", () => {
      expect(selection.isPanelOpen.value).toBe(false);
    });

    it("sets isPanelOpen to true when selecting a node", () => {
      selection.selectNode(mockAuthor1.id);
      expect(selection.isPanelOpen.value).toBe(true);
    });

    it("sets isPanelOpen to true when selecting an edge", () => {
      selection.selectEdge(mockEdge1.id);
      expect(selection.isPanelOpen.value).toBe(true);
    });
  });

  describe("toggleSelectNode", () => {
    it("closes panel but keeps highlight when clicking same node", () => {
      // Select node
      selection.selectNode(mockAuthor1.id);
      expect(selection.selection.value.selectedNodeId).toBe(mockAuthor1.id);
      expect(selection.isPanelOpen.value).toBe(true);

      // Toggle same node - panel closes, selection stays highlighted
      selection.toggleSelectNode(mockAuthor1.id);
      expect(selection.isPanelOpen.value).toBe(false);
      expect(selection.selection.value.selectedNodeId).toBe(mockAuthor1.id); // Still selected
      expect(selection.selection.value.highlightedNodeIds.size).toBeGreaterThan(0); // Still highlighted
    });

    it("opens panel when clicking same node again after toggle close", () => {
      selection.selectNode(mockAuthor1.id);
      selection.toggleSelectNode(mockAuthor1.id); // Close
      selection.toggleSelectNode(mockAuthor1.id); // Open again
      expect(selection.isPanelOpen.value).toBe(true);
    });

    it("switches selection and opens panel when clicking different node", () => {
      selection.selectNode(mockAuthor1.id);
      selection.toggleSelectNode(mockAuthor1.id); // Close panel

      // Toggle different node - should open and switch
      selection.toggleSelectNode(mockPublisher1.id);
      expect(selection.selection.value.selectedNodeId).toBe(mockPublisher1.id);
      expect(selection.isPanelOpen.value).toBe(true);
    });
  });

  describe("selectNode behavior with isPanelOpen", () => {
    it("always opens panel when using selectNode", () => {
      selection.selectNode(mockAuthor1.id);
      selection.toggleSelectNode(mockAuthor1.id); // Close panel

      // Select different node via selectNode - should always open
      selection.selectNode(mockPublisher1.id);
      expect(selection.selection.value.selectedNodeId).toBe(mockPublisher1.id);
      expect(selection.isPanelOpen.value).toBe(true);
    });

    it("closes panel when selecting null", () => {
      selection.selectNode(mockAuthor1.id);
      expect(selection.isPanelOpen.value).toBe(true);

      selection.selectNode(null);
      expect(selection.isPanelOpen.value).toBe(false);
      expect(selection.selection.value.selectedNodeId).toBeNull();
    });
  });

  describe("toggleSelectEdge", () => {
    it("closes panel but keeps highlight when clicking same edge", () => {
      selection.selectEdge(mockEdge1.id);
      expect(selection.selection.value.selectedEdgeId).toBe(mockEdge1.id);
      expect(selection.isPanelOpen.value).toBe(true);

      // Toggle same edge - panel closes, selection stays highlighted
      selection.toggleSelectEdge(mockEdge1.id);
      expect(selection.isPanelOpen.value).toBe(false);
      expect(selection.selection.value.selectedEdgeId).toBe(mockEdge1.id); // Still selected
      expect(selection.selection.value.highlightedEdgeIds.size).toBeGreaterThan(0);
    });

    it("opens panel when clicking same edge again after toggle close", () => {
      selection.selectEdge(mockEdge1.id);
      selection.toggleSelectEdge(mockEdge1.id); // Close
      selection.toggleSelectEdge(mockEdge1.id); // Open again
      expect(selection.isPanelOpen.value).toBe(true);
    });
  });

  describe("closePanel", () => {
    it("closes panel without clearing selection", () => {
      selection.selectNode(mockAuthor1.id);
      expect(selection.isPanelOpen.value).toBe(true);

      selection.closePanel();
      expect(selection.isPanelOpen.value).toBe(false);
      expect(selection.selection.value.selectedNodeId).toBe(mockAuthor1.id); // Selection preserved
      expect(selection.selection.value.highlightedNodeIds.size).toBeGreaterThan(0); // Highlights preserved
    });
  });

  describe("clearSelection", () => {
    it("clears both selection and panel state", () => {
      selection.selectNode(mockAuthor1.id);
      selection.clearSelection();

      expect(selection.selection.value.selectedNodeId).toBeNull();
      expect(selection.isPanelOpen.value).toBe(false);
      expect(selection.selection.value.highlightedNodeIds.size).toBe(0);
    });
  });

  describe("selectedEdge computed", () => {
    it("returns the selected edge object", () => {
      selection.selectEdge(mockEdge1.id);
      expect(selection.selectedEdge.value).toEqual(mockEdge1);
    });

    it("returns null when no edge selected", () => {
      expect(selection.selectedEdge.value).toBeNull();
    });
  });

  describe("isEdgeSelected computed", () => {
    it("returns true when edge is selected", () => {
      selection.selectEdge(mockEdge1.id);
      expect(selection.isEdgeSelected.value).toBe(true);
    });

    it("returns false when no edge selected", () => {
      expect(selection.isEdgeSelected.value).toBe(false);
    });
  });
});

describe("useNetworkSelection edge cases", () => {
  describe("non-existent nodeId handling", () => {
    it("should handle toggleSelectNode with non-existent nodeId gracefully", () => {
      const selection = useNetworkSelection();
      selection.setNodesAndEdges(mockNodes, mockEdges);

      // Should not throw when toggling non-existent node
      expect(() => {
        selection.toggleSelectNode("nonexistent:123" as NodeId);
      }).not.toThrow();

      // Selection should switch to the non-existent ID (the composable doesn't validate)
      // but highlights will be empty since no edges connect to it
      expect(selection.selection.value.highlightedNodeIds.size).toBe(0);
      expect(selection.selection.value.highlightedEdgeIds.size).toBe(0);
    });

    it("should handle selectNode with non-existent nodeId gracefully", () => {
      const selection = useNetworkSelection();
      selection.setNodesAndEdges(mockNodes, mockEdges);

      // Should not throw
      expect(() => {
        selection.selectNode("author:9999" as NodeId);
      }).not.toThrow();

      // Node is selected but no highlights since nothing connects to it
      expect(selection.selection.value.selectedNodeId).toBe("author:9999");
      expect(selection.isPanelOpen.value).toBe(true);
      expect(selection.selection.value.highlightedNodeIds.size).toBe(0);
    });

    it("selectedNode returns null for non-existent nodeId", () => {
      const selection = useNetworkSelection();
      selection.setNodesAndEdges(mockNodes, mockEdges);

      selection.selectNode("author:9999" as NodeId);

      // selectedNode computed should return null since ID not in map
      expect(selection.selectedNode.value).toBeNull();
    });
  });

  describe("missing source/target nodes in edges", () => {
    it("should handle selectEdge when source node does not exist in nodes map", () => {
      const selection = useNetworkSelection();
      const incompleteNodes = [mockPublisher1]; // Missing author:1
      selection.setNodesAndEdges(incompleteNodes, mockEdges);

      // Should not throw
      expect(() => {
        selection.selectEdge(mockEdge1.id);
      }).not.toThrow();

      // Edge is selected and highlights include both node IDs even if not in map
      expect(selection.selection.value.selectedEdgeId).toBe(mockEdge1.id);
      expect(selection.isPanelOpen.value).toBe(true);
      expect(selection.selection.value.highlightedNodeIds.has(mockEdge1.source)).toBe(true);
      expect(selection.selection.value.highlightedNodeIds.has(mockEdge1.target)).toBe(true);
    });

    it("should handle selectEdge when target node does not exist in nodes map", () => {
      const selection = useNetworkSelection();
      const incompleteNodes = [mockAuthor1]; // Missing publisher:1
      selection.setNodesAndEdges(incompleteNodes, mockEdges);

      // Should not throw
      expect(() => {
        selection.selectEdge(mockEdge1.id);
      }).not.toThrow();

      expect(selection.selectedEdge.value).toEqual(mockEdge1);
    });

    it("should handle selectEdge with non-existent edge ID", () => {
      const selection = useNetworkSelection();
      selection.setNodesAndEdges(mockNodes, mockEdges);

      // Should not throw
      expect(() => {
        selection.selectEdge("e:nonexistent:edge" as EdgeId);
      }).not.toThrow();

      // Edge not found, so nothing happens
      expect(selection.selection.value.selectedEdgeId).toBeNull();
      expect(selection.isPanelOpen.value).toBe(false);
    });
  });

  describe("methods called before initialization", () => {
    it("should handle toggleSelectNode before setNodesAndEdges", () => {
      const selection = useNetworkSelection();
      // Do NOT call setNodesAndEdges

      // Should not throw
      expect(() => {
        selection.toggleSelectNode("author:1" as NodeId);
      }).not.toThrow();

      // Panel opens but no highlights since edges map is empty
      expect(selection.isPanelOpen.value).toBe(true);
      expect(selection.highlightedNodeIds.value).toEqual([]);
      expect(selection.highlightedEdgeIds.value).toEqual([]);
    });

    it("should handle selectEdge before setNodesAndEdges", () => {
      const selection = useNetworkSelection();
      // Do NOT call setNodesAndEdges

      // Should not throw
      expect(() => {
        selection.selectEdge("e:author:1:publisher:1" as EdgeId);
      }).not.toThrow();

      // Edge not found in empty map, so nothing happens
      expect(selection.selection.value.selectedEdgeId).toBeNull();
      expect(selection.isPanelOpen.value).toBe(false);
    });

    it("should handle clearSelection before any selection", () => {
      const selection = useNetworkSelection();

      // Should not throw
      expect(() => {
        selection.clearSelection();
      }).not.toThrow();

      expect(selection.selection.value.selectedNodeId).toBeNull();
      expect(selection.selection.value.selectedEdgeId).toBeNull();
      expect(selection.isPanelOpen.value).toBe(false);
    });

    it("should handle isNodeHighlighted before initialization", () => {
      const selection = useNetworkSelection();

      // Should not throw and return false
      expect(selection.isNodeHighlighted("author:1" as NodeId)).toBe(false);
    });

    it("should handle isEdgeHighlighted before initialization", () => {
      const selection = useNetworkSelection();

      // Should not throw and return false
      expect(selection.isEdgeHighlighted("e:author:1:publisher:1" as EdgeId)).toBe(false);
    });
  });

  describe("hover state edge cases", () => {
    it("should handle setHoveredNode with null", () => {
      const selection = useNetworkSelection();
      selection.setNodesAndEdges(mockNodes, mockEdges);

      selection.setHoveredNode(mockAuthor1.id);
      expect(selection.selection.value.hoveredNodeId).toBe(mockAuthor1.id);

      selection.setHoveredNode(null);
      expect(selection.selection.value.hoveredNodeId).toBeNull();
    });

    it("should handle setHoveredEdge with null", () => {
      const selection = useNetworkSelection();
      selection.setNodesAndEdges(mockNodes, mockEdges);

      selection.setHoveredEdge(mockEdge1.id);
      expect(selection.selection.value.hoveredEdgeId).toBe(mockEdge1.id);

      selection.setHoveredEdge(null);
      expect(selection.selection.value.hoveredEdgeId).toBeNull();
    });
  });
});
