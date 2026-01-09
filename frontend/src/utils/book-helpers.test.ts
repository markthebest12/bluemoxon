import { describe, it, expect } from "vitest";
import { computeEra } from "./book-helpers";

describe("computeEra", () => {
  it("returns null when yearStart is null", () => {
    expect(computeEra(null, null)).toBe(null);
    expect(computeEra(null, 1850)).toBe(null);
  });

  it("returns 'Pre-Victorian' for years before 1837", () => {
    expect(computeEra(1800, null)).toBe("Pre-Victorian");
    expect(computeEra(1836, 1836)).toBe("Pre-Victorian");
  });

  it("returns 'Early Victorian' for years 1837-1860", () => {
    expect(computeEra(1837, null)).toBe("Early Victorian");
    expect(computeEra(1850, 1855)).toBe("Early Victorian");
    expect(computeEra(1860, 1860)).toBe("Early Victorian");
  });

  it("returns 'Mid-Victorian' for years 1861-1880", () => {
    expect(computeEra(1861, null)).toBe("Mid-Victorian");
    expect(computeEra(1870, 1875)).toBe("Mid-Victorian");
    expect(computeEra(1880, 1880)).toBe("Mid-Victorian");
  });

  it("returns 'Late Victorian' for years 1881-1901", () => {
    expect(computeEra(1881, null)).toBe("Late Victorian");
    expect(computeEra(1890, 1895)).toBe("Late Victorian");
    expect(computeEra(1901, 1901)).toBe("Late Victorian");
  });

  it("returns 'Edwardian' for years 1902-1910", () => {
    expect(computeEra(1902, null)).toBe("Edwardian");
    expect(computeEra(1905, 1908)).toBe("Edwardian");
    expect(computeEra(1910, 1910)).toBe("Edwardian");
  });

  it("returns 'Later' for years after 1910", () => {
    expect(computeEra(1911, null)).toBe("Later");
    expect(computeEra(1920, 1925)).toBe("Later");
  });

  it("uses yearStart when yearEnd is null", () => {
    expect(computeEra(1850, null)).toBe("Early Victorian");
  });

  it("uses yearEnd when both are provided", () => {
    // Book published 1835-1840 - use end year (1840) = Early Victorian
    expect(computeEra(1835, 1840)).toBe("Early Victorian");
  });
});
