import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import CollectionStats from "../CollectionStats.vue";
import type { ProfileStats } from "@/types/entityProfile";

const mockStats: ProfileStats = {
  total_books: 2,
  total_estimated_value: 800,
  first_editions: 0,
  date_range: [1877, 1920],
  condition_distribution: {},
  acquisition_by_year: {},
};

describe("CollectionStats", () => {
  it("renders total books", () => {
    const wrapper = mount(CollectionStats, { props: { stats: mockStats } });
    expect(wrapper.text()).toContain("2");
  });

  it("renders estimated value", () => {
    const wrapper = mount(CollectionStats, { props: { stats: mockStats } });
    expect(wrapper.text()).toContain("$800");
  });

  it("renders date range", () => {
    const wrapper = mount(CollectionStats, { props: { stats: mockStats } });
    expect(wrapper.text()).toContain("1877");
    expect(wrapper.text()).toContain("1920");
  });

  it("hides first editions when zero", () => {
    const wrapper = mount(CollectionStats, { props: { stats: mockStats } });
    expect(wrapper.text()).not.toContain("First Editions");
  });

  it("shows first editions when present", () => {
    const statsWithFE: ProfileStats = { ...mockStats, first_editions: 1 };
    const wrapper = mount(CollectionStats, { props: { stats: statsWithFE } });
    expect(wrapper.text()).toContain("First Editions");
  });
});

describe("CollectionStats — Condition Breakdown", () => {
  it("renders stacked bar with correct number of segments", () => {
    const stats: ProfileStats = {
      ...mockStats,
      condition_distribution: { FINE: 5, GOOD: 3, POOR: 2 },
    };
    const wrapper = mount(CollectionStats, { props: { stats } });
    const segments = wrapper.findAll("[data-testid='condition-segment']");
    expect(segments).toHaveLength(3);
  });

  it("renders legend with all grades and counts", () => {
    const stats: ProfileStats = {
      ...mockStats,
      condition_distribution: { FINE: 5, GOOD: 3 },
    };
    const wrapper = mount(CollectionStats, { props: { stats } });
    const legend = wrapper.find("[data-testid='condition-legend']");
    expect(legend.exists()).toBe(true);
    expect(legend.text()).toContain("Fine");
    expect(legend.text()).toContain("5");
    expect(legend.text()).toContain("Good");
    expect(legend.text()).toContain("3");
  });

  it("shows single-condition text instead of bar when all same grade", () => {
    const stats: ProfileStats = {
      ...mockStats,
      condition_distribution: { FINE: 12 },
    };
    const wrapper = mount(CollectionStats, { props: { stats } });
    expect(wrapper.text()).toContain("All books: Fine (12)");
    expect(wrapper.find("[data-testid='condition-bar']").exists()).toBe(false);
  });

  it("hides condition section when distribution is empty", () => {
    const wrapper = mount(CollectionStats, { props: { stats: mockStats } });
    expect(wrapper.find("[data-testid='condition-breakdown']").exists()).toBe(false);
  });

  it("applies correct colors from conditionColors palette", () => {
    const stats: ProfileStats = {
      ...mockStats,
      condition_distribution: { FINE: 5, POOR: 2 },
    };
    const wrapper = mount(CollectionStats, { props: { stats } });
    const segments = wrapper.findAll("[data-testid='condition-segment']");
    // FINE = #2d6a4f → rgb(45, 106, 79), POOR = #9c503d → rgb(156, 80, 61)
    expect(segments[0].attributes("style")).toContain("rgb(45, 106, 79)");
    expect(segments[1].attributes("style")).toContain("rgb(156, 80, 61)");
  });
});
