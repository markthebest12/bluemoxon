import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import AnalysisIssuesWarning from "../AnalysisIssuesWarning.vue";

describe("AnalysisIssuesWarning", () => {
  it("renders nothing when issues is null", () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: null },
    });
    expect(wrapper.text()).toBe("");
  });

  it("renders nothing when issues is empty array", () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: [] },
    });
    expect(wrapper.text()).toBe("");
  });

  it("renders warning emoji when issues exist", () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: ["truncated"] },
    });
    expect(wrapper.text()).toContain("⚠️");
  });

  it("shows tooltip on hover", async () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: ["truncated"] },
    });

    const tooltip = wrapper.find('[role="tooltip"]');
    // v-show uses display:none, check the style attribute
    expect(tooltip.attributes("style")).toContain("display: none");
    await wrapper.find(".relative").trigger("mouseenter");
    expect(tooltip.attributes("style")).not.toContain("display: none");
    expect(tooltip.text()).toContain("Truncated");
  });

  it("has correct aria attributes for accessibility", () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: ["truncated"] },
    });
    const span = wrapper.find('[role="img"]');
    expect(span.attributes("aria-label")).toBe("Analysis has issues");
  });
});
