import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useNetworkData } from "../useNetworkData";
import { mockAuthor1, mockPublisher1, mockBinder1, mockEdge1 } from "./fixtures";
import type { SocialCirclesResponse, NodeId, EdgeId, BookId } from "@/types/socialCircles";
import { API } from "@/constants/socialCircles";

// Mock the api service
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

// Import the mocked api after mocking
import { api } from "@/services/api";

const mockApiGet = vi.mocked(api.get);

// Helper to create a mock response
function createMockResponse(): SocialCirclesResponse {
  return {
    nodes: [mockAuthor1, mockPublisher1, mockBinder1],
    edges: [mockEdge1],
    meta: {
      total_books: 20,
      total_authors: 5,
      total_publishers: 3,
      total_binders: 2,
      date_range: [1812, 1920],
      generated_at: "2024-01-15T10:30:00Z",
      truncated: false,
    },
  };
}

describe("useNetworkData", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("initial state", () => {
    it("initializes with idle loading state", () => {
      const { loadingState } = useNetworkData();
      expect(loadingState.value).toBe("idle");
    });

    it("initializes with null data", () => {
      const { data } = useNetworkData();
      expect(data.value).toBeNull();
    });

    it("initializes with null error", () => {
      const { error } = useNetworkData();
      expect(error.value).toBeNull();
    });
  });

  describe("fetchData", () => {
    it("sets loading state while fetching", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });

      const { loadingState, fetchData } = useNetworkData();

      const fetchPromise = fetchData();
      expect(loadingState.value).toBe("loading");

      await fetchPromise;
      expect(loadingState.value).toBe("success");
    });

    it("fetches data with default parameters", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });

      const { fetchData } = useNetworkData();
      await fetchData();

      expect(mockApiGet).toHaveBeenCalledWith(API.endpoint, {
        params: {
          include_binders: true,
          min_book_count: 1,
        },
      });
    });

    it("fetches data with custom parameters", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });

      const { fetchData } = useNetworkData();
      await fetchData({ includeBinders: false, minBookCount: 5 });

      expect(mockApiGet).toHaveBeenCalledWith(API.endpoint, {
        params: {
          include_binders: false,
          min_book_count: 5,
        },
      });
    });

    it("sets data on successful fetch", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });

      const { data, fetchData } = useNetworkData();
      await fetchData();

      expect(data.value).toEqual(mockResponse);
    });

    it("transforms API response with correct node structure", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });

      const { data, fetchData } = useNetworkData();
      await fetchData();

      expect(data.value?.nodes).toHaveLength(3);
      expect(data.value?.nodes[0]).toMatchObject({
        id: "author:1",
        name: "Charles Dickens",
        type: "author",
        book_count: 12,
      });
    });

    it("transforms API response with correct edge structure", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });

      const { data, fetchData } = useNetworkData();
      await fetchData();

      expect(data.value?.edges).toHaveLength(1);
      expect(data.value?.edges[0]).toMatchObject({
        id: "e:author:1:publisher:1",
        source: "author:1",
        target: "publisher:1",
        type: "publisher",
        strength: 4,
      });
    });

    it("provides meta information from response", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });

      const { data, fetchData } = useNetworkData();
      await fetchData();

      expect(data.value?.meta).toEqual({
        total_books: 20,
        total_authors: 5,
        total_publishers: 3,
        total_binders: 2,
        date_range: [1812, 1920],
        generated_at: "2024-01-15T10:30:00Z",
        truncated: false,
      });
    });

    it("clears previous error on new fetch", async () => {
      // First fetch fails
      mockApiGet.mockRejectedValueOnce(new Error("Network error"));
      const { error, fetchData } = useNetworkData();
      await fetchData();
      expect(error.value).not.toBeNull();

      // Second fetch succeeds
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });
      vi.advanceTimersByTime(API.cacheTtlMs + 1);
      await fetchData({ forceRefresh: true });
      expect(error.value).toBeNull();
    });
  });

  describe("error handling", () => {
    it("handles API errors gracefully", async () => {
      mockApiGet.mockRejectedValueOnce(new Error("Network error"));

      const { error, loadingState, fetchData } = useNetworkData();
      await fetchData();

      expect(loadingState.value).toBe("error");
      expect(error.value).toEqual({
        type: "network",
        message: "Network error",
        retryable: true,
      });
    });

    it("handles non-Error rejections", async () => {
      mockApiGet.mockRejectedValueOnce("Unknown error string");

      const { error, fetchData } = useNetworkData();
      await fetchData();

      expect(error.value).toEqual({
        type: "network",
        message: "Unknown error",
        retryable: true,
      });
    });

    it("keeps data as null on error", async () => {
      mockApiGet.mockRejectedValueOnce(new Error("Network error"));

      const { data, fetchData } = useNetworkData();
      await fetchData();

      expect(data.value).toBeNull();
    });
  });

  describe("caching behavior", () => {
    it("uses cached data within TTL", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });

      const { data, fetchData } = useNetworkData();

      // First fetch
      await fetchData();
      expect(mockApiGet).toHaveBeenCalledTimes(1);

      // Second fetch within TTL - should use cache
      await fetchData();
      expect(mockApiGet).toHaveBeenCalledTimes(1);
      expect(data.value).toEqual(mockResponse);
    });

    it("refetches data after TTL expires", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValue({ data: mockResponse });

      const { fetchData } = useNetworkData();

      // First fetch
      await fetchData();
      expect(mockApiGet).toHaveBeenCalledTimes(1);

      // Advance time past TTL
      vi.advanceTimersByTime(API.cacheTtlMs + 1);

      // Second fetch after TTL - should refetch
      await fetchData();
      expect(mockApiGet).toHaveBeenCalledTimes(2);
    });

    it("bypasses cache with forceRefresh option", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValue({ data: mockResponse });

      const { fetchData } = useNetworkData();

      // First fetch
      await fetchData();
      expect(mockApiGet).toHaveBeenCalledTimes(1);

      // Force refresh - should fetch again
      await fetchData({ forceRefresh: true });
      expect(mockApiGet).toHaveBeenCalledTimes(2);
    });

    it("sets loading state to success when using cache", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });

      const { loadingState, fetchData } = useNetworkData();

      await fetchData();
      expect(loadingState.value).toBe("success");

      // Fetch again from cache
      await fetchData();
      expect(loadingState.value).toBe("success");
    });
  });

  describe("clearCache", () => {
    it("clears the cache", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValue({ data: mockResponse });

      const { fetchData, clearCache } = useNetworkData();

      // First fetch
      await fetchData();
      expect(mockApiGet).toHaveBeenCalledTimes(1);

      // Clear cache
      clearCache();

      // Second fetch - should refetch since cache is cleared
      await fetchData();
      expect(mockApiGet).toHaveBeenCalledTimes(2);
    });
  });

  describe("instance isolation", () => {
    it("maintains separate state for each composable instance", async () => {
      const mockResponse1 = createMockResponse();
      const mockResponse2: SocialCirclesResponse = {
        ...createMockResponse(),
        meta: { ...createMockResponse().meta, total_books: 100 },
      };

      mockApiGet.mockResolvedValueOnce({ data: mockResponse1 });
      mockApiGet.mockResolvedValueOnce({ data: mockResponse2 });

      const instance1 = useNetworkData();
      const instance2 = useNetworkData();

      await instance1.fetchData();
      await instance2.fetchData();

      expect(instance1.data.value?.meta.total_books).toBe(20);
      expect(instance2.data.value?.meta.total_books).toBe(100);
    });

    it("maintains separate cache for each instance", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValue({ data: mockResponse });

      const instance1 = useNetworkData();
      const instance2 = useNetworkData();

      await instance1.fetchData();
      await instance2.fetchData();

      // Each instance should fetch independently
      expect(mockApiGet).toHaveBeenCalledTimes(2);
    });
  });

  describe("readonly refs", () => {
    it("returns readonly data ref", async () => {
      const mockResponse = createMockResponse();
      mockApiGet.mockResolvedValueOnce({ data: mockResponse });

      const { data, fetchData } = useNetworkData();
      await fetchData();

      // The ref should be readonly (we test this at compile time via TypeScript,
      // but we can verify the data is populated correctly)
      expect(data.value).not.toBeNull();
    });

    it("returns readonly loadingState ref", () => {
      const { loadingState } = useNetworkData();
      expect(loadingState.value).toBe("idle");
    });

    it("returns readonly error ref", () => {
      const { error } = useNetworkData();
      expect(error.value).toBeNull();
    });
  });

  describe("response data validation", () => {
    it("handles empty nodes array", async () => {
      const emptyResponse: SocialCirclesResponse = {
        nodes: [],
        edges: [],
        meta: {
          total_books: 0,
          total_authors: 0,
          total_publishers: 0,
          total_binders: 0,
          date_range: [1800, 1900],
          generated_at: "2024-01-15T10:30:00Z",
          truncated: false,
        },
      };
      mockApiGet.mockResolvedValueOnce({ data: emptyResponse });

      const { data, fetchData } = useNetworkData();
      await fetchData();

      expect(data.value?.nodes).toEqual([]);
      expect(data.value?.edges).toEqual([]);
    });

    it("handles response with truncated flag", async () => {
      const truncatedResponse: SocialCirclesResponse = {
        ...createMockResponse(),
        meta: { ...createMockResponse().meta, truncated: true },
      };
      mockApiGet.mockResolvedValueOnce({ data: truncatedResponse });

      const { data, fetchData } = useNetworkData();
      await fetchData();

      expect(data.value?.meta.truncated).toBe(true);
    });

    it("handles nodes with optional fields", async () => {
      const responseWithOptionalFields: SocialCirclesResponse = {
        nodes: [
          {
            id: "author:2" as NodeId,
            entity_id: 2,
            name: "Unknown Author",
            type: "author",
            book_count: 1,
            book_ids: [1 as BookId],
            // birth_year, death_year, era, tier are all optional and missing
          },
        ],
        edges: [],
        meta: createMockResponse().meta,
      };
      mockApiGet.mockResolvedValueOnce({ data: responseWithOptionalFields });

      const { data, fetchData } = useNetworkData();
      await fetchData();

      const node = data.value?.nodes[0];
      expect(node?.birth_year).toBeUndefined();
      expect(node?.death_year).toBeUndefined();
      expect(node?.era).toBeUndefined();
      expect(node?.tier).toBeUndefined();
    });

    it("handles edges with optional fields", async () => {
      const responseWithOptionalEdgeFields: SocialCirclesResponse = {
        nodes: [mockAuthor1, mockPublisher1],
        edges: [
          {
            id: "e:author:1:publisher:1" as EdgeId,
            source: "author:1" as NodeId,
            target: "publisher:1" as NodeId,
            type: "publisher",
            strength: 3,
            // evidence, shared_book_ids, start_year, end_year are optional and missing
          },
        ],
        meta: createMockResponse().meta,
      };
      mockApiGet.mockResolvedValueOnce({ data: responseWithOptionalEdgeFields });

      const { data, fetchData } = useNetworkData();
      await fetchData();

      const edge = data.value?.edges[0];
      expect(edge?.evidence).toBeUndefined();
      expect(edge?.shared_book_ids).toBeUndefined();
      expect(edge?.start_year).toBeUndefined();
      expect(edge?.end_year).toBeUndefined();
    });
  });

  describe("concurrent fetch handling", () => {
    it("allows multiple concurrent fetches to complete", async () => {
      const mockResponse = createMockResponse();
      let resolveFirst: (value: { data: SocialCirclesResponse }) => void;
      let resolveSecond: (value: { data: SocialCirclesResponse }) => void;

      mockApiGet.mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve;
          })
      );
      mockApiGet.mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve;
          })
      );

      const { fetchData, loadingState } = useNetworkData();

      // Start first fetch
      const promise1 = fetchData({ forceRefresh: true });
      expect(loadingState.value).toBe("loading");

      // Start second fetch
      const promise2 = fetchData({ forceRefresh: true });
      expect(loadingState.value).toBe("loading");

      // Resolve first
      resolveFirst!({ data: mockResponse });
      await promise1;

      // Resolve second
      resolveSecond!({ data: mockResponse });
      await promise2;

      expect(loadingState.value).toBe("success");
    });
  });
});
