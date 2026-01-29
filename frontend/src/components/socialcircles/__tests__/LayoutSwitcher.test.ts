import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, VueWrapper } from "@vue/test-utils";
import LayoutSwitcher from "../LayoutSwitcher.vue";
import type { LayoutMode } from "@/types/socialCircles";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mountSwitcher(props: Partial<InstanceType<typeof LayoutSwitcher>["$props"]> = {}) {
  return mount(LayoutSwitcher, {
    props: {
      modelValue: "force" as LayoutMode,
      ...props,
    },
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("LayoutSwitcher", () => {
  let wrapper: VueWrapper;

  afterEach(() => {
    wrapper?.unmount();
    vi.restoreAllMocks();
  });

  // =========================================================================
  // Rendering
  // =========================================================================

  describe("rendering", () => {
    it("renders the layout switcher container", () => {
      wrapper = mountSwitcher();
      expect(wrapper.find(".layout-switcher").exists()).toBe(true);
    });

    it("renders four layout buttons", () => {
      wrapper = mountSwitcher();
      const buttons = wrapper.findAll(".layout-switcher__btn");
      expect(buttons.length).toBe(4);
    });

    it("renders Force label", () => {
      wrapper = mountSwitcher();
      const labels = wrapper.findAll(".layout-switcher__label");
      expect(labels[0].text()).toBe("Force");
    });

    it("renders Circle label", () => {
      wrapper = mountSwitcher();
      const labels = wrapper.findAll(".layout-switcher__label");
      expect(labels[1].text()).toBe("Circle");
    });

    it("renders Grid label", () => {
      wrapper = mountSwitcher();
      const labels = wrapper.findAll(".layout-switcher__label");
      expect(labels[2].text()).toBe("Grid");
    });

    it("renders Hierarchy label", () => {
      wrapper = mountSwitcher();
      const labels = wrapper.findAll(".layout-switcher__label");
      expect(labels[3].text()).toBe("Hierarchy");
    });

    it("renders icons for all layout modes", () => {
      wrapper = mountSwitcher();
      const icons = wrapper.findAll(".layout-switcher__icon");
      expect(icons.length).toBe(4);
      // Each should have non-empty text content
      icons.forEach((icon) => {
        expect(icon.text().length).toBeGreaterThan(0);
      });
    });

    it("renders tooltip descriptions as title attributes", () => {
      wrapper = mountSwitcher();
      const buttons = wrapper.findAll(".layout-switcher__btn");
      expect(buttons[0].attributes("title")).toBe("Physics-based layout");
      expect(buttons[1].attributes("title")).toBe("Circular arrangement");
      expect(buttons[2].attributes("title")).toBe("Grid layout");
      expect(buttons[3].attributes("title")).toBe("Tree structure");
    });
  });

  // =========================================================================
  // Active state
  // =========================================================================

  describe("active state", () => {
    it("applies active class to force button when force is selected", () => {
      wrapper = mountSwitcher({ modelValue: "force" });
      const buttons = wrapper.findAll(".layout-switcher__btn");
      expect(buttons[0].classes()).toContain("layout-switcher__btn--active");
    });

    it("applies active class to circle button when circle is selected", () => {
      wrapper = mountSwitcher({ modelValue: "circle" });
      const buttons = wrapper.findAll(".layout-switcher__btn");
      expect(buttons[1].classes()).toContain("layout-switcher__btn--active");
    });

    it("applies active class to grid button when grid is selected", () => {
      wrapper = mountSwitcher({ modelValue: "grid" });
      const buttons = wrapper.findAll(".layout-switcher__btn");
      expect(buttons[2].classes()).toContain("layout-switcher__btn--active");
    });

    it("applies active class to hierarchical button when hierarchical is selected", () => {
      wrapper = mountSwitcher({ modelValue: "hierarchical" });
      const buttons = wrapper.findAll(".layout-switcher__btn");
      expect(buttons[3].classes()).toContain("layout-switcher__btn--active");
    });

    it("only one button has active class at a time", () => {
      wrapper = mountSwitcher({ modelValue: "grid" });
      const activeButtons = wrapper.findAll(".layout-switcher__btn--active");
      expect(activeButtons.length).toBe(1);
    });

    it("non-active buttons do not have active class", () => {
      wrapper = mountSwitcher({ modelValue: "force" });
      const buttons = wrapper.findAll(".layout-switcher__btn");
      expect(buttons[1].classes()).not.toContain("layout-switcher__btn--active");
      expect(buttons[2].classes()).not.toContain("layout-switcher__btn--active");
      expect(buttons[3].classes()).not.toContain("layout-switcher__btn--active");
    });
  });

  // =========================================================================
  // Button interactions
  // =========================================================================

  describe("button interactions", () => {
    it("emits update:modelValue with force when Force clicked", async () => {
      wrapper = mountSwitcher({ modelValue: "circle" });
      const buttons = wrapper.findAll(".layout-switcher__btn");

      await buttons[0].trigger("click");

      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
      expect(wrapper.emitted("update:modelValue")![0]).toEqual(["force"]);
    });

    it("emits update:modelValue with circle when Circle clicked", async () => {
      wrapper = mountSwitcher({ modelValue: "force" });
      const buttons = wrapper.findAll(".layout-switcher__btn");

      await buttons[1].trigger("click");

      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
      expect(wrapper.emitted("update:modelValue")![0]).toEqual(["circle"]);
    });

    it("emits update:modelValue with grid when Grid clicked", async () => {
      wrapper = mountSwitcher({ modelValue: "force" });
      const buttons = wrapper.findAll(".layout-switcher__btn");

      await buttons[2].trigger("click");

      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
      expect(wrapper.emitted("update:modelValue")![0]).toEqual(["grid"]);
    });

    it("emits update:modelValue with hierarchical when Hierarchy clicked", async () => {
      wrapper = mountSwitcher({ modelValue: "force" });
      const buttons = wrapper.findAll(".layout-switcher__btn");

      await buttons[3].trigger("click");

      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
      expect(wrapper.emitted("update:modelValue")![0]).toEqual(["hierarchical"]);
    });

    it("still emits when clicking the already-active mode", async () => {
      wrapper = mountSwitcher({ modelValue: "force" });
      const buttons = wrapper.findAll(".layout-switcher__btn");

      await buttons[0].trigger("click");

      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
      expect(wrapper.emitted("update:modelValue")![0]).toEqual(["force"]);
    });
  });

  // =========================================================================
  // Disabled state
  // =========================================================================

  describe("disabled state", () => {
    it("applies disabled class to container when disabled", () => {
      wrapper = mountSwitcher({ disabled: true });
      expect(wrapper.find(".layout-switcher").classes()).toContain("layout-switcher--disabled");
    });

    it("does not apply disabled class when not disabled", () => {
      wrapper = mountSwitcher({ disabled: false });
      expect(wrapper.find(".layout-switcher").classes()).not.toContain("layout-switcher--disabled");
    });

    it("sets disabled attribute on all buttons when disabled", () => {
      wrapper = mountSwitcher({ disabled: true });
      const buttons = wrapper.findAll(".layout-switcher__btn");
      buttons.forEach((btn) => {
        expect((btn.element as HTMLButtonElement).disabled).toBe(true);
      });
    });

    it("does not set disabled attribute on buttons when not disabled", () => {
      wrapper = mountSwitcher({ disabled: false });
      const buttons = wrapper.findAll(".layout-switcher__btn");
      buttons.forEach((btn) => {
        expect((btn.element as HTMLButtonElement).disabled).toBe(false);
      });
    });

    it("defaults disabled to false", () => {
      wrapper = mountSwitcher();
      expect(wrapper.find(".layout-switcher").classes()).not.toContain("layout-switcher--disabled");
    });
  });

  // =========================================================================
  // Button type
  // =========================================================================

  describe("button type", () => {
    it("all buttons have type=button", () => {
      wrapper = mountSwitcher();
      const buttons = wrapper.findAll(".layout-switcher__btn");
      buttons.forEach((btn) => {
        expect(btn.attributes("type")).toBe("button");
      });
    });
  });
});
