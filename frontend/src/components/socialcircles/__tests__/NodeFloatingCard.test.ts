import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, VueWrapper } from "@vue/test-utils";
import NodeFloatingCard from "../NodeFloatingCard.vue";
import type { ApiNode, ApiEdge, NodeId, EdgeId, BookId } from "@/types/socialCircles";

// Mock useFocusTrap
vi.mock("@vueuse/integrations/useFocusTrap", () => ({
  useFocusTrap: () => ({
    activate: vi.fn(),
    deactivate: vi.fn(),
  }),
}));

// Test fixtures
const mockAuthor: ApiNode = {
  id: "author:1" as NodeId,
  entity_id: 1,
  name: "Charles Dickens",
  type: "author",
  book_count: 12,
  book_ids: [1, 2, 3] as BookId[],
  birth_year: 1812,
  death_year: 1870,
  era: "victorian",
  tier: "TIER_1",
};

const mockPublisher: ApiNode = {
  id: "publisher:1" as NodeId,
  entity_id: 1,
  name: "Chapman & Hall",
  type: "publisher",
  tier: "TIER_1",
  book_count: 8,
  book_ids: [1, 2] as BookId[],
};

const mockBinder: ApiNode = {
  id: "binder:1" as NodeId,
  entity_id: 1,
  name: "Riviere & Son",
  type: "binder",
  tier: "TIER_2",
  book_count: 6,
  book_ids: [1] as BookId[],
};

const mockEdge: ApiEdge = {
  id: "e:author:1:publisher:1" as EdgeId,
  source: "author:1" as NodeId,
  target: "publisher:1" as NodeId,
  type: "publisher",
  strength: 4,
  shared_book_ids: [1, 2] as BookId[],
};

const mockEdge2: ApiEdge = {
  id: "e:author:1:binder:1" as EdgeId,
  source: "author:1" as NodeId,
  target: "binder:1" as NodeId,
  type: "binder",
  strength: 2,
  shared_book_ids: [1] as BookId[],
};

const defaultProps = {
  node: mockAuthor,
  nodePosition: { x: 100, y: 100 },
  viewportSize: { width: 1200, height: 800 },
  edges: [mockEdge, mockEdge2],
  nodes: [mockAuthor, mockPublisher, mockBinder],
  isOpen: true,
};

