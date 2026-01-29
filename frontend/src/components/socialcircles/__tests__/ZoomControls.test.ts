import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ZoomControls from "../ZoomControls.vue";

describe("ZoomControls", () => {
  describe("rendering", () => {
    it("should render zoom in button with + text", () => {
      const wrapper = mount(ZoomControls);
      const buttons = wrapper.findAll(".zoom-controls__btn");
      expect(buttons[0].text()).toBe("+");
    });

    it("should render zoom out button with minus text", () => {
      const wrapper = mount(ZoomControls);
      const buttons = wrapper.findAll(".zoom-controls__btn");
      // Second button is zoom out (minus sign)
      expect(buttons[1].text()).toBe("\u2212"); // Unicode minus sign
    });

    it("should render fit button", () => {
      const wrapper = mount(ZoomControls);
      const fitButton = wrapper.find(".zoom-controls__btn--fit");
      expect(fitButton.exists()).toBe(true);
    });

    it("should display zoom level as percentage", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 1.5 },
      });

      const levelDisplay = wrapper.find(".zoom-controls__level");
      expect(levelDisplay.text()).toBe("150%");
    });

    it("should display default zoom level of 100%", () => {
      const wrapper = mount(ZoomControls);

      const levelDisplay = wrapper.find(".zoom-controls__level");
      expect(levelDisplay.text()).toBe("100%");
    });
  });

  describe("zoom in", () => {
    it("should emit zoom-in event when + button clicked", async () => {
      const wrapper = mount(ZoomControls);
      const zoomInButton = wrapper.findAll(".zoom-controls__btn")[0];

      await zoomInButton.trigger("click");

      expect(wrapper.emitted("zoom-in")).toBeTruthy();
      expect(wrapper.emitted("zoom-in")).toHaveLength(1);
    });

    it("should disable zoom in button when at max zoom", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 3, maxZoom: 3 },
      });

      const zoomInButton = wrapper.findAll(".zoom-controls__btn")[0];
      expect((zoomInButton.element as HTMLButtonElement).disabled).toBe(true);
    });

    it("should enable zoom in button when below max zoom", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 2, maxZoom: 3 },
      });

      const zoomInButton = wrapper.findAll(".zoom-controls__btn")[0];
      expect((zoomInButton.element as HTMLButtonElement).disabled).toBe(false);
    });
  });

  describe("zoom out", () => {
    it("should emit zoom-out event when - button clicked", async () => {
      const wrapper = mount(ZoomControls);
      const zoomOutButton = wrapper.findAll(".zoom-controls__btn")[1];

      await zoomOutButton.trigger("click");

      expect(wrapper.emitted("zoom-out")).toBeTruthy();
      expect(wrapper.emitted("zoom-out")).toHaveLength(1);
    });

    it("should disable zoom out button when at min zoom", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 0.1, minZoom: 0.1 },
      });

      const zoomOutButton = wrapper.findAll(".zoom-controls__btn")[1];
      expect((zoomOutButton.element as HTMLButtonElement).disabled).toBe(true);
    });

    it("should enable zoom out button when above min zoom", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 0.5, minZoom: 0.1 },
      });

      const zoomOutButton = wrapper.findAll(".zoom-controls__btn")[1];
      expect((zoomOutButton.element as HTMLButtonElement).disabled).toBe(false);
    });
  });

  describe("fit to view", () => {
    it("should emit fit event when fit button clicked", async () => {
      const wrapper = mount(ZoomControls);
      const fitButton = wrapper.find(".zoom-controls__btn--fit");

      await fitButton.trigger("click");

      expect(wrapper.emitted("fit")).toBeTruthy();
      expect(wrapper.emitted("fit")).toHaveLength(1);
    });

    it("should never be disabled", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 3, maxZoom: 3 },
      });

      const fitButton = wrapper.find(".zoom-controls__btn--fit");
      expect((fitButton.element as HTMLButtonElement).disabled).toBe(false);
    });
  });

  describe("button titles", () => {
    it("should have correct title for zoom in button", () => {
      const wrapper = mount(ZoomControls);
      const zoomInButton = wrapper.findAll(".zoom-controls__btn")[0];
      expect(zoomInButton.attributes("title")).toBe("Zoom In (+)");
    });

    it("should have correct title for zoom out button", () => {
      const wrapper = mount(ZoomControls);
      const zoomOutButton = wrapper.findAll(".zoom-controls__btn")[1];
      expect(zoomOutButton.attributes("title")).toBe("Zoom Out (-)");
    });

    it("should have correct title for fit button", () => {
      const wrapper = mount(ZoomControls);
      const fitButton = wrapper.find(".zoom-controls__btn--fit");
      expect(fitButton.attributes("title")).toBe("Fit to View (0)");
    });
  });

  describe("zoom level formatting", () => {
    it("should round zoom level to nearest integer percentage", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 0.333 },
      });

      const levelDisplay = wrapper.find(".zoom-controls__level");
      expect(levelDisplay.text()).toBe("33%");
    });

    it("should handle zoom levels greater than 100%", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 2.5 },
      });

      const levelDisplay = wrapper.find(".zoom-controls__level");
      expect(levelDisplay.text()).toBe("250%");
    });

    it("should handle zoom levels less than 100%", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 0.25 },
      });

      const levelDisplay = wrapper.find(".zoom-controls__level");
      expect(levelDisplay.text()).toBe("25%");
    });
  });

  describe("props defaults", () => {
    it("should use default minZoom of 0.1", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 0.1 },
      });

      const zoomOutButton = wrapper.findAll(".zoom-controls__btn")[1];
      expect((zoomOutButton.element as HTMLButtonElement).disabled).toBe(true);
    });

    it("should use default maxZoom of 3", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 3 },
      });

      const zoomInButton = wrapper.findAll(".zoom-controls__btn")[0];
      expect((zoomInButton.element as HTMLButtonElement).disabled).toBe(true);
    });

    it("should allow custom minZoom", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 0.5, minZoom: 0.5 },
      });

      const zoomOutButton = wrapper.findAll(".zoom-controls__btn")[1];
      expect((zoomOutButton.element as HTMLButtonElement).disabled).toBe(true);
    });

    it("should allow custom maxZoom", () => {
      const wrapper = mount(ZoomControls, {
        props: { zoomLevel: 5, maxZoom: 5 },
      });

      const zoomInButton = wrapper.findAll(".zoom-controls__btn")[0];
      expect((zoomInButton.element as HTMLButtonElement).disabled).toBe(true);
    });
  });
});
