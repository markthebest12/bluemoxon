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

/**
 * Format condition grade enum value to human-readable label.
 * Converts NEAR_FINE to "Near Fine", VERY_GOOD to "Very Good", etc.
 *
 * @param grade - Condition grade enum value (e.g., "NEAR_FINE")
 * @returns Human-readable label (e.g., "Near Fine")
 */
export function formatConditionGrade(grade: string | null | undefined): string {
  if (!grade) {
    return "Ungraded";
  }

  // Known condition grades with their display labels
  const labels: Record<string, string> = {
    FINE: "Fine",
    NEAR_FINE: "Near Fine",
    VERY_GOOD: "Very Good",
    GOOD: "Good",
    FAIR: "Fair",
    POOR: "Poor",
  };

  // Return known label or title-case the value
  if (labels[grade]) {
    return labels[grade];
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
