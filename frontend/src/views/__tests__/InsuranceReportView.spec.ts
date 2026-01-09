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
      expect(dataRow).toContain("Victorian Mid"); // era computed from year_start 1865
      expect(dataRow).toContain("No"); // is_complete = false (for "Complete Set")
      expect(dataRow).toContain("92"); // overall_score
      expect(dataRow).toContain("https://ebay.com/item/123"); // source_url
      expect(dataRow).toContain("2024-06-20"); // created_at (date portion)
    });

    it("computes era correctly from year_start", async () => {
      // Test Victorian Early (1837-1850)
      vi.mocked(api.get).mockResolvedValue({
        data: {
          items: [
            { id: 1, title: "Early Victorian", status: "ON_HAND", volumes: 1, year_start: 1845 },
            { id: 2, title: "Mid Victorian", status: "ON_HAND", volumes: 1, year_start: 1860 },
            { id: 3, title: "Late Victorian", status: "ON_HAND", volumes: 1, year_start: 1890 },
            { id: 4, title: "1920s Book", status: "ON_HAND", volumes: 1, year_start: 1925 },
            { id: 5, title: "No Year", status: "ON_HAND", volumes: 1, year_start: null },
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

      // Row 1 (Early Victorian 1845) should have "Victorian Early"
      expect(rows[1]).toContain("Victorian Early");
      // Row 2 (Mid Victorian 1860) should have "Victorian Mid"
      expect(rows[2]).toContain("Victorian Mid");
      // Row 3 (Late Victorian 1890) should have "Victorian Late"
      expect(rows[3]).toContain("Victorian Late");
      // Row 4 (1920s) should have "1920s"
      expect(rows[4]).toContain("1920s");
      // Row 5 (No year) should have empty era or "-"
    });

    it("computes era boundaries correctly", async () => {
      // Test ALL boundary values for Victorian era ranges:
      // Victorian Early: 1837-1850
      // Victorian Mid: 1851-1870
      // Victorian Late: 1871-1901
      // NOTE: Books are sorted by value_mid descending, so we assign value_mid
      // in reverse order to preserve our test order in CSV output
      vi.mocked(api.get).mockResolvedValue({
        data: {
          items: [
            // Victorian Early boundaries
            {
              id: 1,
              title: "Book 1836",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1836,
              value_mid: 1200,
            },
            {
              id: 2,
              title: "Book 1837",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1837,
              value_mid: 1100,
            },
            {
              id: 3,
              title: "Book 1850",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1850,
              value_mid: 1000,
            },
            // Victorian Mid boundaries
            {
              id: 4,
              title: "Book 1851",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1851,
              value_mid: 900,
            },
            {
              id: 5,
              title: "Book 1870",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1870,
              value_mid: 800,
            },
            // Victorian Late boundaries
            {
              id: 6,
              title: "Book 1871",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1871,
              value_mid: 700,
            },
            {
              id: 7,
              title: "Book 1901",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1901,
              value_mid: 600,
            },
            {
              id: 8,
              title: "Book 1902",
              status: "ON_HAND",
              volumes: 1,
              year_start: 1902,
              value_mid: 500,
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

      // Helper to find the row containing a specific title and check if it contains the expected era
      const findRowWithTitle = (title: string): string => {
        const row = rows.find((r) => r.includes(`"${title}"`));
        expect(row).toBeDefined();
        return row!;
      };

      // Victorian Early boundaries
      // 1836 - just before Victorian era -> decade format "1830s"
      expect(findRowWithTitle("Book 1836")).toContain('"1830s"');

      // 1837 - START of Victorian Early
      expect(findRowWithTitle("Book 1837")).toContain('"Victorian Early"');

      // 1850 - END of Victorian Early
      expect(findRowWithTitle("Book 1850")).toContain('"Victorian Early"');

      // Victorian Mid boundaries
      // 1851 - START of Victorian Mid
      expect(findRowWithTitle("Book 1851")).toContain('"Victorian Mid"');

      // 1870 - END of Victorian Mid
      expect(findRowWithTitle("Book 1870")).toContain('"Victorian Mid"');

      // Victorian Late boundaries
      // 1871 - START of Victorian Late
      expect(findRowWithTitle("Book 1871")).toContain('"Victorian Late"');

      // 1901 - END of Victorian Late
      expect(findRowWithTitle("Book 1901")).toContain('"Victorian Late"');

      // 1902 - just after Victorian era -> decade format "1900s"
      expect(findRowWithTitle("Book 1902")).toContain('"1900s"');

      // Edge cases
      // 0 - year zero is falsy, returns empty string (era column will be empty)
      const zeroRow = findRowWithTitle("Book zero");
      // Since era is empty, we check that it doesn't contain any Victorian era labels
      expect(zeroRow).not.toContain("Victorian");
      expect(zeroRow).not.toContain("0s"); // Should not have decade format for 0

      // 2024 - modern year -> decade format "2020s"
      expect(findRowWithTitle("Book modern")).toContain('"2020s"');

      // null year -> empty string (no era)
      const nullRow = findRowWithTitle("Book null");
      expect(nullRow).not.toContain("Victorian");
    });
  });
});
