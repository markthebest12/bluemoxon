import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { BOOK_STATUS_OPTIONS, BOOK_STATUSES } from "@/constants";
import BooksView from "../BooksView.vue";

// Mock vue-router
vi.mock("vue-router", () => ({
  useRoute: () => ({
    query: {},
  }),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

// Mock aws-amplify
vi.mock("aws-amplify/auth", () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({
    tokens: { idToken: { toString: () => "mock-token" } },
  }),
}));

describe("BooksView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  const mountComponent = (): VueWrapper => {
    return mount(BooksView, {
      global: {
        stubs: {
          BookThumbnail: true,
          BookCountBadge: true,
          ComboboxWithAdd: true,
          ImageCarousel: true,
          RouterLink: true,
          teleport: true,
        },
      },
    });
  };

  const expandFilters = async (wrapper: VueWrapper): Promise<void> => {
    const filterButton = wrapper.find('[data-testid="filter-toggle"]');
    if (filterButton.exists()) {
      await filterButton.trigger("click");
    }
  };

  describe("Status Filter Dropdown", () => {
    it("renders all status options from BOOK_STATUS_OPTIONS constant", async () => {
      const wrapper = mountComponent();
      await expandFilters(wrapper);

      // Find the status filter select element
      const statusSelect = wrapper.find('select[data-testid="status-filter"]');
      expect(statusSelect.exists()).toBe(true);

      // Get all options
      const options = statusSelect.findAll("option");

      // Should have "All Statuses" plus all 4 status options
      expect(options).toHaveLength(BOOK_STATUS_OPTIONS.length + 1);

      // First option should be "All Statuses" with empty value
      expect(options[0].text()).toBe("All Statuses");
      expect(options[0].attributes("value")).toBe("");

      // Verify all BOOK_STATUS_OPTIONS are present with correct values and labels
      BOOK_STATUS_OPTIONS.forEach((statusOption, index) => {
        const option = options[index + 1];
        expect(option.attributes("value")).toBe(statusOption.value);
        expect(option.text()).toBe(statusOption.label);
      });
    });

    it("includes EVALUATING status option", async () => {
      const wrapper = mountComponent();
      await expandFilters(wrapper);

      const statusSelect = wrapper.find('select[data-testid="status-filter"]');
      const options = statusSelect.findAll("option");
      const optionValues = options.map((o) => o.attributes("value"));

      expect(optionValues).toContain(BOOK_STATUSES.EVALUATING);
    });

    it("uses REMOVED status instead of hardcoded SOLD", async () => {
      const wrapper = mountComponent();
      await expandFilters(wrapper);

      const statusSelect = wrapper.find('select[data-testid="status-filter"]');
      const options = statusSelect.findAll("option");
      const optionValues = options.map((o) => o.attributes("value"));

      // Should NOT have hardcoded "SOLD"
      expect(optionValues).not.toContain("SOLD");

      // Should have REMOVED from the constant
      expect(optionValues).toContain(BOOK_STATUSES.REMOVED);
    });
  });
});
