import { describe, it, expect } from "vitest";
import { filterNodesByQuery, MAX_FILTER_RESULTS } from "../filterUtils";
import type { ApiNode, NodeId, BookId } from "@/types/socialCircles";

describe("filterNodesByQuery", () => {
  /** Create a minimal ApiNode fixture. */
  function makeNode(id: number, name: string): ApiNode {
    return {
      id: `author:${id}` as NodeId,
      entity_id: id,
      name,
      type: "author",
      book_count: 1,
      book_ids: [1 as BookId],
    };
  }

  it("returns matching nodes when query matches name (case-insensitive)", () => {
    const nodes = [
      makeNode(1, "Charles Dickens"),
      makeNode(2, "Jane Austen"),
      makeNode(3, "Charlotte Bronte"),
    ];

    const result = filterNodesByQuery(nodes, "charles");

    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("Charles Dickens");
  });

  it("returns empty array when no nodes match", () => {
    const nodes = [makeNode(1, "Charles Dickens"), makeNode(2, "Jane Austen")];

    const result = filterNodesByQuery(nodes, "tolkien");

    expect(result).toEqual([]);
  });

  it("returns first MAX_FILTER_RESULTS nodes when query is empty", () => {
    const nodes = Array.from({ length: 30 }, (_, i) => makeNode(i + 1, `Author ${i + 1}`));

    const result = filterNodesByQuery(nodes, "");

    expect(result).toHaveLength(MAX_FILTER_RESULTS);
    expect(result[0].name).toBe("Author 1");
    expect(result[MAX_FILTER_RESULTS - 1].name).toBe(`Author ${MAX_FILTER_RESULTS}`);
  });

  it("limits results to MAX_FILTER_RESULTS", () => {
    const nodes = Array.from({ length: 30 }, (_, i) => makeNode(i + 1, `Match ${i + 1}`));

    const result = filterNodesByQuery(nodes, "match");

    expect(result).toHaveLength(MAX_FILTER_RESULTS);
  });

  it("handles empty nodes array", () => {
    const result = filterNodesByQuery([], "query");

    expect(result).toEqual([]);
  });

  it("trims and lowercases the query", () => {
    const nodes = [makeNode(1, "Charles Dickens"), makeNode(2, "Jane Austen")];

    const result = filterNodesByQuery(nodes, "  CHARLES  ");

    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("Charles Dickens");
  });

  it("returns first MAX_FILTER_RESULTS nodes for whitespace-only query", () => {
    const nodes = Array.from({ length: 30 }, (_, i) => makeNode(i + 1, `Author ${i + 1}`));

    const result = filterNodesByQuery(nodes, "   ");

    expect(result).toHaveLength(MAX_FILTER_RESULTS);
  });

  it("matches partial name substrings", () => {
    const nodes = [
      makeNode(1, "Charles Dickens"),
      makeNode(2, "Jane Austen"),
      makeNode(3, "Charlotte Bronte"),
    ];

    const result = filterNodesByQuery(nodes, "charl");

    expect(result).toHaveLength(2);
    expect(result.map((n) => n.name)).toEqual(["Charles Dickens", "Charlotte Bronte"]);
  });

  it("returns first MAX_FILTER_RESULTS nodes when query is null at runtime", () => {
    const nodes = Array.from({ length: 30 }, (_, i) => makeNode(i + 1, `Author ${i + 1}`));

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result = filterNodesByQuery(nodes, null as any);

    expect(result).toHaveLength(MAX_FILTER_RESULTS);
    expect(result[0].name).toBe("Author 1");
  });

  it("returns first MAX_FILTER_RESULTS nodes when query is undefined at runtime", () => {
    const nodes = Array.from({ length: 30 }, (_, i) => makeNode(i + 1, `Author ${i + 1}`));

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result = filterNodesByQuery(nodes, undefined as any);

    expect(result).toHaveLength(MAX_FILTER_RESULTS);
    expect(result[0].name).toBe("Author 1");
  });
});
