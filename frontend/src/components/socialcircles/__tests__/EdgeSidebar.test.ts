import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import EdgeSidebar from "../EdgeSidebar.vue";
import type { ApiNode, ApiEdge, NodeId, EdgeId, BookId } from "@/types/socialCircles";

// Mock vue-router
vi.mock("vue-router", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

// Mock @vueuse/integrations/useFocusTrap
vi.mock("@/composables/useFocusTrap", () => ({
  useFocusTrap: () => ({
    activate: vi.fn(),
    deactivate: vi.fn(),
  }),
}));

// Mock api service
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: { items: [] } }),
  },
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

const mockEdge: ApiEdge = {
  id: "e:author:1:publisher:1" as EdgeId,
  source: "author:1" as NodeId,
  target: "publisher:1" as NodeId,
  type: "publisher",
  strength: 4,
  shared_book_ids: [1, 2] as BookId[],
};

const mockNodes: ApiNode[] = [mockAuthor, mockPublisher];

const defaultGlobal = {
  stubs: { RouterLink: true },
};

describe("EdgeSidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders when isOpen is true with valid edge and nodes", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    expect(wrapper.find(".edge-sidebar").exists()).toBe(true);
    expect(wrapper.text()).toContain("Charles Dickens");
    expect(wrapper.text()).toContain("Chapman & Hall");
  });

  it("does not render when isOpen is false", () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: false,
      },
      global: defaultGlobal,
    });

    expect(wrapper.find(".edge-sidebar").exists()).toBe(false);
  });

  it("does not render when edge is null", () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: null,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    expect(wrapper.find(".edge-sidebar").exists()).toBe(false);
  });

  it("displays correct connection type label", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    expect(wrapper.text()).toContain("CONNECTION: Published together");
  });

  it("displays connection strength dots", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    const strengthDots = wrapper.find(".edge-sidebar__strength-dots");
    expect(strengthDots.exists()).toBe(true);
    // Strength is calculated from shared_book_ids.length (2), so should be 2 filled dots
    expect(strengthDots.text()).toMatch(/[●○]+/);
  });

  it("displays shared book count", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    expect(wrapper.text()).toContain("(2 works)");
  });

  it("emits close when X button is clicked", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    await wrapper.find(".edge-sidebar__close").trigger("click");
    expect(wrapper.emitted("close")).toBeTruthy();
  });

  it("emits selectNode when source entity is clicked", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    const entityButtons = wrapper.findAll(".edge-sidebar__entity");
    await entityButtons[0].trigger("click");

    expect(wrapper.emitted("selectNode")).toBeTruthy();
    expect(wrapper.emitted("selectNode")![0]).toEqual(["author:1"]);
  });

  it("emits selectNode when target entity is clicked", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    const entityButtons = wrapper.findAll(".edge-sidebar__entity");
    await entityButtons[1].trigger("click");

    expect(wrapper.emitted("selectNode")).toBeTruthy();
    expect(wrapper.emitted("selectNode")![0]).toEqual(["publisher:1"]);
  });

  it("toggles pin state when pin button is clicked", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    const pinButton = wrapper.find(".edge-sidebar__pin");
    expect(pinButton.classes()).not.toContain("edge-sidebar__pin--active");

    await pinButton.trigger("click");
    expect(pinButton.classes()).toContain("edge-sidebar__pin--active");

    await pinButton.trigger("click");
    expect(pinButton.classes()).not.toContain("edge-sidebar__pin--active");
  });

  it("applies correct CSS class based on edge type", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    expect(wrapper.find(".edge-sidebar--publisher").exists()).toBe(true);
  });

  it("displays bidirectional arrow for shared_publisher type", async () => {
    const sharedPublisherEdge: ApiEdge = {
      ...mockEdge,
      type: "shared_publisher",
    };

    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: sharedPublisherEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    expect(wrapper.find(".edge-sidebar__connection-arrow").text()).toBe("↔");
  });

  it("displays unidirectional arrow for publisher type", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    expect(wrapper.find(".edge-sidebar__connection-arrow").text()).toBe("→");
  });

  it("has correct aria-label for accessibility", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    const sidebar = wrapper.find(".edge-sidebar");
    expect(sidebar.attributes("aria-label")).toBe(
      "Connection between Charles Dickens and Chapman & Hall"
    );
  });

  it("shows loading skeleton while fetching books", async () => {
    // Delay the API response
    const { api } = await import("@/services/api");
    vi.mocked(api.get).mockImplementation(() => new Promise(() => {}));

    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    // Should show loading skeleton
    expect(wrapper.find(".edge-sidebar__loading").exists()).toBe(true);
    expect(wrapper.findAll(".edge-sidebar__skeleton-book").length).toBe(3);
  });

  it("shows empty message when no shared books", async () => {
    const edgeWithNoBooks: ApiEdge = {
      ...mockEdge,
      shared_book_ids: [],
    };

    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: edgeWithNoBooks,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    expect(wrapper.find(".edge-sidebar__empty").exists()).toBe(true);
    expect(wrapper.text()).toContain("No shared books found");
  });

  it('displays section title for binder type as "Bound Books"', async () => {
    const binderEdge: ApiEdge = {
      ...mockEdge,
      type: "binder",
    };

    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: binderEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    expect(wrapper.find(".edge-sidebar__section-title").text()).toBe("Bound Books");
  });

  it('displays section title for publisher type as "Shared Books"', async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    expect(wrapper.find(".edge-sidebar__section-title").text()).toBe("Shared Books");
  });

  it("renders footer with view buttons for both entities", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    const viewButtons = wrapper.findAll(".edge-sidebar__view-button");
    expect(viewButtons.length).toBe(2);
    expect(viewButtons[0].text()).toContain("View");
    expect(viewButtons[1].text()).toContain("View");
  });

  it("renders profile links for source and target nodes", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: {
        edge: mockEdge,
        nodes: mockNodes,
        isOpen: true,
      },
      global: defaultGlobal,
    });

    await flushPromises();

    const links = wrapper.findAll(".edge-sidebar__profile-link");
    expect(links).toHaveLength(2);
  });

  it("displays evidence narrative with quotes for AI edges (#1824)", async () => {
    const aiEdge: ApiEdge = {
      ...mockEdge,
      type: "family",
      evidence: "Dickens and Catherine Hogarth married in 1836",
    };

    const wrapper = mount(EdgeSidebar, {
      props: { edge: aiEdge, nodes: mockNodes, isOpen: true },
      global: defaultGlobal,
    });

    await flushPromises();

    const narrative = wrapper.find(".edge-sidebar__narrative");
    expect(narrative.exists()).toBe(true);
    const evidence = wrapper.find(".edge-sidebar__evidence");
    expect(evidence.text()).toContain('"Dickens and Catherine Hogarth');
    expect(evidence.classes()).not.toContain("edge-sidebar__evidence--plain");
  });

  it("displays evidence without quotes for book-based edges (#1824)", async () => {
    const bookEdge: ApiEdge = {
      ...mockEdge,
      type: "publisher",
      evidence: "Published 3 work(s)",
    };

    const wrapper = mount(EdgeSidebar, {
      props: { edge: bookEdge, nodes: mockNodes, isOpen: true },
      global: defaultGlobal,
    });

    await flushPromises();

    const evidence = wrapper.find(".edge-sidebar__evidence");
    expect(evidence.text()).toBe("Published 3 work(s)");
    expect(evidence.classes()).toContain("edge-sidebar__evidence--plain");
  });

  it("hides narrative section when no evidence", async () => {
    const wrapper = mount(EdgeSidebar, {
      props: { edge: mockEdge, nodes: mockNodes, isOpen: true },
      global: defaultGlobal,
    });

    await flushPromises();

    expect(wrapper.find(".edge-sidebar__narrative").exists()).toBe(false);
  });
});
