import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, VueWrapper } from "@vue/test-utils";
import StatsPanel from "../StatsPanel.vue";
import type {
  ApiNode,
  ApiEdge,
  SocialCirclesMeta,
  NodeId,
  EdgeId,
  BookId,
  NodeType,
  ConnectionType,
} from "@/types/socialCircles";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createNode(id: number, name: string, type: NodeType, bookCount = 1): ApiNode {
  return {
    id: `${type}:${id}` as NodeId,
    entity_id: id,
    name,
    type,
    book_count: bookCount,
    book_ids: [1 as BookId],
  };
}

function createEdge(
  sourceType: NodeType,
  sourceId: number,
  targetType: NodeType,
  targetId: number,
  type: ConnectionType = "publisher"
): ApiEdge {
  return {
    id: `e:${sourceType}:${sourceId}:${targetType}:${targetId}` as EdgeId,
    source: `${sourceType}:${sourceId}` as NodeId,
    target: `${targetType}:${targetId}` as NodeId,
    type,
    strength: 1,
  };
}

function createMeta(overrides: Partial<SocialCirclesMeta> = {}): SocialCirclesMeta {
  return {
    total_books: 50,
    total_authors: 10,
    total_publishers: 5,
    total_binders: 3,
    date_range: [1830, 1900],
    generated_at: "2026-01-28T00:00:00Z",
    truncated: false,
    ...overrides,
  };
}

const sampleNodes: ApiNode[] = [
  createNode(1, "Charles Dickens", "author", 12),
  createNode(2, "Charlotte Bronte", "author", 5),
  createNode(3, "George Eliot", "author", 8),
  createNode(10, "Chapman and Hall", "publisher", 15),
  createNode(11, "Smith, Elder", "publisher", 7),
  createNode(20, "Burn and Co", "binder", 4),
];

const sampleEdges: ApiEdge[] = [
  createEdge("author", 1, "publisher", 10, "publisher"),
  createEdge("author", 2, "publisher", 11, "publisher"),
  createEdge("author", 3, "publisher", 10, "publisher"),
  createEdge("author", 1, "author", 3, "shared_publisher"),
  createEdge("author", 1, "binder", 20, "binder"),
];

