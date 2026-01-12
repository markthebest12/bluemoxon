import { describe, it, expect } from "vitest";
import { formatConditionGrade } from "./format";

describe("formatConditionGrade", () => {
  it("converts NEAR_FINE to Near Fine", () => {
    expect(formatConditionGrade("NEAR_FINE")).toBe("Near Fine");
  });

  it("converts VERY_GOOD to Very Good", () => {
    expect(formatConditionGrade("VERY_GOOD")).toBe("Very Good");
  });

  it("converts FINE to Fine", () => {
    expect(formatConditionGrade("FINE")).toBe("Fine");
  });

  it("converts GOOD to Good", () => {
    expect(formatConditionGrade("GOOD")).toBe("Good");
  });

  it("converts FAIR to Fair", () => {
    expect(formatConditionGrade("FAIR")).toBe("Fair");
  });

  it("converts POOR to Poor", () => {
    expect(formatConditionGrade("POOR")).toBe("Poor");
  });

  it("passes through Ungraded unchanged", () => {
    expect(formatConditionGrade("Ungraded")).toBe("Ungraded");
  });

  it("handles null/undefined gracefully", () => {
    expect(formatConditionGrade(null)).toBe("Ungraded");
    expect(formatConditionGrade(undefined)).toBe("Ungraded");
  });

  it("handles unknown values by title-casing", () => {
    expect(formatConditionGrade("UNKNOWN_VALUE")).toBe("Unknown Value");
  });
});
