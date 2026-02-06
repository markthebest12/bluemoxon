/**
 * Shared condition grade color palette for entity profile components.
 */

export const CONDITION_COLORS: Record<string, string> = {
  FINE: "#2d6a4f",
  NEAR_FINE: "#40916c",
  VERY_GOOD: "#2b8a8a",
  GOOD: "#e09f3e",
  FAIR: "#e07c3e",
  POOR: "#9c503d",
  UNGRADED: "#8d8d8d",
};

/**
 * Get the color for a condition grade.
 * Returns grey for unknown/missing grades.
 */
export function getConditionColor(grade: string): string {
  return CONDITION_COLORS[grade.toUpperCase()] ?? CONDITION_COLORS.UNGRADED;
}

/**
 * Format a condition grade for display (e.g., "NEAR_FINE" -> "Near Fine").
 */
export function formatConditionGrade(grade: string): string {
  return grade
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Compute relative luminance from a hex color string.
 * Returns a value between 0 (black) and 1 (white).
 * Uses the W3C WCAG 2.0 formula for relative luminance.
 */
export function getLuminance(hex: string): number {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;

  const toLinear = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);

  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}
