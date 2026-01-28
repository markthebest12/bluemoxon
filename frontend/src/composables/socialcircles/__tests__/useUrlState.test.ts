import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useUrlState } from "../useUrlState";
import { ANIMATION } from "@/constants/socialCircles";

// Mock vue-router
const mockReplace = vi.fn();
const mockIsReady = vi.fn().mockResolvedValue(undefined);

vi.mock("vue-router", () => ({
  useRouter: () => ({
    replace: mockReplace,
    isReady: mockIsReady,
  }),
  useRoute: () => ({
    query: {},
  }),
}));

describe("useUrlState", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
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
      expect(mockReplace).not.toHaveBeenCalled();

      // Fast forward past debounce
      vi.advanceTimersByTime(100);

      // Only the last update should have been applied
      expect(mockReplace).toHaveBeenCalledTimes(1);
      expect(mockReplace).toHaveBeenCalledWith({
        query: { year: "1870" },
      });
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
      expect(mockReplace).not.toHaveBeenCalled();
    });

    it("should update URL when isPlaying is false", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      // Update with isPlaying = false (explicitly)
      updateUrl({ year: 1850, isPlaying: false });

      // Fast forward past debounce
      vi.advanceTimersByTime(100);

      // Should have updated URL
      expect(mockReplace).toHaveBeenCalledTimes(1);
    });

    it("should update URL when isPlaying is undefined (default)", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      // Update without isPlaying parameter
      updateUrl({ year: 1850 });

      // Fast forward past debounce
      vi.advanceTimersByTime(100);

      // Should have updated URL
      expect(mockReplace).toHaveBeenCalledTimes(1);
    });

    it("should resume URL updates when playback stops", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      // Update during playback (should be skipped)
      updateUrl({ year: 1850, isPlaying: true });
      vi.advanceTimersByTime(100);
      expect(mockReplace).not.toHaveBeenCalled();

      // Playback stops, update final position
      updateUrl({ year: 1880, isPlaying: false });
      vi.advanceTimersByTime(100);

      // Now the URL should update with the final year
      expect(mockReplace).toHaveBeenCalledTimes(1);
      expect(mockReplace).toHaveBeenCalledWith({
        query: { year: "1880" },
      });
    });
  });

  describe("filter URL encoding", () => {
    it("should encode filters in URL query params", async () => {
      const { updateUrl, initialize } = useUrlState();
      await initialize();

      updateUrl({
        filters: {
          showAuthors: false,
          showPublishers: true,
          showBinders: true,
          tier1Only: true,
          searchQuery: "dickens",
          connectionTypes: ["publisher"],
          eras: ["victorian"],
        },
      });

      vi.advanceTimersByTime(100);

      expect(mockReplace).toHaveBeenCalledWith({
        query: expect.objectContaining({
          authors: "false",
          tier1: "true",
          search: "dickens",
          connections: "publisher",
          eras: "victorian",
        }),
      });
    });
  });
});
