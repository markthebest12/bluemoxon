import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import AnalysisIssuesWarning from "../AnalysisIssuesWarning.vue";
import BaseTooltip from "../BaseTooltip.vue";

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

  describe("tooltip behavior", () => {
    let wrapper: ReturnType<typeof mount>;
    let container: HTMLElement;

    beforeEach(() => {
      // Create a container for the component
      container = document.createElement("div");
      container.id = "test-container";
      document.body.appendChild(container);

      wrapper = mount(AnalysisIssuesWarning, {
        props: { issues: ["truncated"] },
        attachTo: container,
      });
    });

    afterEach(() => {
      wrapper.unmount();
      // Clean up any teleported tooltips
      document.querySelectorAll('[role="tooltip"]').forEach((el) => el.remove());
      document.getElementById("test-container")?.remove();
    });

    it("has tooltip with correct content teleported to body", async () => {
      // Tooltip is teleported to body - verify it exists and has correct content
      const tooltip = document.body.querySelector('[role="tooltip"]');
      expect(tooltip).toBeTruthy();
      expect(tooltip?.textContent).toContain("Truncated");

      // Verify BaseTooltip component is properly mounted
      const baseTooltip = wrapper.findComponent(BaseTooltip);
      expect(baseTooltip.exists()).toBe(true);

      // Verify trigger element has correct attributes for interaction
      const trigger = wrapper.find('[tabindex="0"]');
      expect(trigger.exists()).toBe(true);
    });

    it("tooltip is initially hidden", () => {
      // v-show adds display:none when isVisible is false
      const tooltip = document.body.querySelector('[role="tooltip"]');
      expect(tooltip?.getAttribute("style")).toContain("display: none");
    });
  });

  it("has correct aria attributes for accessibility", () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: ["truncated"] },
    });
    const span = wrapper.find('[role="img"]');
    expect(span.attributes("aria-label")).toBe("Analysis has issues");
  });
});
