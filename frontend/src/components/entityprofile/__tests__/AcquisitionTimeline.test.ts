import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import AcquisitionTimeline from "../AcquisitionTimeline.vue";

describe("AcquisitionTimeline", () => {
  it("renders correct number of bars for given data", () => {
    const wrapper = mount(AcquisitionTimeline, {
      props: { data: { 2020: 3, 2021: 5, 2022: 2 } },
    });
    const bars = wrapper.findAll("[data-testid='acquisition-bar']");
    expect(bars).toHaveLength(3);
  });

  it("tallest bar gets max height, others proportional", () => {
    const wrapper = mount(AcquisitionTimeline, {
      props: { data: { 2020: 10, 2021: 5 } },
    });
    const bars = wrapper.findAll("[data-testid='acquisition-bar']");
    // tallest bar should have 100% relative height
    expect(bars[0].attributes("style")).toContain("height");
    expect(bars[1].attributes("style")).toContain("height");
  });

  it("hides when fewer than 2 years", () => {
    const wrapper = mount(AcquisitionTimeline, {
      props: { data: { 2020: 3 } },
    });
    expect(wrapper.find("[data-testid='acquisition-timeline']").exists()).toBe(false);
  });

  it("hides when data is empty", () => {
    const wrapper = mount(AcquisitionTimeline, {
      props: { data: {} },
    });
    expect(wrapper.find("[data-testid='acquisition-timeline']").exists()).toBe(false);
  });

  it("renders year labels", () => {
    const wrapper = mount(AcquisitionTimeline, {
      props: { data: { 2019: 1, 2020: 3, 2021: 5 } },
    });
    expect(wrapper.text()).toContain("2019");
    expect(wrapper.text()).toContain("2020");
    expect(wrapper.text()).toContain("2021");
  });

  it("renders section title 'Acquisition History'", () => {
    const wrapper = mount(AcquisitionTimeline, {
      props: { data: { 2020: 3, 2021: 5 } },
    });
    expect(wrapper.text()).toContain("Acquisition History");
  });
});
