import { describe, it, expect } from "vitest";
import { parseEntityMarkers } from "@/utils/entityMarkers";

describe("parseEntityMarkers", () => {
  it("returns single text segment for plain text", () => {
    const result = parseEntityMarkers("Hello world");
    expect(result).toEqual([{ type: "text", content: "Hello world" }]);
  });

  it("parses a single marker", () => {
    const result = parseEntityMarkers("Met {{entity:author:32|Robert Browning}} at a salon.");
    expect(result).toEqual([
      { type: "text", content: "Met " },
      {
        type: "link",
        entityType: "author",
        entityId: 32,
        displayName: "Robert Browning",
      },
      { type: "text", content: " at a salon." },
    ]);
  });

  it("parses multiple markers", () => {
    const result = parseEntityMarkers(
      "{{entity:author:32|Robert Browning}} published with {{entity:publisher:7|Chapman & Hall}}."
    );
    expect(result).toHaveLength(4);
    expect(result[0]).toEqual({
      type: "link",
      entityType: "author",
      entityId: 32,
      displayName: "Robert Browning",
    });
    expect(result[1]).toEqual({ type: "text", content: " published with " });
    expect(result[2]).toEqual({
      type: "link",
      entityType: "publisher",
      entityId: 7,
      displayName: "Chapman & Hall",
    });
    expect(result[3]).toEqual({ type: "text", content: "." });
  });

  it("returns single text segment for empty string", () => {
    expect(parseEntityMarkers("")).toEqual([{ type: "text", content: "" }]);
  });

  it("handles adjacent markers with no text between", () => {
    const result = parseEntityMarkers("{{entity:author:1|Alice}}{{entity:author:2|Bob}}");
    expect(result).toEqual([
      { type: "link", entityType: "author", entityId: 1, displayName: "Alice" },
      { type: "link", entityType: "author", entityId: 2, displayName: "Bob" },
    ]);
  });

  it("handles malformed markers as plain text", () => {
    const result = parseEntityMarkers("Text with {{entity:broken marker here.");
    expect(result).toEqual([{ type: "text", content: "Text with {{entity:broken marker here." }]);
  });

  it("handles marker with special characters in display name", () => {
    const result = parseEntityMarkers("Published by {{entity:publisher:7|Smith, Elder & Co.}}.");
    expect(result[1]).toEqual({
      type: "link",
      entityType: "publisher",
      entityId: 7,
      displayName: "Smith, Elder & Co.",
    });
  });

  it("filters empty text segments between adjacent markers", () => {
    const result = parseEntityMarkers("{{entity:author:1|A}}{{entity:author:2|B}}");
    // Should not have empty text segments between markers
    expect(result.every((s) => s.type === "link" || s.content !== "")).toBe(true);
  });
});
