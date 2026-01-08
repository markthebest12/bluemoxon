import { describe, it, expect } from "vitest";
import { formatAcquisitionTooltip } from "../chartHelpers";
import type { AcquisitionDay } from "@/types/dashboard";

describe("StatisticsDashboard chart helpers", () => {
  describe("formatAcquisitionTooltip", () => {
    it("uses the day label in tooltip, not hardcoded 'today'", () => {
      const day: AcquisitionDay = {
        date: "2026-01-05",
        label: "Jan 5",
        count: 3,
        value: 450,
        cost: 200,
        cumulative_count: 10,
        cumulative_value: 5000,
        cumulative_cost: 2000,
      };

      const result = formatAcquisitionTooltip(day);
      const joined = result.join(" ");

      // Should use the actual date label, not "today"
      expect(joined).toContain("Jan 5");
      expect(joined).not.toMatch(/\btoday\b/i);
    });

    it("formats cumulative value and daily additions correctly", () => {
      const day: AcquisitionDay = {
        date: "2026-01-08",
        label: "Today",
        count: 2,
        value: 1500,
        cost: 500,
        cumulative_count: 50,
        cumulative_value: 25000,
        cumulative_cost: 10000,
      };

      const result = formatAcquisitionTooltip(day);
      const joined = result.join(" ");

      expect(joined).toContain("Total: $25,000");
      expect(joined).toContain("Today");
      expect(joined).toContain("2 items");
      expect(joined).toContain("$1,500");
    });

    it("uses singular 'item' for count of 1", () => {
      const day: AcquisitionDay = {
        date: "2026-01-03",
        label: "Jan 3",
        count: 1,
        value: 300,
        cost: 100,
        cumulative_count: 5,
        cumulative_value: 2500,
        cumulative_cost: 1000,
      };

      const result = formatAcquisitionTooltip(day);
      const joined = result.join(" ");

      expect(joined).toContain("1 item");
      expect(joined).not.toContain("1 items");
    });

    it("returns empty array for undefined day", () => {
      const result = formatAcquisitionTooltip(undefined);
      expect(result).toEqual([]);
    });
  });
});
