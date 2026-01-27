import { describe, it, expect, beforeEach } from "vitest";
import { useNetworkSelection } from "../useNetworkSelection";
import { mockNodes, mockEdges, mockAuthor1, mockPublisher1, mockEdge1 } from "./fixtures";

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
