import { describe, it, expect } from "vitest";
import {
  BOOK_STATUS_OPTIONS,
  BOOK_STATUSES,
  PAGINATION,
  UI_TIMING,
} from "../index";

describe("constants", () => {
  describe("BOOK_STATUS_OPTIONS", () => {
    it("has all required status options", () => {
      expect(BOOK_STATUS_OPTIONS).toHaveLength(4);
      expect(BOOK_STATUS_OPTIONS.map((s) => s.value)).toEqual([
        "EVALUATING",
        "ON_HAND",
        "IN_TRANSIT",
        "REMOVED",
      ]);
    });

    it("has display labels", () => {
      const evaluating = BOOK_STATUS_OPTIONS.find((s) => s.value === "EVALUATING");
      expect(evaluating?.label).toBe("EVAL");
    });
  });

  describe("BOOK_STATUSES", () => {
    it("exports status string constants", () => {
      expect(BOOK_STATUSES.EVALUATING).toBe("EVALUATING");
      expect(BOOK_STATUSES.ON_HAND).toBe("ON_HAND");
      expect(BOOK_STATUSES.IN_TRANSIT).toBe("IN_TRANSIT");
      expect(BOOK_STATUSES.REMOVED).toBe("REMOVED");
    });
  });

  describe("PAGINATION", () => {
    it("exports pagination limits", () => {
      expect(PAGINATION.DEFAULT_PER_PAGE).toBe(100);
      expect(PAGINATION.RECEIVED_PER_PAGE).toBe(50);
      expect(PAGINATION.RECEIVED_DAYS_LOOKBACK).toBe(30);
    });
  });

  describe("UI_TIMING", () => {
    it("exports timing constants", () => {
      expect(UI_TIMING.COMBOBOX_BLUR_DELAY_MS).toBe(200);
    });
  });
});
