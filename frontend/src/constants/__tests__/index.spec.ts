import { describe, it, expect } from "vitest";
import {
  BOOK_STATUS_OPTIONS,
  BOOK_STATUSES,
  PAGINATION,
  FILTERS,
  UI_TIMING,
  PUBLISHER_TIER_OPTIONS,
  PUBLISHER_TIERS,
} from "../index";

describe("constants", () => {
  describe("BOOK_STATUS_OPTIONS", () => {
    it("has all required status options", () => {
      expect(BOOK_STATUS_OPTIONS).toHaveLength(4);
    });

    it("has display labels for each status", () => {
      for (const option of BOOK_STATUS_OPTIONS) {
        expect(option.label).toBeTruthy();
        expect(option.label.length).toBeGreaterThan(0);
      }
    });

    it("derives values from BOOK_STATUSES (referential integrity)", () => {
      // Each option's value should reference the same object as BOOK_STATUSES
      const statusValues = Object.values(BOOK_STATUSES);
      const optionValues = BOOK_STATUS_OPTIONS.map((o) => o.value);
      expect(optionValues).toEqual(statusValues);
    });
  });

  describe("BOOK_STATUSES", () => {
    it("has exactly 4 status types", () => {
      expect(Object.keys(BOOK_STATUSES)).toHaveLength(4);
    });

    it("has required status keys", () => {
      expect(BOOK_STATUSES).toHaveProperty("EVALUATING");
      expect(BOOK_STATUSES).toHaveProperty("ON_HAND");
      expect(BOOK_STATUSES).toHaveProperty("IN_TRANSIT");
      expect(BOOK_STATUSES).toHaveProperty("REMOVED");
    });
  });

  describe("PAGINATION", () => {
    it("has reasonable page size defaults", () => {
      expect(PAGINATION.DEFAULT_PER_PAGE).toBeGreaterThan(0);
      expect(PAGINATION.RECEIVED_PER_PAGE).toBeGreaterThan(0);
      expect(PAGINATION.BOOKS_PER_PAGE).toBeGreaterThan(0);
    });

    it("DEFAULT_PER_PAGE is larger than BOOKS_PER_PAGE", () => {
      // API fetches use larger pages, UI pagination uses smaller
      expect(PAGINATION.DEFAULT_PER_PAGE).toBeGreaterThan(PAGINATION.BOOKS_PER_PAGE);
    });
  });

  describe("FILTERS", () => {
    it("has reasonable lookback window", () => {
      expect(FILTERS.RECEIVED_DAYS_LOOKBACK).toBeGreaterThan(0);
      expect(FILTERS.RECEIVED_DAYS_LOOKBACK).toBeLessThanOrEqual(90);
    });
  });

  describe("UI_TIMING", () => {
    it("has reasonable timing values", () => {
      expect(UI_TIMING.COMBOBOX_BLUR_DELAY_MS).toBeGreaterThan(0);
      expect(UI_TIMING.COMBOBOX_BLUR_DELAY_MS).toBeLessThan(1000);
    });
  });

  describe("PUBLISHER_TIER_OPTIONS", () => {
    it("has human-readable labels for all tiers", () => {
      expect(PUBLISHER_TIER_OPTIONS).toEqual([
        { value: "TIER_1", label: "Tier 1" },
        { value: "TIER_2", label: "Tier 2" },
        { value: "TIER_3", label: "Tier 3" },
        { value: "TIER_4", label: "Tier 4" },
      ]);
    });

    it("has all 4 tier options", () => {
      expect(PUBLISHER_TIER_OPTIONS).toHaveLength(4);
    });
  });

  describe("PUBLISHER_TIERS", () => {
    it("has exactly 4 tier types", () => {
      expect(Object.keys(PUBLISHER_TIERS)).toHaveLength(4);
    });

    it("has required tier keys", () => {
      expect(PUBLISHER_TIERS.TIER_1).toBe("TIER_1");
      expect(PUBLISHER_TIERS.TIER_2).toBe("TIER_2");
      expect(PUBLISHER_TIERS.TIER_3).toBe("TIER_3");
      expect(PUBLISHER_TIERS.TIER_4).toBe("TIER_4");
    });
  });
});
