import { describe, it, expect } from "vitest";
import { getConditionColor, formatConditionGrade, CONDITION_COLORS } from "../conditionColors";

describe("getConditionColor", () => {
  it("returns correct color for FINE", () => {
    expect(getConditionColor("FINE")).toBe("#2d6a4f");
  });

  it("returns correct color for NEAR_FINE", () => {
    expect(getConditionColor("NEAR_FINE")).toBe("#40916c");
  });

  it("returns correct color for VERY_GOOD", () => {
    expect(getConditionColor("VERY_GOOD")).toBe("#2b8a8a");
  });

  it("returns correct color for GOOD", () => {
    expect(getConditionColor("GOOD")).toBe("#e09f3e");
  });

  it("returns correct color for FAIR", () => {
    expect(getConditionColor("FAIR")).toBe("#e07c3e");
  });

  it("returns correct color for POOR", () => {
    expect(getConditionColor("POOR")).toBe("#9c503d");
  });

  it("returns UNGRADED color for unknown grade", () => {
    expect(getConditionColor("UNKNOWN_GRADE")).toBe(CONDITION_COLORS.UNGRADED);
  });

  it("is case-insensitive", () => {
    expect(getConditionColor("fine")).toBe("#2d6a4f");
    expect(getConditionColor("Fine")).toBe("#2d6a4f");
    expect(getConditionColor("near_fine")).toBe("#40916c");
  });
});

describe("formatConditionGrade", () => {
  it('converts NEAR_FINE to "Near Fine"', () => {
    expect(formatConditionGrade("NEAR_FINE")).toBe("Near Fine");
  });

  it('converts FINE to "Fine"', () => {
    expect(formatConditionGrade("FINE")).toBe("Fine");
  });

  it('converts VERY_GOOD to "Very Good"', () => {
    expect(formatConditionGrade("VERY_GOOD")).toBe("Very Good");
  });

  it('converts POOR to "Poor"', () => {
    expect(formatConditionGrade("POOR")).toBe("Poor");
  });
});
