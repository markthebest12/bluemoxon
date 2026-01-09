/**
 * Era values matching backend app/enums.py Era enum.
 * These are the canonical era strings used across the application.
 */
export const Era = {
  PRE_ROMANTIC: "Pre-Romantic",
  ROMANTIC: "Romantic",
  VICTORIAN: "Victorian",
  EDWARDIAN: "Edwardian",
  POST_1910: "Post-1910",
  UNKNOWN: "Unknown",
} as const;

export type EraValue = (typeof Era)[keyof typeof Era];

/**
 * Compute the historical era from publication year(s).
 * Uses yearStart if provided, otherwise falls back to yearEnd.
 *
 * Era boundaries are based on British literary/historical periods:
 * - Pre-Romantic: Before 1800
 * - Romantic: 1800-1836 (Wordsworth, Coleridge, Shelley, Keats, Byron)
 * - Victorian: 1837-1901 (Queen Victoria's reign)
 * - Edwardian: 1902-1910 (Edward VII's reign)
 * - Post-1910: After 1910
 * - Unknown: No year data available
 *
 * This matches backend app/utils/date_parser.py compute_era().
 *
 * @param yearStart - Start year of publication
 * @param yearEnd - End year of publication (for ranges like "1835-1840")
 * @returns Era string matching backend Era enum values
 */
export function computeEra(yearStart: number | null, yearEnd: number | null): EraValue {
  // Use yearStart preferentially, fall back to yearEnd (matches backend)
  const year = yearStart ?? yearEnd;

  if (year === null) {
    return Era.UNKNOWN;
  }

  if (year < 1800) {
    return Era.PRE_ROMANTIC;
  } else if (year <= 1836) {
    return Era.ROMANTIC;
  } else if (year <= 1901) {
    return Era.VICTORIAN;
  } else if (year <= 1910) {
    return Era.EDWARDIAN;
  } else {
    return Era.POST_1910;
  }
}