function mountStats(props: Partial<InstanceType<typeof StatsPanel>["$props"]> = {}) {
  return mount(StatsPanel, {
    props: {
      nodes: sampleNodes,
      edges: sampleEdges,
      meta: createMeta(),
      ...props,
    },
    global: {
      stubs: {
        StatCard: {
          props: ["value", "label", "sublabel"],
          template:
            '<div class="stat-card-stub" :data-value="value" :data-label="label" :data-sublabel="sublabel">{{ value }} {{ label }} {{ sublabel }}</div>',
        },
      },
    },
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("StatsPanel", () => {
  let wrapper: VueWrapper;

  afterEach(() => {
    wrapper?.unmount();
    vi.restoreAllMocks();
  });

  // =========================================================================
  // Rendering
  // =========================================================================

  describe("rendering", () => {
    it("renders the stats panel", () => {
      wrapper = mountStats();
      expect(wrapper.find(".stats-panel").exists()).toBe(true);
    });

    it("renders the toggle button", () => {
      wrapper = mountStats();
      const toggle = wrapper.find(".stats-panel__toggle");
      expect(toggle.exists()).toBe(true);
    });

    it("renders the title as Network Statistics", () => {
      wrapper = mountStats();
      expect(wrapper.find(".stats-panel__title").text()).toBe("Network Statistics");
    });

    it("renders content area when not collapsed", () => {
      wrapper = mountStats({ isCollapsed: false });
      expect(wrapper.find("#stats-panel-content").exists()).toBe(true);
      expect(wrapper.find("#stats-panel-content").isVisible()).toBe(true);
    });

    it("renders the Notable Entities section", () => {
      wrapper = mountStats();
      expect(wrapper.find(".stats-panel__section-title").text()).toBe("Notable Entities");
    });

    it("renders footer with date range", () => {
      wrapper = mountStats();
      const footer = wrapper.find(".stats-panel__footer");
      expect(footer.text()).toContain("1830");
      expect(footer.text()).toContain("1900");
    });

    it("renders total books in footer", () => {
      wrapper = mountStats();
      const footer = wrapper.find(".stats-panel__footer");
      expect(footer.text()).toContain("50 total books");
    });
  });

  // =========================================================================
  // Collapse / Expand
  // =========================================================================

  describe("collapse and expand", () => {
    it("shows minus icon when expanded", () => {
      wrapper = mountStats({ isCollapsed: false });
      expect(wrapper.find(".stats-panel__toggle-icon").text()).toBe("-");
    });

    it("shows plus icon when collapsed", () => {
      wrapper = mountStats({ isCollapsed: true });
      expect(wrapper.find(".stats-panel__toggle-icon").text()).toBe("+");
    });

    it("sets aria-expanded to true when expanded", () => {
      wrapper = mountStats({ isCollapsed: false });
      const toggle = wrapper.find(".stats-panel__toggle");
      expect(toggle.attributes("aria-expanded")).toBe("true");
    });

    it("sets aria-expanded to false when collapsed", () => {
      wrapper = mountStats({ isCollapsed: true });
      const toggle = wrapper.find(".stats-panel__toggle");
      expect(toggle.attributes("aria-expanded")).toBe("false");
    });

    it("adds collapsed class when isCollapsed is true", () => {
      wrapper = mountStats({ isCollapsed: true });
      expect(wrapper.find(".stats-panel").classes()).toContain("stats-panel--collapsed");
    });

    it("does not add collapsed class when isCollapsed is false", () => {
      wrapper = mountStats({ isCollapsed: false });
      expect(wrapper.find(".stats-panel").classes()).not.toContain("stats-panel--collapsed");
    });

    it("emits toggle event when toggle button is clicked", async () => {
      wrapper = mountStats();
      await wrapper.find(".stats-panel__toggle").trigger("click");

      expect(wrapper.emitted("toggle")).toBeTruthy();
      expect(wrapper.emitted("toggle")).toHaveLength(1);
    });

    it("hides content when collapsed", () => {
      wrapper = mountStats({ isCollapsed: true });
      // v-show sets display:none, element still exists but is not visible
      expect(wrapper.find("#stats-panel-content").exists()).toBe(true);
      expect(wrapper.find("#stats-panel-content").isVisible()).toBe(false);
    });
  });

  // =========================================================================
  // Stat calculations
  // =========================================================================

  describe("stat calculations", () => {
    it("displays total node count", () => {
      wrapper = mountStats();
      const statCards = wrapper.findAll(".stat-card-stub");
      const totalNodesCard = statCards.find((c) => c.attributes("data-label") === "Total Nodes");
      expect(totalNodesCard).toBeDefined();
      expect(totalNodesCard!.attributes("data-value")).toBe("6");
    });

    it("displays total connections count", () => {
      wrapper = mountStats();
      const statCards = wrapper.findAll(".stat-card-stub");
      const connectionsCard = statCards.find((c) => c.attributes("data-label") === "Connections");
      expect(connectionsCard).toBeDefined();
      expect(connectionsCard!.attributes("data-value")).toBe("5");
    });

    it("displays node count summary as sublabel", () => {
      wrapper = mountStats();
      const statCards = wrapper.findAll(".stat-card-stub");
      const totalNodesCard = statCards.find((c) => c.attributes("data-label") === "Total Nodes");
      const sublabel = totalNodesCard!.attributes("data-sublabel");
      expect(sublabel).toContain("3 authors");
      expect(sublabel).toContain("2 publishers");
      expect(sublabel).toContain("1 binder");
    });

    it("uses singular form for single node count", () => {
      const nodes = [createNode(1, "Dickens", "author"), createNode(10, "Chapman", "publisher")];
      wrapper = mountStats({ nodes, edges: [] });
      const statCards = wrapper.findAll(".stat-card-stub");
      const totalNodesCard = statCards.find((c) => c.attributes("data-label") === "Total Nodes");
      expect(totalNodesCard!.attributes("data-sublabel")).toContain("1 author");
      expect(totalNodesCard!.attributes("data-sublabel")).toContain("1 publisher");
    });

    it("displays network density", () => {
      wrapper = mountStats();
      const statCards = wrapper.findAll(".stat-card-stub");
      const densityCard = statCards.find((c) => c.attributes("data-label") === "Network Density");
      expect(densityCard).toBeDefined();
      // density = 2 * 5 / (6 * 5) * 100 = 33.33%
      expect(densityCard!.attributes("data-value")).toBe("33.33%");
    });

    it("displays average connections per node", () => {
      wrapper = mountStats();
      const statCards = wrapper.findAll(".stat-card-stub");
      const avgCard = statCards.find((c) => c.attributes("data-label") === "Avg. Connections");
      expect(avgCard).toBeDefined();
      // avg = (5 * 2) / 6 = 1.666... rounds to 1.7
      expect(avgCard!.attributes("data-value")).toBe("1.7");
    });

    it("handles zero nodes gracefully", () => {
      wrapper = mountStats({ nodes: [], edges: [] });
      const statCards = wrapper.findAll(".stat-card-stub");
      const totalNodesCard = statCards.find((c) => c.attributes("data-label") === "Total Nodes");
      expect(totalNodesCard!.attributes("data-value")).toBe("0");
    });

    it("handles density with fewer than 2 nodes", () => {
      const nodes = [createNode(1, "Dickens", "author")];
      wrapper = mountStats({ nodes, edges: [] });
      const statCards = wrapper.findAll(".stat-card-stub");
      const densityCard = statCards.find((c) => c.attributes("data-label") === "Network Density");
      expect(densityCard!.attributes("data-value")).toBe("0%");
    });
  });

  // =========================================================================
  // Notable entities
  // =========================================================================

  describe("notable entities", () => {
    it("displays most connected author", () => {
      wrapper = mountStats();
      const notable = wrapper.find(".stats-panel__notable");
      // Charles Dickens has degree 3 (edges to pub:10, author:3, binder:20)
      expect(notable.text()).toContain("Charles Dickens");
      expect(notable.text()).toContain("3 connections");
    });

    it("displays most prolific publisher", () => {
      wrapper = mountStats();
      const notable = wrapper.find(".stats-panel__notable");
      // Chapman and Hall has book_count 15
      expect(notable.text()).toContain("Chapman and Hall");
      expect(notable.text()).toContain("15 books");
    });

    it("shows empty message when no authors or publishers", () => {
      const nodes = [createNode(20, "Burn and Co", "binder", 4)];
      wrapper = mountStats({ nodes, edges: [] });
      expect(wrapper.find(".stats-panel__notable-empty").exists()).toBe(true);
      expect(wrapper.find(".stats-panel__notable-empty").text()).toContain("No notable entities");
    });

    it("shows most connected author label", () => {
      wrapper = mountStats();
      const labels = wrapper.findAll(".stats-panel__notable-label");
      expect(labels[0].text()).toBe("Most Connected Author");
    });

    it("shows most prolific publisher label", () => {
      wrapper = mountStats();
      const labels = wrapper.findAll(".stats-panel__notable-label");
      expect(labels[1].text()).toBe("Most Prolific Publisher");
    });
  });

  // =========================================================================
  // Meta / footer
  // =========================================================================

  describe("meta and footer", () => {
    it("displays date range from meta", () => {
      wrapper = mountStats();
      const metas = wrapper.findAll(".stats-panel__meta");
      expect(metas[0].text()).toContain("1830");
      expect(metas[0].text()).toContain("1900");
    });

    it("displays total books from meta", () => {
      wrapper = mountStats({ meta: createMeta({ total_books: 123 }) });
      const metas = wrapper.findAll(".stats-panel__meta");
      const booksMetaText = metas.map((m) => m.text()).find((t) => t.includes("total books"));
      expect(booksMetaText).toContain("123 total books");
    });

    it("displays collection prefix for date range", () => {
      wrapper = mountStats();
      const metas = wrapper.findAll(".stats-panel__meta");
      expect(metas[0].text()).toContain("Collection:");
    });
  });
});
