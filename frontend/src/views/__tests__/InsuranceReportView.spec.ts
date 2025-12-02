import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createWebHistory } from "vue-router";
import InsuranceReportView from "../InsuranceReportView.vue";

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "@/services/api";

// Create a mock router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: { template: "<div>Home</div>" } },
    { path: "/books", component: { template: "<div>Books</div>" } },
    { path: "/reports/insurance", component: InsuranceReportView },
  ],
});

describe("InsuranceReportView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("API parameter validation", () => {
    it("uses per_page=100 (not exceeding API limit)", async () => {
      // Mock single page response
      vi.mocked(api.get).mockResolvedValue({
        data: {
          items: [],
          total: 0,
          page: 1,
          pages: 1,
        },
      });

      mount(InsuranceReportView, {
        global: {
          plugins: [router],
        },
      });

      await flushPromises();

      // Verify the first API call uses per_page=100 (API max limit)
      expect(api.get).toHaveBeenCalledWith("/books", {
        params: expect.objectContaining({
          per_page: 100,
        }),
      });

      // Verify it does NOT use per_page=500 (would cause 422 error)
      expect(api.get).not.toHaveBeenCalledWith("/books", {
        params: expect.objectContaining({
          per_page: 500,
        }),
      });
    });

    it("requests PRIMARY inventory type", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { items: [], total: 0, page: 1, pages: 1 },
      });

      mount(InsuranceReportView, {
        global: { plugins: [router] },
      });

      await flushPromises();

      expect(api.get).toHaveBeenCalledWith("/books", {
        params: expect.objectContaining({
          inventory_type: "PRIMARY",
        }),
      });
    });

    it("sorts by value_mid descending", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { items: [], total: 0, page: 1, pages: 1 },
      });

      mount(InsuranceReportView, {
        global: { plugins: [router] },
      });

      await flushPromises();

      expect(api.get).toHaveBeenCalledWith("/books", {
        params: expect.objectContaining({
          sort_by: "value_mid",
          sort_order: "desc",
        }),
      });
    });
  });

  describe("pagination handling", () => {
    it("fetches all pages when collection spans multiple pages", async () => {
      // Mock multi-page response
      vi.mocked(api.get)
        .mockResolvedValueOnce({
          data: {
            items: [{ id: 1, title: "Book 1", status: "ON_HAND", volumes: 1 }],
            total: 150,
            page: 1,
            pages: 2,
          },
        })
        .mockResolvedValueOnce({
          data: {
            items: [{ id: 2, title: "Book 2", status: "ON_HAND", volumes: 1 }],
            total: 150,
            page: 2,
            pages: 2,
          },
        });

      mount(InsuranceReportView, {
        global: { plugins: [router] },
      });

      await flushPromises();

      // Should have made 2 API calls (one per page)
      expect(api.get).toHaveBeenCalledTimes(2);

      // First call: page 1
      expect(api.get).toHaveBeenNthCalledWith(1, "/books", {
        params: expect.objectContaining({ page: 1 }),
      });

      // Second call: page 2
      expect(api.get).toHaveBeenNthCalledWith(2, "/books", {
        params: expect.objectContaining({ page: 2 }),
      });
    });

    it("stops fetching when last page is reached", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: {
          items: [{ id: 1, title: "Book 1", status: "ON_HAND", volumes: 1 }],
          total: 50,
          page: 1,
          pages: 1, // Only one page
        },
      });

      mount(InsuranceReportView, {
        global: { plugins: [router] },
      });

      await flushPromises();

      // Should only make 1 API call
      expect(api.get).toHaveBeenCalledTimes(1);
    });
  });

  describe("ON_HAND filtering", () => {
    it("filters to show only ON_HAND items for insurance", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: {
          items: [
            { id: 1, title: "On Hand Book", status: "ON_HAND", volumes: 1, value_mid: 100 },
            { id: 2, title: "In Transit Book", status: "IN_TRANSIT", volumes: 1, value_mid: 200 },
            { id: 3, title: "Sold Book", status: "SOLD", volumes: 1, value_mid: 300 },
          ],
          total: 3,
          page: 1,
          pages: 1,
        },
      });

      const wrapper = mount(InsuranceReportView, {
        global: { plugins: [router] },
      });

      await flushPromises();

      // The summary should only count ON_HAND items
      const html = wrapper.html();
      // Should show "1" for total items (only ON_HAND book)
      expect(html).toContain("On Hand Book");
      expect(html).not.toContain("In Transit Book");
      expect(html).not.toContain("Sold Book");
    });
  });
});
