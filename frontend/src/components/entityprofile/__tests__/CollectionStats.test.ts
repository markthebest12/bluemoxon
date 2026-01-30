import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import CollectionStats from "../CollectionStats.vue";
import type { ProfileStats } from "@/types/entityProfile";

const mockStats: ProfileStats = {
  total_books: 2,
  total_estimated_value: 800,
  first_editions: 0,
  date_range: [1877, 1920],
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
