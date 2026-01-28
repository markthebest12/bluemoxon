import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useUrlState } from "../useUrlState";
import { ANIMATION } from "@/constants/socialCircles";

// Mock vue-router with configurable query
const mockIsReady = vi.fn().mockResolvedValue(undefined);
let mockRouteQuery: Record<string, string> = {};

vi.mock("vue-router", () => ({
  useRouter: () => ({
    isReady: mockIsReady,
  }),
  useRoute: () => ({
    query: mockRouteQuery,
  }),
}));

describe("useUrlState", () => {
  let historyReplaceSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockRouteQuery = {}; // Reset query between tests
    // Spy on history.replaceState
    historyReplaceSpy = vi.spyOn(window.history, "replaceState");
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe("debounce timing", () => {
    it("should use 100ms debounce (reduced from 300ms)", () => {
      // Verify the constant has been updated
      expect(ANIMATION.debounceUrl).toBe(100);
    });

    it("should debounce URL updates", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      // Make multiple rapid updates
      updateUrl({ year: 1850 });
      updateUrl({ year: 1860 });
      updateUrl({ year: 1870 });

      // No updates yet (debouncing)
      expect(historyReplaceSpy).not.toHaveBeenCalled();

      // Fast forward past debounce
      vi.advanceTimersByTime(100);

      // Only the last update should have been applied
      expect(historyReplaceSpy).toHaveBeenCalledTimes(1);
    });
  });

  describe("playback handling", () => {
    it("should skip URL updates when isPlaying is true", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      // Update with isPlaying = true
      updateUrl({ year: 1850, isPlaying: true });

      // Fast forward past debounce
      vi.advanceTimersByTime(100);

      // Should NOT have updated URL
      expect(historyReplaceSpy).not.toHaveBeenCalled();
    });

    it("should update URL when isPlaying is false", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      // Update with isPlaying = false (explicitly)
      updateUrl({ year: 1850, isPlaying: false });

      // Fast forward past debounce
      vi.advanceTimersByTime(100);

      // Should have updated URL
      expect(historyReplaceSpy).toHaveBeenCalledTimes(1);
    });

    it("should update URL when isPlaying is undefined (default)", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      // Update without isPlaying parameter
      updateUrl({ year: 1850 });

      // Fast forward past debounce
      vi.advanceTimersByTime(100);

      // Should have updated URL
      expect(historyReplaceSpy).toHaveBeenCalledTimes(1);
    });

    it("should resume URL updates when playback stops", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      // Update during playback (should be skipped)
      updateUrl({ year: 1850, isPlaying: true });
      vi.advanceTimersByTime(100);
      expect(historyReplaceSpy).not.toHaveBeenCalled();

      // Playback stops, update final position
      updateUrl({ year: 1880, isPlaying: false });
      vi.advanceTimersByTime(100);

      // Now the URL should update with the final year
      expect(historyReplaceSpy).toHaveBeenCalledTimes(1);
    });
  });

  describe("URL parsing", () => {
    it("should parse filters from URL query params", async () => {
      mockRouteQuery = {
        authors: "false",
        tier1: "true",
        search: "dickens",
        connections: "publisher,shared_publisher",
        eras: "victorian,romantic",
        year: "1850",
        selected: "author-123",
      };

      const { initialize } = useUrlState();
      const result = await initialize();

      expect(result.filters.showAuthors).toBe(false);
      expect(result.filters.tier1Only).toBe(true);
      expect(result.filters.searchQuery).toBe("dickens");
      expect(result.filters.connectionTypes).toEqual(["publisher", "shared_publisher"]);
      expect(result.filters.eras).toEqual(["victorian", "romantic"]);
      expect(result.year).toBe(1850);
      expect(result.selectedNode).toBe("author-123");
    });

    it("should handle year value of 0", async () => {
      mockRouteQuery = { year: "0" };

      const { initialize, updateUrl } = useUrlState();
      const result = await initialize();

      expect(result.year).toBe(0);

      // Also verify encoding works for year 0
      updateUrl({ year: 0 });
      vi.advanceTimersByTime(100);

      expect(historyReplaceSpy).toHaveBeenCalled();
      // Check URL contains year=0
      const url = historyReplaceSpy.mock.calls[0][2] as string;
      expect(url).toContain("year=0");
    });

    it("should filter invalid era values", async () => {
      mockRouteQuery = { eras: "victorian,invalid_era,romantic" };

      const { initialize } = useUrlState();
      const result = await initialize();

      expect(result.filters.eras).toEqual(["victorian", "romantic"]);
    });

    it("should filter invalid connection types", async () => {
      mockRouteQuery = { connections: "publisher,invalid_type,binder" };

      const { initialize } = useUrlState();
      const result = await initialize();

      expect(result.filters.connectionTypes).toEqual(["publisher", "binder"]);
    });
  });

  describe("scroll behavior fix (#1406)", () => {
    it("should use history.replaceState instead of router.replace to avoid scroll reset", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      // Call updateUrl with year parameter
      updateUrl({ year: 1850 });

      // Fast-forward past debounce
      vi.advanceTimersByTime(ANIMATION.debounceUrl + 10);

      // Should use history.replaceState (no scroll trigger)
      expect(historyReplaceSpy).toHaveBeenCalled();
    });

    it("should construct correct URL with query parameters", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      updateUrl({ year: 1850, selectedNode: "author:123" as never });

      vi.advanceTimersByTime(ANIMATION.debounceUrl + 10);

      // Check URL was constructed correctly
      const call = historyReplaceSpy.mock.calls[0];
      expect(call).toBeDefined();
      const [, , url] = call;
      expect(url).toContain("year=1850");
      expect(url).toContain("selected=author");
    });
  });
});
