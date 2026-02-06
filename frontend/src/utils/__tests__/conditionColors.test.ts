import { describe, it, expect } from "vitest";
import {
  getConditionColor,
  formatConditionGrade,
  getLuminance,
  CONDITION_COLORS,
} from "../conditionColors";

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

describe("getLuminance", () => {
  it("returns 0 for black", () => {
    expect(getLuminance("#000000")).toBeCloseTo(0, 3);
  });

  it("returns 1 for white", () => {
    expect(getLuminance("#ffffff")).toBeCloseTo(1, 3);
  });

  it("returns low luminance for dark green (FINE)", () => {
    expect(getLuminance("#2d6a4f")).toBeLessThan(0.18);
  });

  it("returns higher luminance for golden (GOOD)", () => {
    expect(getLuminance("#e09f3e")).toBeGreaterThan(0.18);
  });

  it("matches expected text color decisions for all grades", () => {
    const darkBg = ["FINE", "POOR"];
    const lightBg = ["NEAR_FINE", "VERY_GOOD", "GOOD", "FAIR", "UNGRADED"];

    for (const grade of darkBg) {
      const lum = getLuminance(getConditionColor(grade));
      expect(lum, `${grade} should have dark background`).toBeLessThan(0.18);
    }
    for (const grade of lightBg) {
      const lum = getLuminance(getConditionColor(grade));
      expect(lum, `${grade} should have light background`).toBeGreaterThanOrEqual(0.18);
    }
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
