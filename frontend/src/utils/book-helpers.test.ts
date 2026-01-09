import { describe, it, expect } from "vitest";
import { computeEra, Era } from "./book-helpers";

describe("computeEra", () => {
  describe("null handling", () => {
    it("returns Unknown when both years are null", () => {
      expect(computeEra(null, null)).toBe(Era.UNKNOWN);
    });

    it("uses yearStart when yearEnd is null", () => {
      expect(computeEra(1850, null)).toBe(Era.VICTORIAN);
    });

    it("falls back to yearEnd when yearStart is null", () => {
      expect(computeEra(null, 1850)).toBe(Era.VICTORIAN);
    });
  });

  describe("Pre-Romantic era (before 1800)", () => {
    it("returns Pre-Romantic for years before 1800", () => {
      expect(computeEra(1750, null)).toBe(Era.PRE_ROMANTIC);
      expect(computeEra(1799, 1799)).toBe(Era.PRE_ROMANTIC);
    });
  });

  describe("Romantic era (1800-1836)", () => {
    it("returns Romantic for year 1800", () => {
      expect(computeEra(1800, null)).toBe(Era.ROMANTIC);
    });

    it("returns Romantic for year 1836", () => {
      expect(computeEra(1836, 1836)).toBe(Era.ROMANTIC);
    });

    it("returns Romantic for years in the middle of the era", () => {
      expect(computeEra(1815, null)).toBe(Era.ROMANTIC);
      expect(computeEra(1820, 1825)).toBe(Era.ROMANTIC);
    });
  });

  describe("Victorian era (1837-1901)", () => {
    it("returns Victorian for year 1837 (start of Queen Victoria's reign)", () => {
      expect(computeEra(1837, null)).toBe(Era.VICTORIAN);
    });

    it("returns Victorian for year 1901 (end of Queen Victoria's reign)", () => {
      expect(computeEra(1901, 1901)).toBe(Era.VICTORIAN);
    });

    it("returns Victorian for years in the middle of the era", () => {
      expect(computeEra(1850, null)).toBe(Era.VICTORIAN);
      expect(computeEra(1870, 1875)).toBe(Era.VICTORIAN);
      expect(computeEra(1890, 1895)).toBe(Era.VICTORIAN);
    });
  });

  describe("Edwardian era (1902-1910)", () => {
    it("returns Edwardian for year 1902", () => {
      expect(computeEra(1902, null)).toBe(Era.EDWARDIAN);
    });

    it("returns Edwardian for year 1910", () => {
      expect(computeEra(1910, 1910)).toBe(Era.EDWARDIAN);
    });

    it("returns Edwardian for years in the middle of the era", () => {
      expect(computeEra(1905, 1908)).toBe(Era.EDWARDIAN);
    });
  });

  describe("Post-1910 era (after 1910)", () => {
    it("returns Post-1910 for year 1911", () => {
      expect(computeEra(1911, null)).toBe(Era.POST_1910);
    });

    it("returns Post-1910 for later years", () => {
      expect(computeEra(1920, 1925)).toBe(Era.POST_1910);
      expect(computeEra(2000, null)).toBe(Era.POST_1910);
    });
  });

  describe("yearStart takes precedence over yearEnd (matches backend)", () => {
    it("uses yearStart when both are provided", () => {
      // Book published 1835-1840 - use start year (1835) = Romantic (not Victorian)
      expect(computeEra(1835, 1840)).toBe(Era.ROMANTIC);
    });

    it("uses yearStart even when yearEnd would give different era", () => {
      // Start in Victorian, end in Edwardian - use start = Victorian
      expect(computeEra(1899, 1905)).toBe(Era.VICTORIAN);
    });
  });
});
