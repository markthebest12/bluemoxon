import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import OrphanCleanupPanel from "../OrphanCleanupPanel.vue";
import { api } from "@/services/api";

// Mock the API
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockScanResult = {
  total_count: 15,
  total_bytes: 5242880, // 5 MB
  orphans_by_book: [
    {
      folder_id: 1,
      book_id: 1,
      book_title: "Victorian Poetry Collection",
      count: 10,
      bytes: 3145728,
      keys: ["books/1/img1.jpg", "books/1/img2.jpg"],
    },
    {
      folder_id: 2,
      book_id: null,
      book_title: null,
      count: 5,
      bytes: 2097152,
      keys: ["books/2/img1.jpg"],
    },
  ],
};

const mockEmptyScanResult = {
  total_count: 0,
  total_bytes: 0,
  orphans_by_book: [],
};

describe("OrphanCleanupPanel", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(api.get).mockReset();
    vi.mocked(api.post).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe("initial state", () => {
    it("renders scan button initially", () => {
      const wrapper = mount(OrphanCleanupPanel);

      expect(wrapper.find('[data-testid="scan-button"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="scan-button"]').text()).toContain("Scan for Orphans");
    });

    it("does not show results initially", () => {
      const wrapper = mount(OrphanCleanupPanel);

      expect(wrapper.find('[data-testid="scan-results"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="delete-button"]').exists()).toBe(false);
    });
  });

  describe("scanning", () => {
    it("shows loading state while scanning", async () => {
      // Mock a slow API call
      vi.mocked(api.get).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: mockScanResult }), 1000))
      );

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");

      expect(wrapper.find('[data-testid="scan-button"]').text()).toContain("Scanning...");
      expect(wrapper.find('[data-testid="scan-button"]').attributes("disabled")).toBeDefined();
    });

    it("displays scan results after scanning", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();

      expect(wrapper.find('[data-testid="scan-results"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="orphan-count"]').text()).toBe("15");
      expect(wrapper.find('[data-testid="orphan-size"]').text()).toBe("5.0 MB");
      expect(wrapper.find('[data-testid="orphan-cost"]').text()).toContain("$");
    });

    it("shows no orphans message when storage is clean", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockEmptyScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();

      expect(wrapper.find('[data-testid="no-orphans"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="delete-button"]').exists()).toBe(false);
    });

    it("handles scan errors gracefully", async () => {
      vi.mocked(api.get).mockRejectedValue(new Error("Network error"));

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();

      expect(wrapper.text()).toContain("Network error");
    });
  });

  describe("expandable details", () => {
    it("shows toggle details button after scan", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();

      expect(wrapper.find('[data-testid="toggle-details"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="toggle-details"]').text()).toContain("Show Details");
    });

    it("expands details when clicked", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();

      expect(wrapper.find('[data-testid="orphan-details"]').exists()).toBe(false);

      await wrapper.find('[data-testid="toggle-details"]').trigger("click");

      expect(wrapper.find('[data-testid="orphan-details"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="toggle-details"]').text()).toContain("Hide Details");
    });

    it("shows orphans grouped by book in details", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();
      await wrapper.find('[data-testid="toggle-details"]').trigger("click");

      const details = wrapper.find('[data-testid="orphan-details"]');
      expect(details.text()).toContain("Victorian Poetry Collection");
      expect(details.text()).toContain("Deleted book");
    });
  });

  describe("delete confirmation", () => {
    it("shows confirmation when delete clicked", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();

      await wrapper.find('[data-testid="delete-button"]').trigger("click");

      expect(wrapper.find('[data-testid="confirm-delete"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="cancel-delete"]').exists()).toBe(true);
      expect(wrapper.text()).toContain("Delete all orphaned images?");
    });

    it("cancels confirmation when cancel clicked", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();
      await wrapper.find('[data-testid="delete-button"]').trigger("click");
      await wrapper.find('[data-testid="cancel-delete"]').trigger("click");

      expect(wrapper.find('[data-testid="confirm-delete"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="delete-button"]').exists()).toBe(true);
    });
  });

  describe("deletion progress", () => {
    it("shows progress during deletion", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockScanResult });
      vi.mocked(api.post).mockResolvedValue({ data: { job_id: "test-job-123" } });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();
      await wrapper.find('[data-testid="delete-button"]').trigger("click");
      await wrapper.find('[data-testid="confirm-delete"]').trigger("click");
      await flushPromises();

      expect(wrapper.find('[data-testid="delete-progress"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="progress-bar"]').exists()).toBe(true);
    });

    it("starts polling after delete request", async () => {
      vi.mocked(api.get)
        .mockResolvedValueOnce({ data: mockScanResult })
        .mockResolvedValue({
          data: {
            job_id: "test-job-123",
            status: "running",
            progress_pct: 50,
            total_count: 15,
            total_bytes: 5242880,
            deleted_count: 7,
            deleted_bytes: 2621440,
          },
        });
      vi.mocked(api.post).mockResolvedValue({ data: { job_id: "test-job-123" } });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();
      await wrapper.find('[data-testid="delete-button"]').trigger("click");
      await wrapper.find('[data-testid="confirm-delete"]').trigger("click");
      await flushPromises();

      // Polling should have started
      await vi.advanceTimersByTimeAsync(0);
      await flushPromises();

      expect(api.get).toHaveBeenCalledWith("/admin/cleanup/jobs/test-job-123");
    });
  });

  describe("completion", () => {
    it("shows completion summary when done", async () => {
      vi.mocked(api.get)
        .mockResolvedValueOnce({ data: mockScanResult })
        .mockResolvedValue({
          data: {
            job_id: "test-job-123",
            status: "completed",
            progress_pct: 100,
            total_count: 15,
            total_bytes: 5242880,
            deleted_count: 15,
            deleted_bytes: 5242880,
          },
        });
      vi.mocked(api.post).mockResolvedValue({ data: { job_id: "test-job-123" } });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();
      await wrapper.find('[data-testid="delete-button"]').trigger("click");
      await wrapper.find('[data-testid="confirm-delete"]').trigger("click");
      await flushPromises();

      await vi.advanceTimersByTimeAsync(0);
      await flushPromises();

      expect(wrapper.find('[data-testid="delete-complete"]').exists()).toBe(true);
      expect(wrapper.text()).toContain("Cleanup Complete");
      expect(wrapper.text()).toContain("15");
      expect(wrapper.text()).toContain("5.0 MB");
    });

    it("resets to initial state after clicking done", async () => {
      vi.mocked(api.get)
        .mockResolvedValueOnce({ data: mockScanResult })
        .mockResolvedValue({
          data: {
            job_id: "test-job-123",
            status: "completed",
            progress_pct: 100,
            total_count: 15,
            total_bytes: 5242880,
            deleted_count: 15,
            deleted_bytes: 5242880,
          },
        });
      vi.mocked(api.post).mockResolvedValue({ data: { job_id: "test-job-123" } });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="scan-button"]').trigger("click");
      await flushPromises();
      await wrapper.find('[data-testid="delete-button"]').trigger("click");
      await wrapper.find('[data-testid="confirm-delete"]').trigger("click");
      await flushPromises();

      await vi.advanceTimersByTimeAsync(0);
      await flushPromises();

      await wrapper.find('[data-testid="done-button"]').trigger("click");

      expect(wrapper.find('[data-testid="scan-button"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="delete-complete"]').exists()).toBe(false);
    });
  });

  describe("listings cleanup", () => {
    const mockListingsScanResult = {
      total_count: 10,
      total_bytes: 5000,
      age_threshold_days: 30,
      listings_by_item: [
        { item_id: "123456789", count: 5, bytes: 2500, oldest: "2025-12-01T00:00:00Z" },
        { item_id: "987654321", count: 5, bytes: 2500, oldest: "2025-11-15T00:00:00Z" },
      ],
    };

    const mockEmptyListingsScanResult = {
      total_count: 0,
      total_bytes: 0,
      age_threshold_days: 30,
      listings_by_item: [],
    };

    it("renders listings scan button initially", () => {
      const wrapper = mount(OrphanCleanupPanel);

      expect(wrapper.find('[data-testid="listings-scan-button"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="listings-scan-button"]').text()).toContain(
        "Scan for Stale Listings"
      );
    });

    it("shows loading state while scanning listings", async () => {
      vi.mocked(api.get).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(() => resolve({ data: mockListingsScanResult }), 1000)
          )
      );

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");

      expect(wrapper.find('[data-testid="listings-scan-button"]').text()).toContain("Scanning...");
      expect(
        wrapper.find('[data-testid="listings-scan-button"]').attributes("disabled")
      ).toBeDefined();
    });

    it("displays listings scan results after scanning", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockListingsScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");
      await flushPromises();

      expect(wrapper.find('[data-testid="listings-scan-results"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="listings-count"]').text()).toBe("10");
    });

    it("shows no stale listings message when count is 0", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockEmptyListingsScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");
      await flushPromises();

      expect(wrapper.find('[data-testid="listings-no-stale"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="listings-delete-button"]').exists()).toBe(false);
    });

    it("shows toggle details button after listings scan", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockListingsScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");
      await flushPromises();

      expect(wrapper.find('[data-testid="listings-toggle-details"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="listings-toggle-details"]').text()).toContain(
        "Show Details"
      );
    });

    it("expands listings details when clicked", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockListingsScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");
      await flushPromises();

      expect(wrapper.find('[data-testid="listings-details"]').exists()).toBe(false);

      await wrapper.find('[data-testid="listings-toggle-details"]').trigger("click");

      expect(wrapper.find('[data-testid="listings-details"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="listings-toggle-details"]').text()).toContain(
        "Hide Details"
      );
    });

    it("shows listings grouped by item_id in details", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockListingsScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");
      await flushPromises();
      await wrapper.find('[data-testid="listings-toggle-details"]').trigger("click");

      const details = wrapper.find('[data-testid="listings-details"]');
      expect(details.text()).toContain("123456789");
      expect(details.text()).toContain("987654321");
    });

    it("shows confirmation when listings delete clicked", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockListingsScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");
      await flushPromises();

      await wrapper.find('[data-testid="listings-delete-button"]').trigger("click");

      expect(wrapper.find('[data-testid="listings-confirm-delete"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="listings-cancel-delete"]').exists()).toBe(true);
      expect(wrapper.text()).toContain("Delete all stale listing images?");
    });

    it("cancels listings confirmation when cancel clicked", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockListingsScanResult });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");
      await flushPromises();
      await wrapper.find('[data-testid="listings-delete-button"]').trigger("click");
      await wrapper.find('[data-testid="listings-cancel-delete"]').trigger("click");

      expect(wrapper.find('[data-testid="listings-confirm-delete"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="listings-delete-button"]').exists()).toBe(true);
    });

    it("shows completion summary after listings deletion", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockListingsScanResult });
      vi.mocked(api.post).mockResolvedValue({
        data: { deleted_count: 10, total_bytes: 5000 },
      });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");
      await flushPromises();
      await wrapper.find('[data-testid="listings-delete-button"]').trigger("click");
      await wrapper.find('[data-testid="listings-confirm-delete"]').trigger("click");
      await flushPromises();

      expect(wrapper.find('[data-testid="listings-delete-complete"]').exists()).toBe(true);
      expect(wrapper.text()).toContain("Listings Cleanup Complete");
      expect(wrapper.text()).toContain("10");
    });

    it("resets to initial state after clicking listings done", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockListingsScanResult });
      vi.mocked(api.post).mockResolvedValue({
        data: { deleted_count: 10, total_bytes: 5000 },
      });

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");
      await flushPromises();
      await wrapper.find('[data-testid="listings-delete-button"]').trigger("click");
      await wrapper.find('[data-testid="listings-confirm-delete"]').trigger("click");
      await flushPromises();

      await wrapper.find('[data-testid="listings-done-button"]').trigger("click");

      expect(wrapper.find('[data-testid="listings-scan-button"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="listings-delete-complete"]').exists()).toBe(false);
    });

    it("handles listings scan errors gracefully", async () => {
      vi.mocked(api.get).mockRejectedValue(new Error("Network error"));

      const wrapper = mount(OrphanCleanupPanel);
      await wrapper.find('[data-testid="listings-scan-button"]').trigger("click");
      await flushPromises();

      expect(wrapper.text()).toContain("Network error");
    });
  });
});
