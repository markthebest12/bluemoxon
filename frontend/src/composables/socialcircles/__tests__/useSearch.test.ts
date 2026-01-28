import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ref, nextTick } from "vue";
import { useSearch } from "../useSearch";
import type { ApiNode, NodeId, BookId } from "@/types/socialCircles";

// Helper to create mock nodes with proper branded types
function createMockNode(
  id: string,
  name: string,
  type: "author" | "publisher" | "binder"
): ApiNode {
  return {
    id: id as NodeId,
    entity_id: parseInt(id.split(":")[1] || "0", 10),
    name,
    type,
    book_count: 1,
    book_ids: [1 as BookId],
  };
}

const mockNodes: ApiNode[] = [
  createMockNode("author:1", "Lord Byron", "author"),
  createMockNode("publisher:1", "John Murray", "publisher"),
  createMockNode("author:2", "Charles Darwin", "author"),
  createMockNode("binder:1", "John Smith", "binder"),
];

/**
 * Helper to set query and wait for debounce to complete.
 * Vue's watch needs a tick to process, then we advance timers for debounce.
 */
async function setQueryAndWait(
  query: ReturnType<typeof ref<string>>,
  value: string,
  debounceMs = 150
) {
  query.value = value;
  await nextTick(); // Let Vue process the watch trigger
  vi.advanceTimersByTime(debounceMs);
  await nextTick(); // Let Vue process the debounced update
}

