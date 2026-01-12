import { CONDITION_GRADE_OPTIONS } from "@/constants";

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  if (i === 0) return `${bytes} B`;
  if (i >= 3) return `${(bytes / Math.pow(k, i)).toFixed(2)} ${units[i]}`;
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${units[i]}`;
}

export function formatCost(bytes: number): string {
  const GB = 1024 * 1024 * 1024;
  const costPerGB = 0.023;
  const cost = (bytes / GB) * costPerGB;
  if (cost > 0 && cost < 0.01) {
    return `~<$0.01/month`;
  }
  return `~$${cost.toFixed(2)}/month`;
}

// Build lookup map from existing CONDITION_GRADE_OPTIONS (single source of truth)
const CONDITION_LABELS = Object.fromEntries(
  CONDITION_GRADE_OPTIONS.map((opt) => [opt.value, opt.label])
);

/**
 * Format condition grade enum value to human-readable label.
 * Uses CONDITION_GRADE_OPTIONS from constants as the single source of truth.
 *
 * @param grade - Condition grade enum value (e.g., "NEAR_FINE")
 * @returns Human-readable label (e.g., "Near Fine")
 */
export function formatConditionGrade(grade: string | null | undefined): string {
  if (!grade) {
    return "Ungraded";
  }

  // Return known label from constants
  if (CONDITION_LABELS[grade]) {
    return CONDITION_LABELS[grade];
  }

  // Pass through already-formatted values like "Ungraded"
  if (!grade.includes("_") && grade[0] === grade[0].toUpperCase()) {
    return grade;
  }

  // Title-case unknown SNAKE_CASE values
  return grade
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}
