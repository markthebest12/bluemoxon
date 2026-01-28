import { describe, it, expect } from "vitest";
import { formatTier, calculateStrength, renderStrength, getPlaceholderImage } from "../formatters";

describe("formatTier", () => {
  it("returns Premier for TIER_1", () => {
    const result = formatTier("TIER_1");
    expect(result).toEqual({
      label: "Premier",
      stars: 3,
      tooltip: "Tier 1 - Premier Figure",
    });
  });

  it("returns Established for TIER_2", () => {
    const result = formatTier("TIER_2");
    expect(result.label).toBe("Established");
    expect(result.stars).toBe(2);
  });

  it("returns Known for TIER_3", () => {
    const result = formatTier("TIER_3");
    expect(result.label).toBe("Known");
    expect(result.stars).toBe(1);
  });

  it("returns Unranked for null", () => {
    const result = formatTier(null);
    expect(result.label).toBe("Unranked");
    expect(result.stars).toBe(0);
  });
});

describe("calculateStrength", () => {
  it("returns book count up to 5", () => {
    expect(calculateStrength(1)).toBe(1);
    expect(calculateStrength(3)).toBe(3);
    expect(calculateStrength(5)).toBe(5);
  });

  it("caps at 5 for counts over 5", () => {
    expect(calculateStrength(6)).toBe(5);
    expect(calculateStrength(100)).toBe(5);
  });

  it("returns 0 for 0 books", () => {
    expect(calculateStrength(0)).toBe(0);
  });
});

describe("renderStrength", () => {
  it("renders correct filled/unfilled pattern", () => {
    expect(renderStrength(0)).toBe("○○○○○");
    expect(renderStrength(3)).toBe("●●●○○");
    expect(renderStrength(5)).toBe("●●●●●");
  });
});

describe("getPlaceholderImage", () => {
  it("returns author placeholder path", () => {
    const result = getPlaceholderImage("author", 42);
    expect(result).toMatch(/\/images\/entity-placeholders\/authors\//);
    expect(result).toMatch(/\.svg$/);
  });

  it("returns consistent image for same entity ID", () => {
    const first = getPlaceholderImage("publisher", 123);
    const second = getPlaceholderImage("publisher", 123);
    expect(first).toBe(second);
  });
});
