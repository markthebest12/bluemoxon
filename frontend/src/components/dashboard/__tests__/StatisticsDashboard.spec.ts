import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import { formatAcquisitionTooltip } from "../chartHelpers";
import StatisticsDashboard from "../StatisticsDashboard.vue";
import type { AcquisitionDay, DashboardStats } from "@/types/dashboard";

describe("StatisticsDashboard chart helpers", () => {
  describe("formatAcquisitionTooltip", () => {
    it("uses the day label in tooltip, not hardcoded 'today'", () => {
      const day: AcquisitionDay = {
        date: "2026-01-05",
        label: "Jan 05",
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
      expect(joined).toContain("Jan 05");
      expect(joined).not.toMatch(/\btoday\b/i);
    });

    it("formats cumulative value and daily additions correctly", () => {
      const day: AcquisitionDay = {
        date: "2026-01-08",
        label: "Jan 08",
        count: 2,
        value: 1500,
        cost: 500,
        cumulative_count: 50,
        cumulative_value: 25000,
        cumulative_cost: 10000,
      };

      const result = formatAcquisitionTooltip(day);
      const joined = result.join(" ");

      // Use regex to handle locale-independent number formatting (25,000 or 25.000)
      expect(joined).toMatch(/Total: \$25[,.]000/);
      expect(joined).toContain("Jan 08");
      expect(joined).toContain("2 items");
      expect(joined).toMatch(/\$1[,.]500/);
    });

    it("uses singular 'item' for count of 1", () => {
      const day: AcquisitionDay = {
        date: "2026-01-03",
        label: "Jan 03",
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

  describe("StatisticsDashboard component integration", () => {
    const mockDashboardData: DashboardStats = {
      overview: {
        primary: { count: 10, volumes: 20, value_low: 1000, value_mid: 1500, value_high: 2000 },
        extended: { count: 1 },
        flagged: { count: 0 },
        total_items: 11,
        authenticated_bindings: 5,
        in_transit: 2,
        week_delta: { count: 3, volumes: 5, value_mid: 500, authenticated_bindings: 1 },
      },
      bindings: [],
      by_era: [],
      by_publisher: [],
      by_author: [],
      by_condition: [],
      by_category: [],
      acquisitions_daily: [
        {
          date: "2026-01-05",
          label: "Jan 05",
          count: 3,
          value: 450,
          cost: 200,
          cumulative_count: 10,
          cumulative_value: 5000,
          cumulative_cost: 2000,
        },
        {
          date: "2026-01-06",
          label: "Jan 06",
          count: 0,
          value: 0,
          cost: 0,
          cumulative_count: 10,
          cumulative_value: 5000,
          cumulative_cost: 2000,
        },
      ],
    };

    it("uses formatAcquisitionTooltip in lineChartOptions tooltip callback", () => {
      const wrapper = mount(StatisticsDashboard, {
        props: { data: mockDashboardData },
        global: {
          stubs: {
            Line: true,
            Doughnut: true,
            Bar: true,
          },
        },
      });

      // Access the computed lineChartOptions via component instance
      const vm = wrapper.vm as unknown as {
        lineChartOptions: {
          plugins: {
            tooltip: {
              callbacks: {
                label: (context: { dataIndex: number }) => string[];
              };
            };
          };
        };
      };

      // Simulate tooltip callback with dataIndex pointing to first day
      const tooltipResult = vm.lineChartOptions.plugins.tooltip.callbacks.label({
        dataIndex: 0,
      });

      // Verify it uses the day's label, not hardcoded "today"
      const joined = tooltipResult.join(" ");
      expect(joined).toContain("Jan 05");
      expect(joined).not.toMatch(/\btoday\b/i);
    });

    it("tooltip callback handles out-of-bounds index gracefully", () => {
      const wrapper = mount(StatisticsDashboard, {
        props: { data: mockDashboardData },
        global: {
          stubs: {
            Line: true,
            Doughnut: true,
            Bar: true,
          },
        },
      });

      const vm = wrapper.vm as unknown as {
        lineChartOptions: {
          plugins: {
            tooltip: {
              callbacks: {
                label: (context: { dataIndex: number }) => string[];
              };
            };
          };
        };
      };

      // Out of bounds index should return empty array (via formatAcquisitionTooltip)
      const tooltipResult = vm.lineChartOptions.plugins.tooltip.callbacks.label({
        dataIndex: 999,
      });

      expect(tooltipResult).toEqual([]);
    });

    it("formats condition chart labels as human-readable text", () => {
      const dataWithConditions: DashboardStats = {
        ...mockDashboardData,
        by_condition: [
          { condition: "NEAR_FINE", count: 5, value: 1000 },
          { condition: "VERY_GOOD", count: 3, value: 600 },
          { condition: "FINE", count: 2, value: 800 },
          { condition: "Ungraded", count: 1, value: 100 }, // Backend converts null to "Ungraded"
        ],
      };

      const wrapper = mount(StatisticsDashboard, {
        props: { data: dataWithConditions },
        global: {
          stubs: {
            Line: true,
            Doughnut: true,
            Bar: true,
          },
        },
      });

      const vm = wrapper.vm as unknown as {
        conditionChartData: {
          labels: string[];
        };
      };

      // Verify labels are human-readable, not raw enum values
      expect(vm.conditionChartData.labels).toEqual(["Near Fine", "Very Good", "Fine", "Ungraded"]);
    });
  });
});