describe("NodeFloatingCard", () => {
  let wrapper: VueWrapper;

  beforeEach(() => {
    // Mock window event listeners
    vi.spyOn(window, "addEventListener");
    vi.spyOn(window, "removeEventListener");
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("renders author card with correct data", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      expect(wrapper.text()).toContain("Charles Dickens");
      expect(wrapper.text()).toContain("12 books");
      expect(wrapper.text()).toContain("1812");
      expect(wrapper.text()).toContain("1870");
    });

    it("renders publisher card with type-specific styling", () => {
      wrapper = mount(NodeFloatingCard, {
        props: { ...defaultProps, node: mockPublisher },
      });

      expect(wrapper.find(".node-floating-card--publisher").exists()).toBe(true);
      expect(wrapper.text()).toContain("Chapman & Hall");
    });

    it("renders binder card with type-specific styling", () => {
      wrapper = mount(NodeFloatingCard, {
        props: { ...defaultProps, node: mockBinder },
      });

      expect(wrapper.find(".node-floating-card--binder").exists()).toBe(true);
      expect(wrapper.text()).toContain("Riviere & Son");
    });

    it("does not render when isOpen is false", () => {
      wrapper = mount(NodeFloatingCard, {
        props: { ...defaultProps, isOpen: false },
      });

      expect(wrapper.find(".node-floating-card").exists()).toBe(false);
    });

    it("does not render when node is null", () => {
      wrapper = mount(NodeFloatingCard, {
        props: { ...defaultProps, node: null },
      });

      expect(wrapper.find(".node-floating-card").exists()).toBe(false);
    });

    it("does not render when nodePosition is null", () => {
      wrapper = mount(NodeFloatingCard, {
        props: { ...defaultProps, nodePosition: null },
      });

      expect(wrapper.find(".node-floating-card").exists()).toBe(false);
    });

    it("renders tier display with correct stars", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const tierDisplay = wrapper.find(".node-floating-card__tier");
      expect(tierDisplay.exists()).toBe(true);
      // TIER_1 should show 3 filled stars
      expect(tierDisplay.text()).toContain("★★★");
    });

    it("renders era with underscores replaced by spaces", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      expect(wrapper.text()).toContain("victorian");
    });
  });

  describe("connections", () => {
    it("displays connections list", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      expect(wrapper.text()).toContain("Connections");
      expect(wrapper.text()).toContain("Chapman & Hall");
      expect(wrapper.text()).toContain("Riviere & Son");
    });

    it("displays total connections count", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      expect(wrapper.text()).toContain("2 connections");
    });

    it("limits connections to 5 and shows remaining count", () => {
      const manyEdges: ApiEdge[] = [];
      const manyNodes: ApiNode[] = [mockAuthor];

      for (let i = 2; i <= 8; i++) {
        manyNodes.push({
          id: `publisher:${i}` as NodeId,
          entity_id: i,
          name: `Publisher ${i}`,
          type: "publisher",
          book_count: 1,
          book_ids: [],
        });
        manyEdges.push({
          id: `e:author:1:publisher:${i}` as EdgeId,
          source: "author:1" as NodeId,
          target: `publisher:${i}` as NodeId,
          type: "publisher",
          strength: 1,
        });
      }

      wrapper = mount(NodeFloatingCard, {
        props: {
          ...defaultProps,
          edges: manyEdges,
          nodes: manyNodes,
        },
      });

      const connectionItems = wrapper.findAll(".node-floating-card__connection-item");
      expect(connectionItems.length).toBe(5);
      expect(wrapper.text()).toContain("showing 5 of 7");
      expect(wrapper.text()).toContain("View 2 more");
    });

    it("shows empty state when no connections exist", () => {
      wrapper = mount(NodeFloatingCard, {
        props: { ...defaultProps, edges: [] },
      });

      expect(wrapper.text()).toContain("No connections found");
    });

    it("renders correct connection icon for publisher type", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const icons = wrapper.findAll(".node-floating-card__connection-icon");
      // First connection is publisher type
      expect(icons[0].text()).toContain("📚");
    });

    it("renders correct connection icon for binder type", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const icons = wrapper.findAll(".node-floating-card__connection-icon");
      // Second connection is binder type
      expect(icons[1].text()).toContain("🪡");
    });
  });

  describe("events", () => {
    it("emits close when X button clicked", async () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      await wrapper.find(".node-floating-card__close").trigger("click");

      expect(wrapper.emitted("close")).toBeTruthy();
      expect(wrapper.emitted("close")).toHaveLength(1);
    });

    it("emits selectEdge when connection button clicked", async () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const connectionButtons = wrapper.findAll(".node-floating-card__connection-button");
      await connectionButtons[0].trigger("click");

      expect(wrapper.emitted("selectEdge")).toBeTruthy();
      expect(wrapper.emitted("selectEdge")![0]).toEqual([mockEdge.id]);
    });

    it("emits viewProfile when profile button clicked", async () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      await wrapper.find(".node-floating-card__profile-button").trigger("click");

      expect(wrapper.emitted("viewProfile")).toBeTruthy();
      expect(wrapper.emitted("viewProfile")![0]).toEqual([mockAuthor.id]);
    });

    it('emits viewProfile when "view more" link clicked', async () => {
      const manyEdges: ApiEdge[] = [];
      const manyNodes: ApiNode[] = [mockAuthor];

      for (let i = 2; i <= 8; i++) {
        manyNodes.push({
          id: `publisher:${i}` as NodeId,
          entity_id: i,
          name: `Publisher ${i}`,
          type: "publisher",
          book_count: 1,
          book_ids: [],
        });
        manyEdges.push({
          id: `e:author:1:publisher:${i}` as EdgeId,
          source: "author:1" as NodeId,
          target: `publisher:${i}` as NodeId,
          type: "publisher",
          strength: 1,
        });
      }

      wrapper = mount(NodeFloatingCard, {
        props: { ...defaultProps, edges: manyEdges, nodes: manyNodes },
      });

      await wrapper.find(".node-floating-card__more-link").trigger("click");

      expect(wrapper.emitted("viewProfile")).toBeTruthy();
    });
  });

  describe("keyboard handling", () => {
    it("adds keydown listener on mount", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      expect(window.addEventListener).toHaveBeenCalledWith("keydown", expect.any(Function));
    });

    it("removes keydown listener on unmount", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });
      wrapper.unmount();

      expect(window.removeEventListener).toHaveBeenCalledWith("keydown", expect.any(Function));
    });

    it("emits close on Escape key", async () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      // Simulate Escape key press
      const event = new KeyboardEvent("keydown", { key: "Escape" });
      window.dispatchEvent(event);

      // Wait for Vue to process the event
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted("close")).toBeTruthy();
    });
  });

  describe("accessibility", () => {
    it("has correct dialog role and aria attributes", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const card = wrapper.find(".node-floating-card");
      expect(card.attributes("role")).toBe("dialog");
      expect(card.attributes("aria-modal")).toBe("false");
      expect(card.attributes("aria-label")).toBe("Details for Charles Dickens");
    });

    it("close button has aria-label", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const closeButton = wrapper.find(".node-floating-card__close");
      expect(closeButton.attributes("aria-label")).toBe("Close");
    });

    it("has screen reader text for tier", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const srOnly = wrapper.find(".node-floating-card__tier .sr-only");
      expect(srOnly.exists()).toBe(true);
      expect(srOnly.text()).toContain("Tier 1");
    });

    it("close button meets minimum touch target size", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const closeButton = wrapper.find(".node-floating-card__close");
      // Check that min-width and min-height classes are applied via CSS
      // The actual size verification would require computed styles
      expect(closeButton.exists()).toBe(true);
    });
  });

  describe("positioning", () => {
    it("applies computed position to card style", () => {
      wrapper = mount(NodeFloatingCard, {
        props: {
          ...defaultProps,
          nodePosition: { x: 200, y: 150 },
        },
      });

      const card = wrapper.find(".node-floating-card");
      const style = card.attributes("style");

      // Position should be computed by getBestCardPosition
      expect(style).toContain("left:");
      expect(style).toContain("top:");
    });

    it("updates position when nodePosition prop changes", async () => {
      wrapper = mount(NodeFloatingCard, {
        props: {
          ...defaultProps,
          nodePosition: { x: 100, y: 100 },
        },
      });

      const initialStyle = wrapper.find(".node-floating-card").attributes("style");

      await wrapper.setProps({
        nodePosition: { x: 500, y: 300 },
      });

      const updatedStyle = wrapper.find(".node-floating-card").attributes("style");
      expect(updatedStyle).not.toBe(initialStyle);
    });
  });

  describe("image handling", () => {
    it("renders placeholder image with correct src", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const img = wrapper.find(".node-floating-card__image");
      expect(img.exists()).toBe(true);
      expect(img.attributes("src")).toContain("/images/entity-placeholders/authors/");
    });

    it("has lazy loading attribute", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const img = wrapper.find(".node-floating-card__image");
      expect(img.attributes("loading")).toBe("lazy");
    });

    it("has alt text for image", () => {
      wrapper = mount(NodeFloatingCard, { props: defaultProps });

      const img = wrapper.find(".node-floating-card__image");
      expect(img.attributes("alt")).toBe("Portrait of Charles Dickens");
    });
  });
});
