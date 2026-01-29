/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck - Test mocks don't need full type compliance
import { describe, it, expect } from "vitest";
import {
  getLayoutConfig,
  LAYOUT_MODE_LABELS,
  LAYOUT_MODE_DESCRIPTIONS,
  AVAILABLE_LAYOUTS,
} from "../layoutConfigs";
import type { LayoutMode } from "@/types/socialCircles";

describe("layoutConfigs", () => {
  describe("getLayoutConfig", () => {
    describe("force layout", () => {
      it("returns cose layout configuration", () => {
        const config = getLayoutConfig("force");
        expect(config.name).toBe("cose");
      });

      it("includes force-specific physics parameters", () => {
        const config = getLayoutConfig("force");
        expect(config).toHaveProperty("idealEdgeLength");
        expect(config).toHaveProperty("nodeOverlap");
        expect(config).toHaveProperty("nodeRepulsion");
        expect(config).toHaveProperty("edgeElasticity");
        expect(config).toHaveProperty("gravity");
      });

      it("has iteration and temperature settings for simulation", () => {
        const config = getLayoutConfig("force");
        expect(config).toHaveProperty("numIter", 1000);
        expect(config).toHaveProperty("initialTemp", 200);
        expect(config).toHaveProperty("coolingFactor", 0.95);
        expect(config).toHaveProperty("minTemp", 1.0);
      });

      it("enables animation with proper duration", () => {
        const config = getLayoutConfig("force");
        expect(config.animate).toBe(true);
        expect(config).toHaveProperty("animationDuration", 800);
        expect(config).toHaveProperty("animationEasing", "ease-out-quad");
      });

      it("has nodeRepulsion as a function returning expected value", () => {
        const config = getLayoutConfig("force");
        const repulsionFn = config.nodeRepulsion as () => number;
        expect(typeof repulsionFn).toBe("function");
        expect(repulsionFn()).toBe(400000);
      });

      it("has edgeElasticity as a function returning expected value", () => {
        const config = getLayoutConfig("force");
        const elasticityFn = config.edgeElasticity as () => number;
        expect(typeof elasticityFn).toBe("function");
        expect(elasticityFn()).toBe(100);
      });
    });

    describe("circle layout", () => {
      it("returns circle layout configuration", () => {
        const config = getLayoutConfig("circle");
        expect(config.name).toBe("circle");
      });

      it("includes circle-specific settings", () => {
        const config = getLayoutConfig("circle");
        expect(config).toHaveProperty("avoidOverlap", true);
        expect(config).toHaveProperty("spacingFactor", 1.5);
      });

      it("enables animation with proper duration", () => {
        const config = getLayoutConfig("circle");
        expect(config.animate).toBe(true);
        expect(config).toHaveProperty("animationDuration", 500);
      });
    });

    describe("grid layout", () => {
      it("returns grid layout configuration", () => {
        const config = getLayoutConfig("grid");
        expect(config.name).toBe("grid");
      });

      it("includes grid-specific settings", () => {
        const config = getLayoutConfig("grid");
        expect(config).toHaveProperty("avoidOverlap", true);
        expect(config).toHaveProperty("condense", true);
      });

      it("enables animation with proper duration", () => {
        const config = getLayoutConfig("grid");
        expect(config.animate).toBe(true);
        expect(config).toHaveProperty("animationDuration", 500);
      });
    });

    describe("hierarchical layout", () => {
      it("returns dagre layout configuration", () => {
        const config = getLayoutConfig("hierarchical");
        expect(config.name).toBe("dagre");
      });

      it("includes hierarchical-specific settings", () => {
        const config = getLayoutConfig("hierarchical");
        expect(config).toHaveProperty("rankDir", "TB");
        expect(config).toHaveProperty("nodeSep", 50);
        expect(config).toHaveProperty("rankSep", 100);
      });

      it("enables animation with proper duration", () => {
        const config = getLayoutConfig("hierarchical");
        expect(config.animate).toBe(true);
        expect(config).toHaveProperty("animationDuration", 500);
      });
    });

    describe("common properties", () => {
      it.each(["force", "circle", "grid", "hierarchical"] as LayoutMode[])(
        "%s layout has fit enabled",
        (mode) => {
          const config = getLayoutConfig(mode);
          expect(config.fit).toBe(true);
        }
      );

      it.each(["force", "circle", "grid", "hierarchical"] as LayoutMode[])(
        "%s layout has padding of 30",
        (mode) => {
          const config = getLayoutConfig(mode);
          expect(config.padding).toBe(30);
        }
      );

      it.each(["force", "circle", "grid", "hierarchical"] as LayoutMode[])(
        "%s layout has animation enabled",
        (mode) => {
          const config = getLayoutConfig(mode);
          expect(config.animate).toBe(true);
        }
      );
    });

    describe("default/unknown mode handling", () => {
      it("returns force layout config for unknown mode", () => {
        const config = getLayoutConfig("unknown" as LayoutMode);
        expect(config.name).toBe("cose");
      });

      it("returns same config as force for unknown mode", () => {
        const unknownConfig = getLayoutConfig("unknown" as LayoutMode);
        const forceConfig = getLayoutConfig("force");
        expect(unknownConfig.name).toBe(forceConfig.name);
        expect(unknownConfig.fit).toBe(forceConfig.fit);
        expect(unknownConfig.padding).toBe(forceConfig.padding);
      });
    });
  });

  describe("LAYOUT_MODE_LABELS", () => {
    it("contains labels for all layout modes", () => {
      expect(LAYOUT_MODE_LABELS.force).toBe("Force-Directed");
      expect(LAYOUT_MODE_LABELS.circle).toBe("Circle");
      expect(LAYOUT_MODE_LABELS.grid).toBe("Grid");
      expect(LAYOUT_MODE_LABELS.hierarchical).toBe("Hierarchical");
    });

    it("has exactly four entries", () => {
      expect(Object.keys(LAYOUT_MODE_LABELS)).toHaveLength(4);
    });

    it("has non-empty string labels for all modes", () => {
      for (const label of Object.values(LAYOUT_MODE_LABELS)) {
        expect(typeof label).toBe("string");
        expect(label.length).toBeGreaterThan(0);
      }
    });
  });

  describe("LAYOUT_MODE_DESCRIPTIONS", () => {
    it("contains descriptions for all layout modes", () => {
      expect(LAYOUT_MODE_DESCRIPTIONS.force).toBe("Natural clustering based on connections");
      expect(LAYOUT_MODE_DESCRIPTIONS.circle).toBe("Nodes arranged in a circle");
      expect(LAYOUT_MODE_DESCRIPTIONS.grid).toBe("Nodes arranged in a grid pattern");
      expect(LAYOUT_MODE_DESCRIPTIONS.hierarchical).toBe(
        "Top-down hierarchy based on relationships"
      );
    });

    it("has exactly four entries", () => {
      expect(Object.keys(LAYOUT_MODE_DESCRIPTIONS)).toHaveLength(4);
    });

    it("has non-empty string descriptions for all modes", () => {
      for (const description of Object.values(LAYOUT_MODE_DESCRIPTIONS)) {
        expect(typeof description).toBe("string");
        expect(description.length).toBeGreaterThan(0);
      }
    });
  });

  describe("AVAILABLE_LAYOUTS", () => {
    it("contains all expected layout modes", () => {
      expect(AVAILABLE_LAYOUTS).toContain("force");
      expect(AVAILABLE_LAYOUTS).toContain("circle");
      expect(AVAILABLE_LAYOUTS).toContain("grid");
      expect(AVAILABLE_LAYOUTS).toContain("hierarchical");
    });

    it("has exactly four layout modes", () => {
      expect(AVAILABLE_LAYOUTS).toHaveLength(4);
    });

    it("has force as the first layout (default)", () => {
      expect(AVAILABLE_LAYOUTS[0]).toBe("force");
    });

    it("is in the expected presentation order", () => {
      expect(AVAILABLE_LAYOUTS).toEqual(["force", "circle", "grid", "hierarchical"]);
    });

    it("matches the keys in LAYOUT_MODE_LABELS", () => {
      const labelKeys = Object.keys(LAYOUT_MODE_LABELS) as LayoutMode[];
      for (const mode of AVAILABLE_LAYOUTS) {
        expect(labelKeys).toContain(mode);
      }
    });

    it("matches the keys in LAYOUT_MODE_DESCRIPTIONS", () => {
      const descriptionKeys = Object.keys(LAYOUT_MODE_DESCRIPTIONS) as LayoutMode[];
      for (const mode of AVAILABLE_LAYOUTS) {
        expect(descriptionKeys).toContain(mode);
      }
    });
  });

  describe("integration", () => {
    it("all AVAILABLE_LAYOUTS have valid getLayoutConfig results", () => {
      for (const mode of AVAILABLE_LAYOUTS) {
        const config = getLayoutConfig(mode);
        expect(config).toBeDefined();
        expect(config.name).toBeDefined();
        expect(typeof config.name).toBe("string");
      }
    });

    it("all AVAILABLE_LAYOUTS have corresponding labels and descriptions", () => {
      for (const mode of AVAILABLE_LAYOUTS) {
        expect(LAYOUT_MODE_LABELS[mode]).toBeDefined();
        expect(LAYOUT_MODE_DESCRIPTIONS[mode]).toBeDefined();
      }
    });
  });
});
