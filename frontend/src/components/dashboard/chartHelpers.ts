import type { AcquisitionDay } from "@/types/dashboard";

/**
 * Format tooltip content for acquisition chart data points.
 * Returns an array of strings to display in the tooltip.
 */
export function formatAcquisitionTooltip(day: AcquisitionDay | undefined): string[] {
  if (!day) return [];
  const itemWord = day.count === 1 ? "item" : "items";
  return [
    `Total: $${day.cumulative_value.toLocaleString()}`,
    `Added ${day.label}: ${day.count} ${itemWord} ($${day.value.toLocaleString()})`,
  ];
}
