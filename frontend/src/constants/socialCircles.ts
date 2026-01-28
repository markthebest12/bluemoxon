// frontend/src/constants/socialCircles.ts

/**
 * Social Circles constants.
 * Visual encoding, animation timings, and configuration.
 */

import type { NodeType, ConnectionType, Era, LayoutMode } from "@/types/socialCircles";

// =============================================================================
// Connection Types
// =============================================================================

/** All connection types for filter validation */
export const ALL_CONNECTION_TYPES: readonly ConnectionType[] = [
  "publisher",
  "shared_publisher",
  "binder",
] as const;

// =============================================================================
// Victorian Color Palette
// =============================================================================

/** Node colors by type and variant (hex values - Cytoscape doesn't support CSS variables) */
export const NODE_COLORS: Record<string, string> = {
  // Authors by era
  "author:pre_romantic": "#6b3a4a", // muted burgundy for pre-romantic
  "author:romantic": "#8b3a42", // burgundy-light
  "author:victorian": "#254a3d", // hunter-700
  "author:edwardian": "#3a6b5c", // hunter-500
  "author:post_1910": "#4a7b6c", // lighter hunter for post-1910
  "author:unknown": "#2f5a4b", // hunter-600 default
  "author:default": "#2f5a4b", // hunter-600

  // Publishers by tier
  "publisher:tier1": "#d4af37", // gold-light
  "publisher:tier2": "#b8956e", // gold-muted
  "publisher:default": "#c9a227", // gold

  // Binders
  "binder:tier1": "#5c262e", // burgundy-dark
  "binder:default": "#722f37", // burgundy
};

/** Edge colors by connection type (hex values - Cytoscape doesn't support CSS variables) */
export const EDGE_COLORS: Record<ConnectionType, string> = {
  publisher: "#c9a227", // gold
  shared_publisher: "#3a6b5c", // hunter-500
  binder: "#722f37", // burgundy
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
    idealEdgeLength: 100, // Target length for edges in pixels
    nodeOverlap: 20, // Padding to prevent node overlap
    refresh: 20, // Frames between layout updates during animation
    fit: true, // Fit graph to viewport when layout completes
    padding: 30, // Padding around graph when fitting
    randomize: false, // Use existing positions as starting point
    componentSpacing: 100, // Space between disconnected components
    nodeRepulsion: 400000, // Higher = nodes push apart more strongly
    edgeElasticity: 100, // Higher = edges act like stiffer springs
    nestingFactor: 5, // Multiplier for nested node repulsion
    gravity: 80, // Higher = nodes pulled toward center more
    numIter: 1000, // Number of iterations for layout algorithm
    initialTemp: 200, // Starting temperature for simulated annealing
    coolingFactor: 0.95, // Rate temperature decreases per iteration
    minTemp: 1.0, // Temperature at which layout stops
  },
  circle: {
    name: "circle",
    fit: true, // Fit graph to viewport when layout completes
    padding: 30, // Padding around graph when fitting
    avoidOverlap: true, // Prevent nodes from overlapping
    spacingFactor: 1.5, // Multiplier for spacing between nodes
  },
  grid: {
    name: "grid",
    fit: true, // Fit graph to viewport when layout completes
    padding: 30, // Padding around graph when fitting
    avoidOverlap: true, // Prevent nodes from overlapping
    condense: true, // Pack grid tightly without gaps
    rows: undefined, // Auto-calculate row count
    cols: undefined, // Auto-calculate column count
  },
  hierarchical: {
    name: "dagre",
    rankDir: "TB", // Direction: TB (top-bottom), BT, LR, RL
    nodeSep: 50, // Horizontal spacing between nodes
    rankSep: 100, // Vertical spacing between ranks/levels
    fit: true, // Fit graph to viewport when layout completes
    padding: 30, // Padding around graph when fitting
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

// =============================================================================
// Detail Panel Colors (from design doc)
// =============================================================================

export const PANEL_COLORS = {
  // Backgrounds
  cardBg: "#F5F1E8",
  sidebarBg: "#FAF8F3",
  skeletonBg: "#E8E4DB",

  // Text
  textPrimary: "#2C2416",
  textSecondary: "#5C5446",
  textMuted: "#8B8579",

  // Interactive
  accentGold: "#B8860B",
  hover: "#8B4513",
  selected: "#2C5F77",
  link: "#6B4423",

  // Borders
  border: "#D4CFC4",
  borderStrong: "#A69F92",

  // Entity accents
  author: "#7B4B94",
  publisher: "#2C5F77",
  binder: "#8B4513",
} as const;

// =============================================================================
// Panel Animation Config
// =============================================================================

export const PANEL_ANIMATION = {
  duration: 200,
  easing: "cubic-bezier(0.4, 0.0, 0.2, 1)",
  easingOut: "cubic-bezier(0.4, 0.0, 1, 1)",
} as const;

// =============================================================================
// Panel Dimensions
// =============================================================================

export const PANEL_DIMENSIONS = {
  card: {
    width: 280,
    maxHeight: 400,
    margin: 20,
  },
  sidebar: {
    widthPercent: 35,
    minWidth: 320,
    maxWidth: 500,
  },
} as const;

// =============================================================================
// Responsive Breakpoints
// =============================================================================

export const BREAKPOINTS = {
  mobile: 768,
  tablet: 1024,
} as const;

// =============================================================================
// Touch Targets (Accessibility)
// =============================================================================

export const TOUCH_TARGETS = {
  minSize: 44,
  minSizeAndroid: 48,
} as const;
