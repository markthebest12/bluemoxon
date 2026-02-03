import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ConditionBadge from "../ConditionBadge.vue";

describe("ConditionBadge", () => {
  it("renders the formatted condition label", () => {
    const wrapper = mount(ConditionBadge, {
      props: { condition: "NEAR_FINE" },
    });
    expect(wrapper.text()).toBe("Near Fine");
  });

  it("applies the correct background color", () => {
    const wrapper = mount(ConditionBadge, {
      props: { condition: "FINE" },
    });
    const el = wrapper.element as HTMLElement;
    expect(el.style.backgroundColor).toBe("rgb(45, 106, 79)");
  });

  it("renders with FINE condition", () => {
    const wrapper = mount(ConditionBadge, {
      props: { condition: "FINE" },
    });
    expect(wrapper.text()).toBe("Fine");
  });

  it("renders with GOOD condition", () => {
    const wrapper = mount(ConditionBadge, {
      props: { condition: "GOOD" },
    });
    expect(wrapper.text()).toBe("Good");
  });

  it("renders with POOR condition", () => {
    const wrapper = mount(ConditionBadge, {
      props: { condition: "POOR" },
    });
    expect(wrapper.text()).toBe("Poor");
  });
});