describe("useSearch", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("initial state", () => {
    it("returns empty results for empty query", () => {
      const nodes = ref(mockNodes);
      const { query, results } = useSearch(nodes);

      expect(query.value).toBe("");
      expect(results.value).toEqual([]);
    });

    it("starts with activeIndex at 0", () => {
      const nodes = ref(mockNodes);
      const { activeIndex } = useSearch(nodes);

      expect(activeIndex.value).toBe(0);
    });
  });

  describe("filtering", () => {
    it("filters nodes by name (case insensitive)", async () => {
      const nodes = ref(mockNodes);
      const { query, results } = useSearch(nodes);

      await setQueryAndWait(query, "byron");

      expect(results.value).toHaveLength(1);
      expect(results.value[0].name).toBe("Lord Byron");
    });

    it("filters nodes by uppercase query", async () => {
      const nodes = ref(mockNodes);
      const { query, results } = useSearch(nodes);

      await setQueryAndWait(query, "BYRON");

      expect(results.value).toHaveLength(1);
      expect(results.value[0].name).toBe("Lord Byron");
    });

    it("matches partial strings", async () => {
      const nodes = ref(mockNodes);
      const { query, results } = useSearch(nodes);

      await setQueryAndWait(query, "dar");

      expect(results.value).toHaveLength(1);
      expect(results.value[0].name).toBe("Charles Darwin");
    });

    it("returns empty results for no matches", async () => {
      const nodes = ref(mockNodes);
      const { query, results } = useSearch(nodes);

      await setQueryAndWait(query, "xyz123nonexistent");

      expect(results.value).toEqual([]);
    });

    it("trims whitespace from query", async () => {
      const nodes = ref(mockNodes);
      const { query, results } = useSearch(nodes);

      await setQueryAndWait(query, "  byron  ");

      expect(results.value).toHaveLength(1);
      expect(results.value[0].name).toBe("Lord Byron");
    });

    it("returns empty for whitespace-only query", async () => {
      const nodes = ref(mockNodes);
      const { query, results } = useSearch(nodes);

      await setQueryAndWait(query, "   ");

      expect(results.value).toEqual([]);
    });
  });

  describe("result limiting", () => {
    it("limits results to 10", async () => {
      const manyNodes = Array.from({ length: 20 }, (_, i) =>
        createMockNode(`author:${i}`, `Person ${i}`, "author")
      );
      const nodes = ref(manyNodes);
      const { query, results } = useSearch(nodes);

      await setQueryAndWait(query, "Person");

      expect(results.value).toHaveLength(10);
    });

    it("returns all results if fewer than 10 match", async () => {
      const nodes = ref(mockNodes);
      const { query, results } = useSearch(nodes);

      await setQueryAndWait(query, "john");

      expect(results.value).toHaveLength(2);
    });
  });

  describe("debouncing", () => {
    it("debounces query updates", async () => {
      const nodes = ref(mockNodes);
      const { query, results } = useSearch(nodes);

      query.value = "byron";
      await nextTick();

      // Results should be empty before debounce completes
      expect(results.value).toEqual([]);

      vi.advanceTimersByTime(100); // Still within debounce period
      await nextTick();
      expect(results.value).toEqual([]);

      vi.advanceTimersByTime(50); // Now debounce completes (150ms total)
      await nextTick();
      expect(results.value).toHaveLength(1);
    });

    it("resets debounce on rapid typing", async () => {
      const nodes = ref(mockNodes);
      const { query, results } = useSearch(nodes);

      query.value = "b";
      await nextTick();
      vi.advanceTimersByTime(100);

      query.value = "by";
      await nextTick();
      vi.advanceTimersByTime(100);

      query.value = "byr";
      await nextTick();
      vi.advanceTimersByTime(100);

      // Still no results - each keystroke reset the timer
      expect(results.value).toEqual([]);

      vi.advanceTimersByTime(50); // Complete final debounce
      await nextTick();
      expect(results.value).toHaveLength(1);
      expect(results.value[0].name).toBe("Lord Byron");
    });
  });

  describe("groupedResults", () => {
    it("groups results by type", async () => {
      const nodes = ref(mockNodes);
      const { query, groupedResults } = useSearch(nodes);

      await setQueryAndWait(query, "john");

      expect(groupedResults.value.length).toBe(2);

      const types = groupedResults.value.map((g) => g.type);
      expect(types).toContain("publisher");
      expect(types).toContain("binder");
    });

    it("returns empty array when no results", () => {
      const nodes = ref(mockNodes);
      const { groupedResults } = useSearch(nodes);

      expect(groupedResults.value).toEqual([]);
    });

    it("maintains consistent type order (author, publisher, binder)", async () => {
      // Create nodes that match in different order than the desired output
      const testNodes: ApiNode[] = [
        createMockNode("binder:1", "Test A Binder", "binder"),
        createMockNode("publisher:1", "Test A Publisher", "publisher"),
        createMockNode("author:1", "Test A Author", "author"),
      ];
      const nodes = ref(testNodes);
      const { query, groupedResults } = useSearch(nodes);

      await setQueryAndWait(query, "test a");

      expect(groupedResults.value[0].type).toBe("author");
      expect(groupedResults.value[1].type).toBe("publisher");
      expect(groupedResults.value[2].type).toBe("binder");
    });

    it("includes proper labels for each group", async () => {
      const nodes = ref(mockNodes);
      const { query, groupedResults } = useSearch(nodes);

      await setQueryAndWait(query, "john");

      const publisherGroup = groupedResults.value.find((g) => g.type === "publisher");
      const binderGroup = groupedResults.value.find((g) => g.type === "binder");

      expect(publisherGroup?.label).toBe("Publishers");
      expect(binderGroup?.label).toBe("Binders");
    });

    it("only includes groups with matching nodes", async () => {
      const nodes = ref(mockNodes);
      const { query, groupedResults } = useSearch(nodes);

      await setQueryAndWait(query, "byron");

      expect(groupedResults.value).toHaveLength(1);
      expect(groupedResults.value[0].type).toBe("author");
      expect(groupedResults.value[0].label).toBe("Authors");
      expect(groupedResults.value[0].nodes).toHaveLength(1);
    });
  });

  describe("navigation", () => {
    it("navigateDown increments activeIndex", async () => {
      const nodes = ref(mockNodes);
      const { query, activeIndex, navigateDown } = useSearch(nodes);

      await setQueryAndWait(query, "a"); // matches multiple nodes

      expect(activeIndex.value).toBe(0);
      navigateDown();
      expect(activeIndex.value).toBe(1);
    });

    it("navigateDown stops at last result", async () => {
      const nodes = ref(mockNodes);
      const { query, activeIndex, navigateDown, results } = useSearch(nodes);

      await setQueryAndWait(query, "john"); // matches 2 nodes

      expect(results.value).toHaveLength(2);

      navigateDown(); // 0 -> 1
      navigateDown(); // Should stay at 1 (last index)
      navigateDown(); // Should still stay at 1

      expect(activeIndex.value).toBe(1);
    });

    it("navigateUp decrements activeIndex", async () => {
      const nodes = ref(mockNodes);
      const { query, activeIndex, navigateUp, navigateDown } = useSearch(nodes);

      // "a" matches: "John Murray" (Murray), "Charles Darwin" (Charles, Darwin)
      await setQueryAndWait(query, "a");

      navigateDown(); // 0 -> 1
      expect(activeIndex.value).toBe(1);

      navigateUp(); // 1 -> 0
      expect(activeIndex.value).toBe(0);
    });

    it("navigateUp stops at 0", async () => {
      const nodes = ref(mockNodes);
      const { query, activeIndex, navigateUp } = useSearch(nodes);

      await setQueryAndWait(query, "a");

      expect(activeIndex.value).toBe(0);
      navigateUp();
      navigateUp();

      expect(activeIndex.value).toBe(0);
    });

    it("activeIndex resets to 0 when results change", async () => {
      const nodes = ref(mockNodes);
      const { query, activeIndex, navigateDown } = useSearch(nodes);

      await setQueryAndWait(query, "john");

      navigateDown();
      expect(activeIndex.value).toBe(1);

      // Change query - activeIndex should reset
      await setQueryAndWait(query, "byron");

      expect(activeIndex.value).toBe(0);
    });
  });

  describe("clearSearch", () => {
    it("resets query to empty string", async () => {
      const nodes = ref(mockNodes);
      const { query, clearSearch } = useSearch(nodes);

      await setQueryAndWait(query, "byron");

      clearSearch();

      expect(query.value).toBe("");
    });

    it("resets activeIndex to 0", async () => {
      const nodes = ref(mockNodes);
      const { query, activeIndex, navigateDown, clearSearch } = useSearch(nodes);

      // "a" matches: "John Murray", "Charles Darwin" - 2 results
      await setQueryAndWait(query, "a");

      navigateDown(); // 0 -> 1
      expect(activeIndex.value).toBe(1);

      clearSearch();

      expect(activeIndex.value).toBe(0);
    });

    it("clears debounced query immediately", async () => {
      const nodes = ref(mockNodes);
      const { query, results, clearSearch } = useSearch(nodes);

      await setQueryAndWait(query, "byron");

      expect(results.value).toHaveLength(1);

      clearSearch();
      await nextTick();

      // Results should be empty immediately, not after debounce
      expect(results.value).toEqual([]);
    });

    it("cancels pending debounce", async () => {
      const nodes = ref(mockNodes);
      const { query, results, clearSearch } = useSearch(nodes);

      query.value = "byron";
      await nextTick();
      vi.advanceTimersByTime(50); // Partial debounce

      clearSearch();
      vi.advanceTimersByTime(100); // Complete original debounce period
      await nextTick();

      // Should still be empty - debounce was cancelled
      expect(results.value).toEqual([]);
    });
  });

  describe("selectResult", () => {
    it("returns correct node at given index", async () => {
      const nodes = ref(mockNodes);
      const { query, selectResult } = useSearch(nodes);

      await setQueryAndWait(query, "byron");

      const selected = selectResult(0);

      expect(selected).not.toBeNull();
      expect(selected?.name).toBe("Lord Byron");
      expect(selected?.id).toBe("author:1");
    });

    it("returns null for out-of-bounds index", async () => {
      const nodes = ref(mockNodes);
      const { query, selectResult } = useSearch(nodes);

      await setQueryAndWait(query, "byron");

      expect(selectResult(99)).toBeNull();
    });

    it("returns null for negative index", async () => {
      const nodes = ref(mockNodes);
      const { query, selectResult } = useSearch(nodes);

      await setQueryAndWait(query, "byron");

      expect(selectResult(-1)).toBeNull();
    });

    it("returns null when no results", () => {
      const nodes = ref(mockNodes);
      const { selectResult } = useSearch(nodes);

      expect(selectResult(0)).toBeNull();
    });
  });

  describe("reactive nodes", () => {
    it("updates results when nodes ref changes", async () => {
      const nodes = ref<ApiNode[]>([]);
      const { query, results } = useSearch(nodes);

      await setQueryAndWait(query, "byron");

      expect(results.value).toEqual([]);

      // Add nodes - computed should react
      nodes.value = mockNodes;
      await nextTick();

      // Results should update (computed is reactive)
      expect(results.value).toHaveLength(1);
      expect(results.value[0].name).toBe("Lord Byron");
    });

    it("handles empty nodes array", async () => {
      const nodes = ref<ApiNode[]>([]);
      const { query, results, groupedResults } = useSearch(nodes);

      await setQueryAndWait(query, "test");

      expect(results.value).toEqual([]);
      expect(groupedResults.value).toEqual([]);
    });
  });

  describe("edge cases", () => {
    it("handles nodes with special characters in name", async () => {
      const specialNodes: ApiNode[] = [
        createMockNode("publisher:1", "Smith & Sons", "publisher"),
        createMockNode("publisher:2", "O'Reilly", "publisher"),
      ];
      const nodes = ref(specialNodes);
      const { query, results } = useSearch(nodes);

      await setQueryAndWait(query, "&");
      expect(results.value).toHaveLength(1);
      expect(results.value[0].name).toBe("Smith & Sons");

      await setQueryAndWait(query, "'");
      expect(results.value).toHaveLength(1);
      expect(results.value[0].name).toBe("O'Reilly");
    });

    it("handles nodes without type (unknown)", async () => {
      // Simulate a node that might come from API with missing type
      const nodeWithoutType = {
        id: "unknown:1" as NodeId,
        entity_id: 1,
        name: "Unknown Entity",
        type: undefined as unknown as "author",
        book_count: 1,
        book_ids: [1 as BookId],
      };
      const nodes = ref([nodeWithoutType]);
      const { query, groupedResults } = useSearch(nodes);

      await setQueryAndWait(query, "unknown");

      expect(groupedResults.value).toHaveLength(1);
      expect(groupedResults.value[0].type).toBe("unknown");
      expect(groupedResults.value[0].label).toBe("Other");
    });
  });
});
