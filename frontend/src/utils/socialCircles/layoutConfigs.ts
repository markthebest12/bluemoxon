/**
 * Cytoscape layout configurations.
 */

import type { LayoutOptions } from "cytoscape";
import type { LayoutMode } from "@/types/socialCircles";

/**
 * Get layout configuration for a given mode.
 */
export function getLayoutConfig(mode: LayoutMode): LayoutOptions {
  switch (mode) {
    case "force":
      return {
        name: "cose",
        idealEdgeLength: 100,
        nodeOverlap: 20,
        refresh: 20,
        fit: true,
        padding: 80,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: () => 400000,
        edgeElasticity: () => 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
        animate: true,
        animationDuration: 800,
        animationEasing: "ease-out-quad",
      };

    case "circle":
      return {
        name: "circle",
        fit: true,
        padding: 80,
        avoidOverlap: true,
        spacingFactor: 1.5,
        animate: true,
        animationDuration: 500,
      };

    case "grid":
      return {
        name: "grid",
        fit: true,
        padding: 80,
        avoidOverlap: true,
        condense: true,
        animate: true,
        animationDuration: 500,
      };

    case "hierarchical":
      return {
        name: "dagre",
        rankDir: "TB",
        nodeSep: 50,
        rankSep: 100,
        fit: true,
        padding: 80,
        animate: true,
        animationDuration: 500,
      } as LayoutOptions;

    default:
      return getLayoutConfig("force");
  }
}

/**
 * Layout mode display names.
 */
export const LAYOUT_MODE_LABELS: Record<LayoutMode, string> = {
  force: "Force-Directed",
  circle: "Circle",
  grid: "Grid",
  hierarchical: "Hierarchical",
};

/**
 * Layout mode descriptions.
 */
export const LAYOUT_MODE_DESCRIPTIONS: Record<LayoutMode, string> = {
  force: "Natural clustering based on connections",
  circle: "Nodes arranged in a circle",
  grid: "Nodes arranged in a grid pattern",
  hierarchical: "Top-down hierarchy based on relationships",
};

/**
 * Available layout modes in order of presentation.
 */
export const AVAILABLE_LAYOUTS: LayoutMode[] = ["force", "circle", "grid", "hierarchical"];
