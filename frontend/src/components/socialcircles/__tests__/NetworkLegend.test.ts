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

      // Book-based connections
      expect(wrapper.text()).toContain("Publisher");
      expect(wrapper.text()).toContain("Binder");
      // AI-discovered connections
      expect(wrapper.text()).toContain("Personal");
      expect(wrapper.text()).toContain("Influence");
      expect(wrapper.text()).toContain("Scandal");
    });

    it("displays line indicators for connection types", () => {
      const wrapper = mount(NetworkLegend);

      const lines = wrapper.findAll(".network-legend__line");
      expect(lines).toHaveLength(5);
    });

    it("applies correct line styles to connection indicators", () => {
      const wrapper = mount(NetworkLegend);

      const lines = wrapper.findAll(".network-legend__line");

      // Publisher - solid
      expect(lines[0].classes()).toContain("network-legend__line--solid");
      // Binder - dashed
      expect(lines[1].classes()).toContain("network-legend__line--dashed");
      // Personal - solid
      expect(lines[2].classes()).toContain("network-legend__line--solid");
      // Influence - dotted
      expect(lines[3].classes()).toContain("network-legend__line--dotted");
      // Scandal - dashed
      expect(lines[4].classes()).toContain("network-legend__line--dashed");
    });

    it("applies correct colors to connection line indicators", () => {
      const wrapper = mount(NetworkLegend);

      const lines = wrapper.findAll(".network-legend__line");

      // Publisher - green (#4ade80)
      expect(lines[0].attributes("style")).toContain("background-color: rgb(74, 222, 128)");
      // Binder - purple (#a78bfa)
      expect(lines[1].attributes("style")).toContain("background-color: rgb(167, 139, 250)");
      // Personal - blue (#60a5fa)
      expect(lines[2].attributes("style")).toContain("background-color: rgb(96, 165, 250)");
      // Influence - blue (#60a5fa)
      expect(lines[3].attributes("style")).toContain("background-color: rgb(96, 165, 250)");
      // Scandal - red (#f87171)
      expect(lines[4].attributes("style")).toContain("background-color: rgb(248, 113, 113)");
    });
  });

  describe("structure", () => {
    it("renders items within items containers", () => {
      const wrapper = mount(NetworkLegend);

      const itemContainers = wrapper.findAll(".network-legend__items");
      expect(itemContainers).toHaveLength(2);

      // First container has 3 node items
      expect(itemContainers[0].findAll(".network-legend__item")).toHaveLength(3);
      // Second container has 5 connection items (2 book-based + 3 AI-discovered)
      expect(itemContainers[1].findAll(".network-legend__item")).toHaveLength(5);
    });

    it("renders labels for all items", () => {
      const wrapper = mount(NetworkLegend);

      const labels = wrapper.findAll(".network-legend__label");
      expect(labels).toHaveLength(8); // 3 nodes + 5 connections

      const labelTexts = labels.map((label) => label.text());
      // Node types
      expect(labelTexts).toContain("Author");
      expect(labelTexts).toContain("Publisher");
      expect(labelTexts).toContain("Binder");
      // Connection types (book-based + AI-discovered)
      expect(labelTexts).toContain("Personal");
      expect(labelTexts).toContain("Influence");
      expect(labelTexts).toContain("Scandal");
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
