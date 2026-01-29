import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import NetworkLegend from "../NetworkLegend.vue";

describe("NetworkLegend", () => {
  describe("rendering", () => {
    it("renders the component", () => {
      const wrapper = mount(NetworkLegend);

      expect(wrapper.find(".network-legend").exists()).toBe(true);
    });

    it("renders two sections: Nodes and Connections", () => {
      const wrapper = mount(NetworkLegend);

      const sections = wrapper.findAll(".network-legend__section");
      expect(sections).toHaveLength(2);

      const titles = wrapper.findAll(".network-legend__title");
      expect(titles[0].text()).toBe("Nodes");
      expect(titles[1].text()).toBe("Connections");
    });
  });

  describe("node types", () => {
    it("renders legend items for each node type", () => {
      const wrapper = mount(NetworkLegend);

      expect(wrapper.text()).toContain("Author");
      expect(wrapper.text()).toContain("Publisher");
      expect(wrapper.text()).toContain("Binder");
    });

    it("displays shape indicators for node types", () => {
      const wrapper = mount(NetworkLegend);

      const shapes = wrapper.findAll(".network-legend__shape");
      expect(shapes).toHaveLength(3);

      expect(shapes[0].classes()).toContain("network-legend__shape--circle");
      expect(shapes[1].classes()).toContain("network-legend__shape--square");
      expect(shapes[2].classes()).toContain("network-legend__shape--diamond");
    });

    it("applies correct colors to node shape indicators", () => {
      const wrapper = mount(NetworkLegend);

      const shapes = wrapper.findAll(".network-legend__shape");

      // Author - hunter green
      expect(shapes[0].attributes("style")).toContain(
        "background-color: var(--color-victorian-hunter-600)"
      );
      // Publisher - gold
      expect(shapes[1].attributes("style")).toContain(
        "background-color: var(--color-victorian-gold)"
      );
      // Binder - burgundy
      expect(shapes[2].attributes("style")).toContain(
        "background-color: var(--color-victorian-burgundy)"
      );
    });
  });

  describe("connection types", () => {
    it("renders legend items for each connection type", () => {
      const wrapper = mount(NetworkLegend);

      expect(wrapper.text()).toContain("Published by");
      expect(wrapper.text()).toContain("Shared publisher");
      expect(wrapper.text()).toContain("Bound by");
    });

    it("displays line indicators for connection types", () => {
      const wrapper = mount(NetworkLegend);

      const lines = wrapper.findAll(".network-legend__line");
      expect(lines).toHaveLength(3);
    });

    it("applies correct line styles to connection indicators", () => {
      const wrapper = mount(NetworkLegend);

      const lines = wrapper.findAll(".network-legend__line");

      // Published by - solid
      expect(lines[0].classes()).toContain("network-legend__line--solid");
      // Shared publisher - solid
      expect(lines[1].classes()).toContain("network-legend__line--solid");
      // Bound by - dashed
      expect(lines[2].classes()).toContain("network-legend__line--dashed");
    });

    it("applies correct colors to connection line indicators", () => {
      const wrapper = mount(NetworkLegend);

      const lines = wrapper.findAll(".network-legend__line");

      // Published by - gold
      expect(lines[0].attributes("style")).toContain(
        "background-color: var(--color-victorian-gold)"
      );
      // Shared publisher - hunter green
      expect(lines[1].attributes("style")).toContain(
        "background-color: var(--color-victorian-hunter-500)"
      );
      // Bound by - burgundy
      expect(lines[2].attributes("style")).toContain(
        "background-color: var(--color-victorian-burgundy)"
      );
    });
  });

  describe("structure", () => {
    it("renders items within items containers", () => {
      const wrapper = mount(NetworkLegend);

      const itemContainers = wrapper.findAll(".network-legend__items");
      expect(itemContainers).toHaveLength(2);

      // First container has 3 node items
      expect(itemContainers[0].findAll(".network-legend__item")).toHaveLength(3);
      // Second container has 3 connection items
      expect(itemContainers[1].findAll(".network-legend__item")).toHaveLength(3);
    });

    it("renders labels for all items", () => {
      const wrapper = mount(NetworkLegend);

      const labels = wrapper.findAll(".network-legend__label");
      expect(labels).toHaveLength(6);

      const labelTexts = labels.map((label) => label.text());
      expect(labelTexts).toContain("Author");
      expect(labelTexts).toContain("Publisher");
      expect(labelTexts).toContain("Binder");
      expect(labelTexts).toContain("Published by");
      expect(labelTexts).toContain("Shared publisher");
      expect(labelTexts).toContain("Bound by");
    });
  });

  describe("styling", () => {
    it("has correct root class for positioning", () => {
      const wrapper = mount(NetworkLegend);

      expect(wrapper.find(".network-legend").exists()).toBe(true);
    });

    it("each item has proper flex layout with gap", () => {
      const wrapper = mount(NetworkLegend);

      const items = wrapper.findAll(".network-legend__item");
      // Each item should have both a shape/line indicator and a label
      items.forEach((item) => {
        const children = item.element.children;
        expect(children.length).toBe(2);
      });
    });
  });
});
