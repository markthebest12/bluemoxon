// frontend/src/types/__tests__/errors.spec.ts
import { describe, it, expect } from "vitest";
import { isEntityConflictResponse, type EntityConflictResponse } from "../errors";

describe("isEntityConflictResponse", () => {
  it("returns true for valid 409 conflict response", () => {
    const response: EntityConflictResponse = {
      error: "similar_entity_exists",
      entity_type: "publisher",
      input: "Macmillan",
      suggestions: [{ id: 123, name: "Macmillan and Co.", match: 0.85, book_count: 42 }],
      resolution: "Use existing publisher ID, or add force=true",
    };
    expect(isEntityConflictResponse(response)).toBe(true);
  });

  it("returns false for non-conflict response", () => {
    expect(isEntityConflictResponse({ error: "not_found" })).toBe(false);
    expect(isEntityConflictResponse(null)).toBe(false);
    expect(isEntityConflictResponse("string")).toBe(false);
  });

  it("returns false when suggestions is not an array", () => {
    const response = {
      error: "similar_entity_exists",
      entity_type: "publisher",
      input: "Test",
      suggestions: "not an array",
      resolution: "hint",
    };
    expect(isEntityConflictResponse(response)).toBe(false);
  });
});
