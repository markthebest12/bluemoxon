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
