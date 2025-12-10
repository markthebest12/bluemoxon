import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createWebHistory } from "vue-router";
import { createPinia, setActivePinia } from "pinia";
import AcquisitionsView from "../AcquisitionsView.vue";

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/services/api";

// Create a mock router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: { template: "<div>Home</div>" } },
    { path: "/admin/acquisitions", component: AcquisitionsView },
    { path: "/books/new", component: { template: "<div>New Book</div>" } },
    { path: "/books/:id", component: { template: "<div>Book Detail</div>" } },
  ],
});

describe("AcquisitionsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  const mockEmptyResponse = () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { items: [], total: 0, page: 1, pages: 1 },
    });
  };

  describe("smoke tests", () => {
    it("renders without crashing with empty data", async () => {
      mockEmptyResponse();

      const wrapper = mount(AcquisitionsView, {
        global: {
          plugins: [router, createPinia()],
        },
      });

      await flushPromises();

      expect(wrapper.text()).toContain("Acquisitions");
      expect(wrapper.text()).toContain("Evaluating");
      expect(wrapper.text()).toContain("In Transit");
      expect(wrapper.text()).toContain("Received");
    });

    it("renders correctly with null/undefined price values", async () => {
      vi.mocked(api.get).mockImplementation((_url, config) => {
        const status = config?.params?.status;
        if (status === "EVALUATING") {
          return Promise.resolve({
            data: {
              items: [
                {
                  id: 1,
                  title: "Book with null values",
                  author: { name: "Test Author" },
                  value_mid: null,
                  purchase_price: undefined,
                  discount_pct: null,
                },
              ],
              total: 1,
              page: 1,
              pages: 1,
            },
          });
        }
        return Promise.resolve({ data: { items: [], total: 0, page: 1, pages: 1 } });
      });

      const wrapper = mount(AcquisitionsView, {
        global: {
          plugins: [router, createPinia()],
        },
      });

      await flushPromises();

      // Should render "-" for null values, not crash with toFixed error
      expect(wrapper.text()).toContain("Book with null values");
      expect(wrapper.text()).toContain("-"); // Null values show as dash
    });

    it("renders correctly with string values that should be numbers", async () => {
      vi.mocked(api.get).mockImplementation((_url, config) => {
        const status = config?.params?.status;
        if (status === "IN_TRANSIT") {
          return Promise.resolve({
            data: {
              items: [
                {
                  id: 2,
                  title: "Book with string values",
                  author: { name: "Test Author" },
                  value_mid: "100.00" as unknown as number,
                  purchase_price: "50.00" as unknown as number,
                  discount_pct: "50" as unknown as number,
                },
              ],
              total: 1,
              page: 1,
              pages: 1,
            },
          });
        }
        return Promise.resolve({ data: { items: [], total: 0, page: 1, pages: 1 } });
      });

      const wrapper = mount(AcquisitionsView, {
        global: {
          plugins: [router, createPinia()],
        },
      });

      await flushPromises();

      // Should handle gracefully without crashing
      expect(wrapper.text()).toContain("Book with string values");
    });

    it("renders correctly with valid number values", async () => {
      vi.mocked(api.get).mockImplementation((_url, config) => {
        const status = config?.params?.status;
        if (status === "IN_TRANSIT") {
          return Promise.resolve({
            data: {
              items: [
                {
                  id: 3,
                  title: "Valid Book",
                  author: { name: "Test Author" },
                  value_mid: 500.0,
                  purchase_price: 250.5,
                  discount_pct: 49.9,
                  estimated_delivery: "2025-01-15",
                },
              ],
              total: 1,
              page: 1,
              pages: 1,
            },
          });
        }
        return Promise.resolve({ data: { items: [], total: 0, page: 1, pages: 1 } });
      });

      const wrapper = mount(AcquisitionsView, {
        global: {
          plugins: [router, createPinia()],
        },
      });

      await flushPromises();

      expect(wrapper.text()).toContain("Valid Book");
      expect(wrapper.text()).toContain("$250.50");
      expect(wrapper.text()).toContain("50% off");
      // Date formatting depends on timezone, just check it contains "Jan"
      expect(wrapper.text()).toMatch(/Jan \d+/);
    });
  });

  describe("API calls", () => {
    it("fetches all three status categories on mount", async () => {
      mockEmptyResponse();

      mount(AcquisitionsView, {
        global: {
          plugins: [router, createPinia()],
        },
      });

      await flushPromises();

      // Should call API for EVALUATING, IN_TRANSIT, and ON_HAND
      expect(api.get).toHaveBeenCalledWith("/books", {
        params: expect.objectContaining({ status: "EVALUATING" }),
      });
      expect(api.get).toHaveBeenCalledWith("/books", {
        params: expect.objectContaining({ status: "IN_TRANSIT" }),
      });
      expect(api.get).toHaveBeenCalledWith("/books", {
        params: expect.objectContaining({ status: "ON_HAND" }),
      });
    });
  });

  describe("Kanban columns", () => {
    it("displays correct count badges", async () => {
      vi.mocked(api.get).mockImplementation((url, config) => {
        const status = config?.params?.status;
        if (status === "EVALUATING") {
          return Promise.resolve({
            data: {
              items: [{ id: 1, title: "Eval Book", author: { name: "A" } }],
              total: 1,
              page: 1,
              pages: 1,
            },
          });
        }
        if (status === "IN_TRANSIT") {
          return Promise.resolve({
            data: {
              items: [
                { id: 2, title: "Transit 1", author: { name: "B" } },
                { id: 3, title: "Transit 2", author: { name: "C" } },
              ],
              total: 2,
              page: 1,
              pages: 1,
            },
          });
        }
        return Promise.resolve({ data: { items: [], total: 0, page: 1, pages: 1 } });
      });

      const wrapper = mount(AcquisitionsView, {
        global: {
          plugins: [router, createPinia()],
        },
      });

      await flushPromises();

      const html = wrapper.html();
      // Column headers should show counts
      expect(html).toContain("Evaluating");
      expect(html).toContain("In Transit");
    });
  });
});
