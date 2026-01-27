// frontend/src/constants/socialCircles.ts

/**
 * Social Circles constants.
 * Visual encoding, animation timings, and configuration.
 */

import type { NodeType, ConnectionType, Era, LayoutMode } from "@/types/socialCircles";

// =============================================================================
// Victorian Color Palette
// =============================================================================

/** Node colors by type and variant */
export const NODE_COLORS: Record<string, string> = {
  // Authors by era
  "author:romantic": "var(--color-victorian-burgundy-light)", // #8b3a42
  "author:victorian": "var(--color-victorian-hunter-700)", // #254a3d
  "author:edwardian": "var(--color-victorian-hunter-500)", // #3a6b5c
  "author:default": "var(--color-victorian-hunter-600)", // #2f5a4b

  // Publishers by tier
  "publisher:tier1": "var(--color-victorian-gold-light)", // #d4af37
  "publisher:tier2": "var(--color-victorian-gold-muted)", // #b8956e
  "publisher:default": "var(--color-victorian-gold)", // #c9a227

  // Binders
  "binder:tier1": "var(--color-victorian-burgundy-dark)", // #5c262e
  "binder:default": "var(--color-victorian-burgundy)", // #722f37
};

/** Edge colors by connection type */
export const EDGE_COLORS: Record<ConnectionType, string> = {
  publisher: "var(--color-victorian-gold)", // #c9a227
  shared_publisher: "var(--color-victorian-hunter-500)", // #3a6b5c
  binder: "var(--color-victorian-burgundy)", // #722f37
};

// =============================================================================
// Node Visual Encoding
// =============================================================================

/** Node shapes by type */
export const NODE_SHAPES: Record<NodeType, string> = {
  author: "ellipse",
  publisher: "rectangle",
  binder: "diamond",
};

/** Node size calculation */
export const NODE_SIZE = {
  author: { base: 20, perBook: 5, max: 60 },
  publisher: { base: 25, perBook: 4, max: 65 },
  binder: { base: 20, perBook: 5, max: 55 },
} as const;

/** Calculate node size based on book count with diminishing returns */
export function calculateNodeSize(type: NodeType, bookCount: number): number {
  const config = NODE_SIZE[type];
  // Use square root for diminishing returns scaling
  // sqrt(1)=1, sqrt(4)=2, sqrt(9)=3, sqrt(25)=5
  const scaled = Math.sqrt(Math.max(bookCount, 1)) * config.perBook;
  return Math.min(config.base + scaled, config.max);
}

// =============================================================================
// Edge Visual Encoding
// =============================================================================

/** Edge width by strength (1-10 scale) */
export const EDGE_WIDTH = {
  min: 1,
  max: 6,
} as const;

/** Edge styles by connection type */
export const EDGE_STYLES: Record<ConnectionType, { lineStyle: string; opacity: number }> = {
  publisher: { lineStyle: "solid", opacity: 0.8 },
  shared_publisher: { lineStyle: "solid", opacity: 0.6 },
  binder: { lineStyle: "dashed", opacity: 0.5 },
};

/** Calculate edge width from strength */
export function calculateEdgeWidth(strength: number): number {
  const normalized = Math.min(Math.max(strength, 1), 10) / 10;
  return EDGE_WIDTH.min + normalized * (EDGE_WIDTH.max - EDGE_WIDTH.min);
}

// =============================================================================
// Animation Timings
// =============================================================================

export const ANIMATION = {
  nodeHover: 150,
  nodeSelect: 250,
  highlightSpread: 400,
  timelineFade: 400,
  panelSlide: 300,
  layoutReflow: 800,
  debounceFilter: 100,
  debounceUrl: 300,
} as const;

// =============================================================================
// Layout Configurations
// =============================================================================

export const LAYOUT_CONFIGS: Record<LayoutMode, object> = {
  force: {
    name: "cose",
    idealEdgeLength: 100,
    nodeOverlap: 20,
    refresh: 20,
    fit: true,
    padding: 30,
    randomize: false,
    componentSpacing: 100,
    nodeRepulsion: 400000,
    edgeElasticity: 100,
    nestingFactor: 5,
    gravity: 80,
    numIter: 1000,
    initialTemp: 200,
    coolingFactor: 0.95,
    minTemp: 1.0,
  },
  circle: {
    name: "circle",
    fit: true,
    padding: 30,
    avoidOverlap: true,
    spacingFactor: 1.5,
  },
  grid: {
    name: "grid",
    fit: true,
    padding: 30,
    avoidOverlap: true,
    condense: true,
    rows: undefined,
    cols: undefined,
  },
  hierarchical: {
    name: "dagre",
    rankDir: "TB",
    nodeSep: 50,
    rankSep: 100,
    fit: true,
    padding: 30,
  },
};

// =============================================================================
// Era Date Ranges
// =============================================================================

export const ERA_RANGES: Record<Era, [number, number]> = {
  pre_romantic: [1700, 1789],
  romantic: [1789, 1837],
  victorian: [1837, 1901],
  edwardian: [1901, 1910],
  post_1910: [1910, 1950],
  unknown: [1700, 1950],
};

/** Determine era from year */
export function getEraFromYear(year: number): Era {
  if (year < 1789) return "pre_romantic";
  if (year < 1837) return "romantic";
  if (year < 1901) return "victorian";
  if (year < 1910) return "edwardian";
  return "post_1910";
}

// =============================================================================
// API Configuration
// =============================================================================

export const API = {
  endpoint: "/social-circles", // Relative to api baseURL (/api/v1)
  cacheKey: "social-circles-data",
  cacheTtlMs: 5 * 60 * 1000, // 5 minutes
} as const;

// =============================================================================
// Keyboard Shortcuts
// =============================================================================

export const KEYBOARD_SHORTCUTS = {
  zoomIn: ["+", "="],
  zoomOut: ["-", "_"],
  fitToView: ["0"],
  togglePlay: [" "],
  escape: ["Escape"],
  search: ["/"],
  export: ["e"],
  share: ["s"],
  help: ["?"],
  nextNode: ["ArrowRight"],
  prevNode: ["ArrowLeft"],
  openDetails: ["Enter"],
} as const;
