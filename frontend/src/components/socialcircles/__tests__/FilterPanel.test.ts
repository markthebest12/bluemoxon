import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, VueWrapper } from "@vue/test-utils";
import FilterPanel from "../FilterPanel.vue";
import type { FilterState, Era } from "@/types/socialCircles";

// Default filter state matching the component's expected structure
const createDefaultFilterState = (overrides: Partial<FilterState> = {}): FilterState => ({
  showAuthors: true,
  showPublishers: true,
  showBinders: true,
  connectionTypes: [
    "publisher",
    "shared_publisher",
    "binder",
    "family",
    "friendship",
    "influence",
    "collaboration",
    "scandal",
  ],
  tier1Only: false,
  eras: [],
  searchQuery: "",
  ...overrides,
});

describe("FilterPanel", () => {
  let wrapper: VueWrapper;

  afterEach(() => {
    wrapper?.unmount();
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("renders the filter panel with header", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.find(".filter-panel").exists()).toBe(true);
      expect(wrapper.find(".filter-panel__title").text()).toBe("Filters");
    });

    it("renders reset button in header", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const resetButton = wrapper.find(".filter-panel__reset");
      expect(resetButton.exists()).toBe(true);
      expect(resetButton.text()).toBe("Reset");
    });

    it("renders search input", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const searchInput = wrapper.find('input#search[type="text"]');
      expect(searchInput.exists()).toBe(true);
      expect(searchInput.attributes("placeholder")).toBe("Find person...");
    });

    it("renders search label", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const label = wrapper.find('label[for="search"]');
      expect(label.exists()).toBe(true);
      expect(label.text()).toBe("Search");
    });
  });

  describe("node type filters", () => {
    it("renders Authors checkbox with indicator", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Authors");
      expect(wrapper.find(".filter-panel__checkbox-indicator--author").exists()).toBe(true);
    });

    it("renders Publishers checkbox with indicator", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Publishers");
      expect(wrapper.find(".filter-panel__checkbox-indicator--publisher").exists()).toBe(true);
    });

    it("renders Binders checkbox with indicator", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Binders");
      expect(wrapper.find(".filter-panel__checkbox-indicator--binder").exists()).toBe(true);
    });

    it("displays Node Types section title", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Node Types");
    });

    it("reflects showAuthors state in checkbox", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState({ showAuthors: true }) },
      });

      const authorsCheckbox = wrapper.find('[data-testid="filter-authors"] input[type="checkbox"]');
      expect((authorsCheckbox.element as HTMLInputElement).checked).toBe(true);
    });

    it("reflects showAuthors false state in checkbox", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState({ showAuthors: false }) },
      });

      const authorsCheckbox = wrapper.find('[data-testid="filter-authors"] input[type="checkbox"]');
      expect((authorsCheckbox.element as HTMLInputElement).checked).toBe(false);
    });

    it("reflects showPublishers state in checkbox", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState({ showPublishers: false }) },
      });

      const publishersCheckbox = wrapper.find(
        '[data-testid="filter-publishers"] input[type="checkbox"]'
      );
      expect((publishersCheckbox.element as HTMLInputElement).checked).toBe(false);
    });

    it("reflects showBinders state in checkbox", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState({ showBinders: false }) },
      });

      const bindersCheckbox = wrapper.find('[data-testid="filter-binders"] input[type="checkbox"]');
      expect((bindersCheckbox.element as HTMLInputElement).checked).toBe(false);
    });

    it("emits update:filter when Authors checkbox label clicked", async () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState({ showAuthors: true }) },
      });

      await wrapper.find('[data-testid="filter-authors"]').trigger("click");

      expect(wrapper.emitted("update:filter")).toBeTruthy();
      expect(wrapper.emitted("update:filter")![0]).toEqual(["showAuthors", false]);
    });

    it("emits update:filter when Publishers checkbox label clicked", async () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState({ showPublishers: true }) },
      });

      await wrapper.find('[data-testid="filter-publishers"]').trigger("click");

      expect(wrapper.emitted("update:filter")).toBeTruthy();
      expect(wrapper.emitted("update:filter")![0]).toEqual(["showPublishers", false]);
    });

    it("emits update:filter when Binders checkbox label clicked", async () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState({ showBinders: true }) },
      });

      await wrapper.find('[data-testid="filter-binders"]').trigger("click");

      expect(wrapper.emitted("update:filter")).toBeTruthy();
      expect(wrapper.emitted("update:filter")![0]).toEqual(["showBinders", false]);
    });
  });

  describe("connection type filters", () => {
    it("displays Connections section title", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Connections");
    });

    it("renders Published By connection filter", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Published By");
    });

    it("renders Shared Publisher connection filter", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Shared Publisher");
    });

    it("renders Same Bindery connection filter", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Same Bindery");
    });

    it("renders connection color indicators", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const colorIndicators = wrapper.findAll(".filter-panel__connection-color");
      // 3 book-based + 5 AI-discovered = 8 connection types
      expect(colorIndicators.length).toBe(8);
    });

    it("shows connection type as checked when in connectionTypes array", () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({
            connectionTypes: ["publisher", "shared_publisher", "binder"],
          }),
        },
      });

      const publisherCb = wrapper.find('[data-testid="filter-publisher"] input[type="checkbox"]');
      const sharedPubCb = wrapper.find(
        '[data-testid="filter-shared_publisher"] input[type="checkbox"]'
      );
      const binderCb = wrapper.find('[data-testid="filter-binder"] input[type="checkbox"]');
      expect((publisherCb.element as HTMLInputElement).checked).toBe(true);
      expect((sharedPubCb.element as HTMLInputElement).checked).toBe(true);
      expect((binderCb.element as HTMLInputElement).checked).toBe(true);
    });

    it("shows connection type as unchecked when not in connectionTypes array", () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({
            connectionTypes: ["publisher"],
          }),
        },
      });

      const publisherCb = wrapper.find('[data-testid="filter-publisher"] input[type="checkbox"]');
      const sharedPubCb = wrapper.find(
        '[data-testid="filter-shared_publisher"] input[type="checkbox"]'
      );
      const binderCb = wrapper.find('[data-testid="filter-binder"] input[type="checkbox"]');
      expect((publisherCb.element as HTMLInputElement).checked).toBe(true);
      expect((sharedPubCb.element as HTMLInputElement).checked).toBe(false);
      expect((binderCb.element as HTMLInputElement).checked).toBe(false);
    });

    it("emits update:filter with added connection type when checkbox clicked", async () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({
            connectionTypes: ["publisher"],
          }),
        },
      });

      await wrapper.find('[data-testid="filter-shared_publisher"]').trigger("click");

      expect(wrapper.emitted("update:filter")).toBeTruthy();
      expect(wrapper.emitted("update:filter")![0]).toEqual([
        "connectionTypes",
        ["publisher", "shared_publisher"],
      ]);
    });

    it("emits update:filter with removed connection type when checkbox clicked", async () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({
            connectionTypes: ["publisher", "shared_publisher", "binder"],
          }),
        },
      });

      await wrapper.find('[data-testid="filter-binder"]').trigger("click");

      expect(wrapper.emitted("update:filter")).toBeTruthy();
      expect(wrapper.emitted("update:filter")![0]).toEqual([
        "connectionTypes",
        ["publisher", "shared_publisher"],
      ]);
    });
  });

  describe("era filters", () => {
    it("displays Era section title", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Era");
    });

    it("renders Pre-Romantic era filter with date range", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Pre-Romantic");
      expect(wrapper.text()).toContain("1700-1789");
    });

    it("renders Romantic era filter with date range", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Romantic");
      expect(wrapper.text()).toContain("1789-1837");
    });

    it("renders Victorian era filter with date range", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Victorian");
      expect(wrapper.text()).toContain("1837-1901");
    });

    it("renders Edwardian era filter with date range", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Edwardian");
      expect(wrapper.text()).toContain("1901-1910");
    });

    it("renders Post 1910 era filter with date range", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Post 1910");
      expect(wrapper.text()).toContain("1910+");
    });

    it("shows all eras as checked when eras array is empty (all eras shown)", () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({ eras: [] }),
        },
      });

      const preRomanticCb = wrapper.find(
        '[data-testid="filter-era-pre_romantic"] input[type="checkbox"]'
      );
      const romanticCb = wrapper.find('[data-testid="filter-era-romantic"] input[type="checkbox"]');
      const victorianCb = wrapper.find(
        '[data-testid="filter-era-victorian"] input[type="checkbox"]'
      );
      const edwardianCb = wrapper.find(
        '[data-testid="filter-era-edwardian"] input[type="checkbox"]'
      );
      const post1910Cb = wrapper.find(
        '[data-testid="filter-era-post_1910"] input[type="checkbox"]'
      );
      expect((preRomanticCb.element as HTMLInputElement).checked).toBe(true);
      expect((romanticCb.element as HTMLInputElement).checked).toBe(true);
      expect((victorianCb.element as HTMLInputElement).checked).toBe(true);
      expect((edwardianCb.element as HTMLInputElement).checked).toBe(true);
      expect((post1910Cb.element as HTMLInputElement).checked).toBe(true);
    });

    it("shows specific eras as checked when in eras array", () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({
            eras: ["victorian", "edwardian"] as Era[],
          }),
        },
      });

      const preRomanticCb = wrapper.find(
        '[data-testid="filter-era-pre_romantic"] input[type="checkbox"]'
      );
      const romanticCb = wrapper.find('[data-testid="filter-era-romantic"] input[type="checkbox"]');
      const victorianCb = wrapper.find(
        '[data-testid="filter-era-victorian"] input[type="checkbox"]'
      );
      const edwardianCb = wrapper.find(
        '[data-testid="filter-era-edwardian"] input[type="checkbox"]'
      );
      const post1910Cb = wrapper.find(
        '[data-testid="filter-era-post_1910"] input[type="checkbox"]'
      );
      expect((preRomanticCb.element as HTMLInputElement).checked).toBe(false);
      expect((romanticCb.element as HTMLInputElement).checked).toBe(false);
      expect((victorianCb.element as HTMLInputElement).checked).toBe(true);
      expect((edwardianCb.element as HTMLInputElement).checked).toBe(true);
      expect((post1910Cb.element as HTMLInputElement).checked).toBe(false);
    });

    it("emits update:filter when era checkbox clicked to add era", async () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({
            eras: ["victorian"] as Era[],
          }),
        },
      });

      await wrapper.find('[data-testid="filter-era-romantic"]').trigger("click");

      expect(wrapper.emitted("update:filter")).toBeTruthy();
      expect(wrapper.emitted("update:filter")![0]).toEqual(["eras", ["victorian", "romantic"]]);
    });

    it("emits update:filter when era checkbox clicked to remove era", async () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({
            eras: ["victorian", "romantic"] as Era[],
          }),
        },
      });

      await wrapper.find('[data-testid="filter-era-victorian"]').trigger("click");

      expect(wrapper.emitted("update:filter")).toBeTruthy();
      expect(wrapper.emitted("update:filter")![0]).toEqual(["eras", ["romantic"]]);
    });

    it("renders era range elements with correct styling class", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const eraRanges = wrapper.findAll(".filter-panel__era-range");
      expect(eraRanges.length).toBe(5);
    });
  });

  describe("tier filter", () => {
    it("displays Tier section title", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Tier");
    });

    it("renders Tier 1 Only checkbox", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.text()).toContain("Tier 1 Only");
    });

    it("renders help text for tier filter", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const helpText = wrapper.find(".filter-panel__help");
      expect(helpText.exists()).toBe(true);
      expect(helpText.text()).toContain("major authors");
      expect(helpText.text()).toContain("established publishers");
    });

    it("shows tier1Only checkbox as checked when true", () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({ tier1Only: true }),
        },
      });

      const tierCb = wrapper.find('[data-testid="filter-tier1"] input[type="checkbox"]');
      expect((tierCb.element as HTMLInputElement).checked).toBe(true);
    });

    it("shows tier1Only checkbox as unchecked when false", () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({ tier1Only: false }),
        },
      });

      const tierCb = wrapper.find('[data-testid="filter-tier1"] input[type="checkbox"]');
      expect((tierCb.element as HTMLInputElement).checked).toBe(false);
    });

    it("emits update:filter when tier1Only checkbox clicked", async () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({ tier1Only: false }),
        },
      });

      await wrapper.find('[data-testid="filter-tier1"]').trigger("click");

      expect(wrapper.emitted("update:filter")).toBeTruthy();
      expect(wrapper.emitted("update:filter")![0]).toEqual(["tier1Only", true]);
    });
  });

  describe("search functionality", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("reflects searchQuery in input value", () => {
      wrapper = mount(FilterPanel, {
        props: {
          filterState: createDefaultFilterState({ searchQuery: "Dickens" }),
        },
      });

      const searchInput = wrapper.find("input#search");
      expect((searchInput.element as HTMLInputElement).value).toBe("Dickens");
    });

    it("emits update:filter with debounced search query", async () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const searchInput = wrapper.find("input#search");
      await searchInput.setValue("Charles");
      await searchInput.trigger("input");

      // Should not emit immediately
      expect(wrapper.emitted("update:filter")).toBeFalsy();

      // Fast-forward debounce timer
      vi.advanceTimersByTime(200);

      expect(wrapper.emitted("update:filter")).toBeTruthy();
      expect(wrapper.emitted("update:filter")![0]).toEqual(["searchQuery", "Charles"]);
    });

    it("debounces multiple rapid search inputs", async () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const searchInput = wrapper.find("input#search");

      // Type characters rapidly
      await searchInput.setValue("C");
      await searchInput.trigger("input");
      vi.advanceTimersByTime(50);

      await searchInput.setValue("Ch");
      await searchInput.trigger("input");
      vi.advanceTimersByTime(50);

      await searchInput.setValue("Cha");
      await searchInput.trigger("input");
      vi.advanceTimersByTime(50);

      await searchInput.setValue("Char");
      await searchInput.trigger("input");

      // Wait for debounce
      vi.advanceTimersByTime(200);

      // Should only emit once with final value
      expect(wrapper.emitted("update:filter")).toHaveLength(1);
      expect(wrapper.emitted("update:filter")![0]).toEqual(["searchQuery", "Char"]);
    });

    it("updates local search when prop changes externally", async () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState({ searchQuery: "" }) },
      });

      await wrapper.setProps({
        filterState: createDefaultFilterState({ searchQuery: "External" }),
      });

      const searchInput = wrapper.find("input#search");
      expect((searchInput.element as HTMLInputElement).value).toBe("External");
    });
  });

  describe("reset functionality", () => {
    it("emits reset event when reset button clicked", async () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      await wrapper.find(".filter-panel__reset").trigger("click");

      expect(wrapper.emitted("reset")).toBeTruthy();
      expect(wrapper.emitted("reset")).toHaveLength(1);
    });

    it("clears local search query when reset clicked", async () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState({ searchQuery: "Dickens" }) },
      });

      await wrapper.find(".filter-panel__reset").trigger("click");

      const searchInput = wrapper.find("input#search");
      expect((searchInput.element as HTMLInputElement).value).toBe("");
    });
  });

  describe("structure and layout", () => {
    it("has correct number of filter sections", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const sections = wrapper.findAll(".filter-panel__section");
      // Search, Node Types, Connections, Era, Tier
      expect(sections.length).toBe(5);
    });

    it("has correct number of section titles", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const sectionTitles = wrapper.findAll(".filter-panel__section-title");
      // Node Types, Connections, Era, Tier (Search section has a label, not section-title)
      expect(sectionTitles.length).toBe(4);
    });

    it("renders content area with scrollable container", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.find(".filter-panel__content").exists()).toBe(true);
    });

    it("renders as aside element", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      expect(wrapper.element.tagName).toBe("ASIDE");
    });
  });

  describe("checkbox behavior", () => {
    it("prevents default on label click to use custom toggle", async () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const mockEvent = { preventDefault: vi.fn() };

      // The component uses @click.prevent, so we verify the emit happens
      await wrapper.find('[data-testid="filter-authors"]').trigger("click", mockEvent);

      expect(wrapper.emitted("update:filter")).toBeTruthy();
    });

    it("renders checkbox input elements with correct type", () => {
      wrapper = mount(FilterPanel, {
        props: { filterState: createDefaultFilterState() },
      });

      const checkboxes = wrapper.findAll('input[type="checkbox"]');
      // 3 node types + 8 connection types + 5 eras + 1 tier = 17 checkboxes
      expect(checkboxes.length).toBe(17);
    });
  });
});
