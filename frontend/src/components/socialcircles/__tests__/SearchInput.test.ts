import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { mount, VueWrapper } from "@vue/test-utils";
import SearchInput, { MAX_RESULTS } from "../SearchInput.vue";
import type { ApiNode, NodeType, NodeId, BookId } from "@/types/socialCircles";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createNode(id: number, name: string, type: NodeType = "author", bookCount = 1): ApiNode {
  return {
    id: `${type}:${id}` as NodeId,
    entity_id: id,
    name,
    type,
    book_count: bookCount,
    book_ids: [1 as BookId],
  };
}

const sampleNodes: ApiNode[] = [
  createNode(1, "Charles Dickens", "author", 12),
  createNode(2, "Charlotte Bronte", "author", 5),
  createNode(3, "Chapman and Hall", "publisher", 8),
  createNode(4, "Cassell and Company", "publisher", 3),
  createNode(5, "Burn and Co", "binder", 2),
];

function mountSearch(props: Partial<InstanceType<typeof SearchInput>["$props"]> = {}) {
  return mount(SearchInput, {
    props: {
      nodes: sampleNodes,
      modelValue: "",
      ...props,
    },
    attachTo: document.body,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SearchInput", () => {
  let wrapper: VueWrapper;

  beforeEach(() => {
    vi.useFakeTimers();
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // =========================================================================
  // Rendering
  // =========================================================================

  describe("rendering", () => {
    it("renders the search input field", () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");
      expect(input.exists()).toBe(true);
    });

    it("uses the default placeholder", () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");
      expect(input.attributes("placeholder")).toBe("Search people...");
    });

    it("accepts a custom placeholder", () => {
      wrapper = mountSearch({ placeholder: "Find author..." });
      const input = wrapper.find("input.search-input__field");
      expect(input.attributes("placeholder")).toBe("Find author...");
    });

    it("renders the search icon", () => {
      wrapper = mountSearch();
      expect(wrapper.find("svg.search-input__icon").exists()).toBe(true);
    });

    it("uses the default id", () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");
      expect(input.attributes("id")).toBe("search-people");
    });

    it("accepts a custom id", () => {
      wrapper = mountSearch({ id: "custom-search" });
      const input = wrapper.find("input.search-input__field");
      expect(input.attributes("id")).toBe("custom-search");
    });

    it("does not show dropdown initially", () => {
      wrapper = mountSearch();
      expect(wrapper.find(".search-input__dropdown").exists()).toBe(false);
    });
  });

  // =========================================================================
  // Debounced search
  // =========================================================================

  describe("debounced search", () => {
    it("does not show results before debounce completes", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Char");
      await input.trigger("input");

      // Before debounce fires
      expect(wrapper.find(".search-input__dropdown").exists()).toBe(false);
    });

    it("shows results after 300ms debounce", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Char");
      await input.trigger("input");

      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      expect(wrapper.find(".search-input__dropdown").exists()).toBe(true);
    });

    it("emits update:modelValue on input", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Char");
      await input.trigger("input");

      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
      expect(wrapper.emitted("update:modelValue")![0]).toEqual(["Char"]);
    });

    it("debounces rapid inputs and only searches with final value", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("C");
      await input.trigger("input");
      vi.advanceTimersByTime(100);

      await input.setValue("Ch");
      await input.trigger("input");
      vi.advanceTimersByTime(100);

      await input.setValue("Cha");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      // Dropdown should be open with results matching "Cha"
      expect(wrapper.find(".search-input__dropdown").exists()).toBe(true);
      // "Charles Dickens", "Charlotte Bronte", "Chapman and Hall" all match "Cha"
      const items = wrapper.findAll(".search-input__item");
      expect(items.length).toBe(3);
    });

    it("shows no results message when query matches nothing", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("zzzzz");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      expect(wrapper.find(".search-input__no-results").exists()).toBe(true);
      expect(wrapper.find(".search-input__no-results").text()).toContain("zzzzz");
    });

    it("does not open dropdown for whitespace-only query", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("   ");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      expect(wrapper.find(".search-input__dropdown").exists()).toBe(false);
    });
  });

  // =========================================================================
  // Grouped results
  // =========================================================================

  describe("grouped results", () => {
    it("groups results by node type", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("C");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const groups = wrapper.findAll(".search-input__group");
      // "C" matches: Charles Dickens, Charlotte Bronte (authors), Chapman and Hall, Cassell and Company (publishers), Burn and Co (binder)
      expect(groups.length).toBe(3); // Authors, Publishers, and Binders
    });

    it("displays group headers", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("C");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const headers = wrapper.findAll(".search-input__group-header");
      expect(headers[0].text()).toBe("Authors");
      expect(headers[1].text()).toBe("Publishers");
    });

    it("displays node names in results", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Charles");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const items = wrapper.findAll(".search-input__item-name");
      expect(items[0].text()).toBe("Charles Dickens");
    });

    it("displays book count for nodes", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Charles");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const counts = wrapper.findAll(".search-input__item-count");
      expect(counts[0].text()).toBe("12 books");
    });

    it("uses singular book when count is 1", async () => {
      const nodes = [createNode(1, "Single Book Author", "author", 1)];
      wrapper = mount(SearchInput, {
        props: { nodes, modelValue: "" },
        attachTo: document.body,
      });
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Single");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const counts = wrapper.findAll(".search-input__item-count");
      expect(counts[0].text()).toBe("1 book");
    });
  });

  // =========================================================================
  // MAX_RESULTS limit
  // =========================================================================

  describe("result limiting", () => {
    it("exports MAX_RESULTS constant", () => {
      expect(MAX_RESULTS).toBe(10);
    });

    it("limits results to MAX_RESULTS", async () => {
      const manyNodes: ApiNode[] = [];
      for (let i = 0; i < 20; i++) {
        manyNodes.push(createNode(i, `Author ${i}`, "author", 1));
      }

      wrapper = mount(SearchInput, {
        props: { nodes: manyNodes, modelValue: "" },
        attachTo: document.body,
      });
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Author");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const items = wrapper.findAll(".search-input__item");
      expect(items.length).toBe(MAX_RESULTS);
    });
  });

  // =========================================================================
  // Keyboard navigation
  // =========================================================================

  describe("keyboard navigation", () => {
    async function openDropdown(w: VueWrapper) {
      const input = w.find("input.search-input__field");
      await input.setValue("C");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await w.vm.$nextTick();
    }

    it("navigates down with ArrowDown", async () => {
      wrapper = mountSearch();
      await openDropdown(wrapper);

      const input = wrapper.find("input.search-input__field");
      await input.trigger("keydown", { key: "ArrowDown" });
      await wrapper.vm.$nextTick();

      const activeItems = wrapper.findAll(".search-input__item--active");
      expect(activeItems.length).toBe(1);
    });

    it("navigates up with ArrowUp after going down", async () => {
      wrapper = mountSearch();
      await openDropdown(wrapper);

      const input = wrapper.find("input.search-input__field");
      await input.trigger("keydown", { key: "ArrowDown" });
      await input.trigger("keydown", { key: "ArrowDown" });
      await input.trigger("keydown", { key: "ArrowUp" });
      await wrapper.vm.$nextTick();

      const activeItems = wrapper.findAll(".search-input__item--active");
      expect(activeItems.length).toBe(1);
    });

    it("does not go below last item with ArrowDown", async () => {
      wrapper = mountSearch();
      await openDropdown(wrapper);

      const input = wrapper.find("input.search-input__field");
      const items = wrapper.findAll(".search-input__item");
      const totalItems = items.length;

      // Press down more times than items
      for (let i = 0; i < totalItems + 5; i++) {
        await input.trigger("keydown", { key: "ArrowDown" });
      }
      await wrapper.vm.$nextTick();

      // Last item should be active
      const lastItem = items[totalItems - 1];
      expect(lastItem.classes()).toContain("search-input__item--active");
    });

    it("does not go above first item with ArrowUp", async () => {
      wrapper = mountSearch();
      await openDropdown(wrapper);

      const input = wrapper.find("input.search-input__field");
      await input.trigger("keydown", { key: "ArrowDown" });
      // Now at index 0, press up should stay at 0
      await input.trigger("keydown", { key: "ArrowUp" });
      await wrapper.vm.$nextTick();

      const items = wrapper.findAll(".search-input__item");
      expect(items[0].classes()).toContain("search-input__item--active");
    });

    it("selects item on Enter", async () => {
      wrapper = mountSearch();
      await openDropdown(wrapper);

      const input = wrapper.find("input.search-input__field");
      await input.trigger("keydown", { key: "ArrowDown" });
      await input.trigger("keydown", { key: "Enter" });

      expect(wrapper.emitted("select")).toBeTruthy();
      expect(wrapper.emitted("select")![0][0]).toMatchObject({
        name: "Charles Dickens",
        type: "author",
      });
    });

    it("closes dropdown on Escape", async () => {
      wrapper = mountSearch();
      await openDropdown(wrapper);

      expect(wrapper.find(".search-input__dropdown").exists()).toBe(true);

      const input = wrapper.find("input.search-input__field");
      await input.trigger("keydown", { key: "Escape" });
      await wrapper.vm.$nextTick();

      expect(wrapper.find(".search-input__dropdown").exists()).toBe(false);
    });

    it("does not emit select on Enter when no item is active", async () => {
      wrapper = mountSearch();
      await openDropdown(wrapper);

      const input = wrapper.find("input.search-input__field");
      // activeIndex is -1 initially, press Enter without ArrowDown
      await input.trigger("keydown", { key: "Enter" });

      expect(wrapper.emitted("select")).toBeFalsy();
    });
  });

  // =========================================================================
  // Node selection
  // =========================================================================

  describe("node selection", () => {
    it("emits select event when item is clicked", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Charles");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const item = wrapper.find(".search-input__item");
      await item.trigger("click");

      expect(wrapper.emitted("select")).toBeTruthy();
      expect(wrapper.emitted("select")![0][0]).toMatchObject({
        name: "Charles Dickens",
      });
    });

    it("closes dropdown after selection", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Charles");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const item = wrapper.find(".search-input__item");
      await item.trigger("click");
      await wrapper.vm.$nextTick();

      expect(wrapper.find(".search-input__dropdown").exists()).toBe(false);
    });

    it("updates input value to selected node name", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Charles");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const item = wrapper.find(".search-input__item");
      await item.trigger("click");

      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
      const emitted = wrapper.emitted("update:modelValue")!;
      // Last emission should be the selected node name
      expect(emitted[emitted.length - 1]).toEqual(["Charles Dickens"]);
    });

    it("highlights item on mouseenter", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("C");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const items = wrapper.findAll(".search-input__item");
      await items[1].trigger("mouseenter");
      await wrapper.vm.$nextTick();

      expect(items[1].classes()).toContain("search-input__item--active");
    });
  });

  // =========================================================================
  // Focus behavior
  // =========================================================================

  describe("focus behavior", () => {
    it("opens dropdown on focus when there is a query", async () => {
      wrapper = mountSearch({ modelValue: "Charles" });
      const input = wrapper.find("input.search-input__field");

      // Set debounced query by triggering input and waiting
      await input.setValue("Charles");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      // Close it first via Escape
      await input.trigger("keydown", { key: "Escape" });
      await wrapper.vm.$nextTick();
      expect(wrapper.find(".search-input__dropdown").exists()).toBe(false);

      // Focus should re-open
      await input.trigger("focus");
      await wrapper.vm.$nextTick();

      expect(wrapper.find(".search-input__dropdown").exists()).toBe(true);
    });

    it("does not open dropdown on focus when query is empty", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.trigger("focus");
      await wrapper.vm.$nextTick();

      expect(wrapper.find(".search-input__dropdown").exists()).toBe(false);
    });
  });

  // =========================================================================
  // External modelValue sync
  // =========================================================================

  describe("external modelValue sync", () => {
    it("syncs when modelValue prop changes externally", async () => {
      wrapper = mountSearch({ modelValue: "" });

      await wrapper.setProps({ modelValue: "Dickens" });
      await wrapper.vm.$nextTick();

      const input = wrapper.find("input.search-input__field");
      expect((input.element as HTMLInputElement).value).toBe("Dickens");
    });
  });

  // =========================================================================
  // Node type indicators
  // =========================================================================

  describe("node type indicators", () => {
    it("applies author type class to author items", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Charles Dickens");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const item = wrapper.find(".search-input__item");
      expect(item.classes()).toContain("search-input__item--author");
    });

    it("applies publisher type class to publisher items", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Chapman");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const item = wrapper.find(".search-input__item");
      expect(item.classes()).toContain("search-input__item--publisher");
    });

    it("applies binder type class to binder items", async () => {
      wrapper = mountSearch();
      const input = wrapper.find("input.search-input__field");

      await input.setValue("Burn");
      await input.trigger("input");
      vi.advanceTimersByTime(300);
      await wrapper.vm.$nextTick();

      const item = wrapper.find(".search-input__item");
      expect(item.classes()).toContain("search-input__item--binder");
    });
  });
});
