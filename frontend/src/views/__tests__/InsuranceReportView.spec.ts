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

  describe("CSV export fields", () => {
    // Helper to set up CSV capture mocks - captures CSV content via Blob constructor
    function setupCSVCapture(): { getCSV: () => string; cleanup: () => void } {
      let capturedCSV = "";
      const originalBlob = global.Blob;

      global.Blob = class MockBlob extends originalBlob {
        constructor(parts: BlobPart[], options?: BlobPropertyBag) {
          super(parts, options);
          if (options?.type === "text/csv;charset=utf-8;") {
            capturedCSV = parts.join("");
          }
        }
      } as typeof Blob;

      // Mock link element behavior
      const originalCreateElement = document.createElement.bind(document);
      vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
        if (tag === "a") {
          return {
            setAttribute: vi.fn(),
            click: vi.fn(),
            style: { visibility: "" },
          } as unknown as HTMLElement;
        }
        return originalCreateElement(tag);
      });

      vi.spyOn(document.body, "appendChild").mockReturnValue(null as unknown as Node);
      vi.spyOn(document.body, "removeChild").mockReturnValue(null as unknown as Node);
      vi.spyOn(URL, "createObjectURL").mockReturnValue("mock-url");

      return {
        getCSV: () => capturedCSV,
        cleanup: () => {
          global.Blob = originalBlob;
          vi.restoreAllMocks();
        },
      };
    }

    it("includes all required CSV headers for new fields", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: {
          items: [
            {
              id: 1,
              title: "Test Book",
              status: "ON_HAND",
              volumes: 1,
              acquisition_cost: 150.0,
              is_first_edition: true,
              has_provenance: true,
              provenance_tier: "TIER_1",
              year_start: 1855,
              year_end: 1855,
              is_complete: true,
              overall_score: 85,
              source_url: "https://example.com/listing",
              created_at: "2024-01-15T10:30:00Z",
            },
          ],
          total: 1,
          page: 1,
          pages: 1,
        },
      });

      const wrapper = mount(InsuranceReportView, {
        global: { plugins: [router] },
      });

      await flushPromises();

      // Verify books are loaded
      const vm = wrapper.vm as unknown as { sortedBooks: { title: string }[] };
      expect(vm.sortedBooks.length).toBe(1);

      // Set up CSV capture
      const { getCSV, cleanup } = setupCSVCapture();

      // Find and click the Export CSV button
      const buttons = wrapper.findAll("button");
      const csvButton = buttons.find((b) => b.text().includes("Export CSV"));
      expect(csvButton).toBeDefined();
      await csvButton!.trigger("click");

      // Verify the CSV contains the new required headers
      const headers = getCSV().split("\n")[0];
      cleanup();

      expect(headers).toContain("Acquisition Cost");
      expect(headers).toContain("First Edition");
      expect(headers).toContain("Has Provenance");
      expect(headers).toContain("Provenance Tier");
      expect(headers).toContain("Year Start");
      expect(headers).toContain("Year End");
      expect(headers).toContain("Era");
      expect(headers).toContain("Complete Set");
      expect(headers).toContain("Overall Score");
      expect(headers).toContain("Source URL");
      expect(headers).toContain("Created At");
    });

    it("exports correct values for new fields", async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: {
          items: [
            {
              id: 1,
              title: "Victorian Gems",
              status: "ON_HAND",
              volumes: 3,
              acquisition_cost: 250.5,
              is_first_edition: true,
              has_provenance: true,
              provenance_tier: "TIER_2",
              year_start: 1865,
              year_end: 1867,
              is_complete: false,
              overall_score: 92,
              source_url: "https://ebay.com/item/123",
              created_at: "2024-06-20T14:45:00Z",
            },
          ],
          total: 1,
          page: 1,
          pages: 1,
        },
      });

      const wrapper = mount(InsuranceReportView, {
        global: { plugins: [router] },
      });

      await flushPromises();

      // Set up CSV capture
      const { getCSV, cleanup } = setupCSVCapture();

      const buttons = wrapper.findAll("button");
      const csvButton = buttons.find((b) => b.text().includes("Export CSV"));
      await csvButton!.trigger("click");

      // Verify the data row contains correct values
      const dataRow = getCSV().split("\n")[1];
      cleanup();

      expect(dataRow).toContain("250.5"); // acquisition_cost
      expect(dataRow).toContain("Yes"); // is_first_edition = true
      expect(dataRow).toContain("TIER_2"); // provenance_tier
      expect(dataRow).toContain("1865"); // year_start
      expect(dataRow).toContain("1867"); // year_end
      expect(dataRow).toContain("Victorian"); // era computed from year_start 1865 (unified era)
      expect(dataRow).toContain("No"); // is_complete = false (for "Complete Set")
      expect(dataRow).toContain("92"); // overall_score
      expect(dataRow).toContain("https://ebay.com/item/123"); // source_url
      expect(dataRow).toContain("2024-06-20"); // created_at (date portion)
    });

    it("computes era correctly from year_start using unified era logic", async () => {
      // Test unified eras matching backend:
      // Pre-Romantic (<1800), Romantic (1800-1836), Victorian (1837-1901),
      // Edwardian (1902-1910), Post-1910 (>1910), Unknown (null)
      vi.mocked(api.get).mockResolvedValue({
        data: {
          items: [
            { id: 1, title: "Romantic Book", status: "ON_HAND", volumes: 1, year_start: 1820 },
            { id: 2, title: "Victorian Book", status: "ON_HAND", volumes: 1, year_start: 1860 },
            { id: 3, title: "Edwardian Book", status: "ON_HAND", volumes: 1, year_start: 1905 },
            { id: 4, title: "Post-1910 Book", status: "ON_HAND", volumes: 1, year_start: 1925 },
            {
              id: 5,
              title: "No Year",
              status: "ON_HAND",
              volumes: 1,
              year_start: null,
              year_end: null,
            },
          ],
          total: 5,
          page: 1,
          pages: 1,
        },
      });

      const wrapper = mount(InsuranceReportView, {
        global: { plugins: [router] },
      });

      await flushPromises();

      // Set up CSV capture
      const { getCSV, cleanup } = setupCSVCapture();

      const buttons = wrapper.findAll("button");
      const csvButton = buttons.find((b) => b.text().includes("Export CSV"));
      await csvButton!.trigger("click");

      const rows = getCSV().split("\n");
      cleanup();

      // Row 1 (1820) should have "Romantic"
      expect(rows[1]).toContain("Romantic");
      // Row 2 (1860) should have "Victorian"
      expect(rows[2]).toContain("Victorian");
      // Row 3 (1905) should have "Edwardian"
      expect(rows[3]).toContain("Edwardian");
      // Row 4 (1925) should have "Post-1910"
      expect(rows[4]).toContain("Post-1910");
      // Row 5 (No year) should have "Unknown"
      expect(rows[5]).toContain("Unknown");
    });

    it("computes era boundaries correctly using unified backend eras", async () => {
      // Test ALL boundary values for unified eras (matching backend):
      // Pre-Romantic: <1800
      // Romantic: 1800-1836
      // Victorian: 1837-1901
      // Edwardian: 1902-1910
      // Post-1910: >1910
      // NOTE: Books are sorted by value_mid descending, so we assign value_mid
      // in reverse order to preserve our test order in CSV output
      vi.mocked(api.get).mockResolvedValue({
        data: {
          items: [
            // Pre-Romantic boundary
            {
              id: 1,
              title: "Book 1799",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1799,
              value_mid: 1400,
            },
            // Romantic boundaries
            {
              id: 2,
              title: "Book 1800",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1800,
              value_mid: 1300,
            },
            {
              id: 3,
              title: "Book 1836",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1836,
              value_mid: 1200,
            },
            // Victorian boundaries
            {
              id: 4,
              title: "Book 1837",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1837,
              value_mid: 1100,
            },
            {
              id: 5,
              title: "Book 1901",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1901,
              value_mid: 1000,
            },
            // Edwardian boundaries
            {
              id: 6,
              title: "Book 1902",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1902,
              value_mid: 900,
            },
            {
              id: 7,
              title: "Book 1910",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1910,
              value_mid: 800,
            },
            // Post-1910 boundary
            {
              id: 8,
              title: "Book 1911",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1911,
              value_mid: 700,
            },
            // Edge cases
            {
              id: 9,
              title: "Book zero",
              status: "ON_HAND",
              volumes: 1,
              year_start: 0,
              value_mid: 400,
            },
            {
              id: 10,
              title: "Book modern",
              status: "ON_HAND",
              volumes: 1,
              year_start: 2024,
              value_mid: 300,
            },
            {
              id: 11,
              title: "Book null",
              status: "ON_HAND",
              volumes: 1,
              year_start: null,
              year_end: null,
              value_mid: 200,
            },
          ],
          total: 11,
          page: 1,
          pages: 1,
        },
      });

      const wrapper = mount(InsuranceReportView, {
        global: { plugins: [router] },
      });

      await flushPromises();

      const { getCSV, cleanup } = setupCSVCapture();

      const buttons = wrapper.findAll("button");
      const csvButton = buttons.find((b) => b.text().includes("Export CSV"));
      await csvButton!.trigger("click");

      const csv = getCSV();
      const rows = csv.split("\n");
      cleanup();

      // Helper to find the row containing a specific title
      const findRowWithTitle = (title: string): string => {
        const row = rows.find((r) => r.includes(`"${title}"`));
        expect(row).toBeDefined();
        return row!;
      };

      // Pre-Romantic (before 1800)
      expect(findRowWithTitle("Book 1799")).toContain('"Pre-Romantic"');

      // Romantic boundaries (1800-1836)
      expect(findRowWithTitle("Book 1800")).toContain('"Romantic"');
      expect(findRowWithTitle("Book 1836")).toContain('"Romantic"');

      // Victorian boundaries (1837-1901)
      expect(findRowWithTitle("Book 1837")).toContain('"Victorian"');
      expect(findRowWithTitle("Book 1901")).toContain('"Victorian"');

      // Edwardian boundaries (1902-1910)
      expect(findRowWithTitle("Book 1902")).toContain('"Edwardian"');
      expect(findRowWithTitle("Book 1910")).toContain('"Edwardian"');

      // Post-1910 (after 1910)
      expect(findRowWithTitle("Book 1911")).toContain('"Post-1910"');

      // Edge cases
      // 0 - year zero is Pre-Romantic (< 1800)
      expect(findRowWithTitle("Book zero")).toContain('"Pre-Romantic"');

      // 2024 - modern year -> Post-1910
      expect(findRowWithTitle("Book modern")).toContain('"Post-1910"');

      // null year -> Unknown
      expect(findRowWithTitle("Book null")).toContain('"Unknown"');
    });
  });
});
