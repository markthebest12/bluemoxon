/**
 * Victorian color palettes for the social circles graph.
 * Provides runtime color utilities beyond the static constants.
 */

import type { NodeType, Era, ConnectionType } from '@/types/socialCircles';

/**
 * Victorian color values (CSS variable fallbacks for use in Cytoscape).
 */
export const VICTORIAN_COLORS = {
  // Hunter greens
  hunter100: '#e8f0ed',
  hunter200: '#c5d9d2',
  hunter300: '#8fb8a8',
  hunter400: '#5a9a83',
  hunter500: '#3a6b5c',
  hunter600: '#2f5a4b',
  hunter700: '#254a3d',
  hunter800: '#1a3a2f',
  hunter900: '#0f2318',

  // Golds
  goldLight: '#d4af37',
  gold: '#c9a227',
  goldDark: '#a67c00',
  goldMuted: '#b8956e',

  // Burgundy
  burgundyLight: '#8b3a42',
  burgundy: '#722f37',
  burgundyDark: '#5c262e',

  // Papers
  paperWhite: '#fdfcfa',
  paperCream: '#f8f5f0',
  paperAged: '#f0ebe3',
  paperAntique: '#e8e1d5',

  // Inks
  inkBlack: '#1a1a18',
  inkDark: '#2d2d2a',
  inkMuted: '#5c5c58',
} as const;

/**
 * Get node color based on type and attributes.
 */
export function getNodeColor(
  type: NodeType,
  era?: Era,
  tier?: string | null
): string {
  if (type === 'author') {
    switch (era) {
      case 'romantic':
        return VICTORIAN_COLORS.burgundyLight;
      case 'victorian':
        return VICTORIAN_COLORS.hunter700;
      case 'edwardian':
        return VICTORIAN_COLORS.hunter500;
      default:
        return VICTORIAN_COLORS.hunter600;
    }
  }

  if (type === 'publisher') {
    return tier === 'Tier 1'
      ? VICTORIAN_COLORS.goldLight
      : VICTORIAN_COLORS.goldMuted;
  }

  if (type === 'binder') {
    return tier === 'Tier 1'
      ? VICTORIAN_COLORS.burgundyDark
      : VICTORIAN_COLORS.burgundy;
  }

  return VICTORIAN_COLORS.hunter600;
}

/**
 * Get edge color based on connection type.
 */
export function getEdgeColor(type: ConnectionType): string {
  switch (type) {
    case 'publisher':
      return VICTORIAN_COLORS.gold;
    case 'shared_publisher':
      return VICTORIAN_COLORS.hunter500;
    case 'binder':
      return VICTORIAN_COLORS.burgundy;
    default:
      return VICTORIAN_COLORS.inkMuted;
  }
}

/**
 * Get highlight color for selected/hovered elements.
 */
export function getHighlightColor(type: 'selected' | 'hovered' | 'connected'): string {
  switch (type) {
    case 'selected':
      return VICTORIAN_COLORS.goldLight;
    case 'hovered':
      return VICTORIAN_COLORS.hunter400;
    case 'connected':
      return VICTORIAN_COLORS.hunter300;
    default:
      return VICTORIAN_COLORS.inkMuted;
  }
}

/**
 * Get dimmed color for non-highlighted elements.
 */
export function getDimmedColor(): string {
  return VICTORIAN_COLORS.paperAntique;
}

/**
 * Generate a color gradient between two colors.
 */
export function interpolateColor(
  color1: string,
  color2: string,
  factor: number
): string {
  // Parse hex colors
  const c1 = parseInt(color1.slice(1), 16);
  const c2 = parseInt(color2.slice(1), 16);

  const r1 = (c1 >> 16) & 255;
  const g1 = (c1 >> 8) & 255;
  const b1 = c1 & 255;

  const r2 = (c2 >> 16) & 255;
  const g2 = (c2 >> 8) & 255;
  const b2 = c2 & 255;

  const r = Math.round(r1 + factor * (r2 - r1));
  const g = Math.round(g1 + factor * (g2 - g1));
  const b = Math.round(b1 + factor * (b2 - b1));

  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}
