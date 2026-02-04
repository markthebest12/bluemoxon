import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useEntityProfile } from "../useEntityProfile";
import { api } from "@/services/api";

vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("useEntityProfile", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(api.get).mockReset();
    vi.mocked(api.post).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("#1558: regenerateProfile sets loadingState on error", () => {
    it("sets loadingState to error when regenerate POST fails", async () => {
      vi.mocked(api.post).mockRejectedValueOnce(new Error("API failure"));

      const { regenerateProfile, loadingState, hasError, error } = useEntityProfile();

      await regenerateProfile("author", 1);

      expect(loadingState.value).toBe("error");
      expect(hasError.value).toBe(true);
      expect(error.value).toBe("API failure");
    });

    it("sets loadingState to error with default message for non-Error throws", async () => {
      vi.mocked(api.post).mockRejectedValueOnce("string error");

      const { regenerateProfile, loadingState, hasError } = useEntityProfile();

      await regenerateProfile("author", 1);

      expect(loadingState.value).toBe("error");
      expect(hasError.value).toBe(true);
    });
  });

  describe("#1551: AbortController cancels stale requests", () => {
    it("aborts previous request when fetchProfile is called again", async () => {
      const signals: AbortSignal[] = [];

      vi.mocked(api.get).mockImplementation((_url, config) => {
        if (config?.signal) signals.push(config.signal as AbortSignal);
        return new Promise(() => {});
      });

      const { fetchProfile } = useEntityProfile();

      fetchProfile("author", 1);
      fetchProfile("author", 2);

      expect(signals).toHaveLength(2);
      expect(signals[0].aborted).toBe(true);
      expect(signals[1].aborted).toBe(false);
    });

    it("does not set error state when axios CanceledError is thrown", async () => {
      const abortError = new Error("canceled");
      abortError.name = "CanceledError";

      vi.mocked(api.get).mockRejectedValueOnce(abortError);

      const { fetchProfile, loadingState, error } = useEntityProfile();
      await fetchProfile("author", 1);

      expect(loadingState.value).not.toBe("error");
      expect(error.value).toBeNull();
    });

    it("does not set error state when native AbortError is thrown", async () => {
      const abortError = new Error("The operation was aborted");
      abortError.name = "AbortError";

      vi.mocked(api.get).mockRejectedValueOnce(abortError);

      const { fetchProfile, loadingState, error } = useEntityProfile();
      await fetchProfile("author", 1);

      expect(loadingState.value).not.toBe("error");
      expect(error.value).toBeNull();
    });

    it("passes signal to api.get", async () => {
      vi.mocked(api.get).mockResolvedValueOnce({
        data: { entity: {}, profile: {}, connections: [], books: [], stats: {} },
      });

      const { fetchProfile } = useEntityProfile();
      await fetchProfile("author", 1);

      expect(api.get).toHaveBeenCalledWith(
        "/entity/author/1/profile",
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      );
    });
  });

  describe("regenerateProfile concurrency guard", () => {
    it("ignores second call while regeneration is in flight", async () => {
      let resolvePost: () => void;
      vi.mocked(api.post).mockImplementation(
        () => new Promise<void>((resolve) => (resolvePost = resolve))
      );

      const { regenerateProfile, isRegenerating } = useEntityProfile();

      const first = regenerateProfile("author", 1);
      expect(isRegenerating.value).toBe(true);

      const second = regenerateProfile("author", 1);

      resolvePost!();
      // After POST resolves, polling starts. Return a profile with bio to stop polling.
      vi.mocked(api.get).mockResolvedValue({
        data: {
          entity: {},
          profile: { bio_summary: "done" },
          connections: [],
          books: [],
          stats: {},
        },
      });
      await vi.advanceTimersByTimeAsync(5000);
      await first;
      await second;

      expect(api.post).toHaveBeenCalledTimes(1);
    });

    it("resets isRegenerating after profile appears", async () => {
      vi.mocked(api.post).mockResolvedValueOnce(undefined);
      // First poll returns profile with bio_summary (generation complete)
      vi.mocked(api.get).mockResolvedValueOnce({
        data: {
          entity: {},
          profile: { bio_summary: "Generated bio" },
          connections: [],
          books: [],
          stats: {},
        },
      });

      const { regenerateProfile, isRegenerating } = useEntityProfile();
      const promise = regenerateProfile("author", 1);
      await vi.advanceTimersByTimeAsync(5000);
      await promise;

      expect(isRegenerating.value).toBe(false);
    });

    it("resets isRegenerating after POST error", async () => {
      vi.mocked(api.post).mockRejectedValueOnce(new Error("fail"));

      const { regenerateProfile, isRegenerating } = useEntityProfile();
      await regenerateProfile("author", 1);

      expect(isRegenerating.value).toBe(false);
    });
  });

  describe("fetchProfile happy path", () => {
    it("sets loaded state on success", async () => {
      const mockData = {
        entity: { name: "Dickens", type: "author" },
        profile: { bio_summary: "A writer." },
        connections: [],
        books: [],
        stats: { total_books: 0 },
      };
      vi.mocked(api.get).mockResolvedValueOnce({ data: mockData });

      const { fetchProfile, loadingState, profileData } = useEntityProfile();
      await fetchProfile("author", 1);

      expect(loadingState.value).toBe("loaded");
      expect(profileData.value).toEqual(mockData);
    });
  });
});
