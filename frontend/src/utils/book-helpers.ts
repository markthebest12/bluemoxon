/**
 * Compute the historical era from publication year(s).
 * Uses yearEnd if provided, otherwise yearStart.
 *
 * @param yearStart - Start year of publication
 * @param yearEnd - End year of publication (for ranges like "1835-1840")
 * @returns Era string or null if no year provided
 */
export function computeEra(yearStart: number | null, yearEnd: number | null): string | null {
  if (yearStart === null) {
    return null;
  }

  // Use yearEnd if available, otherwise yearStart
  const year = yearEnd ?? yearStart;

  if (year < 1837) {
    return "Pre-Victorian";
  } else if (year <= 1860) {
    return "Early Victorian";
  } else if (year <= 1880) {
    return "Mid-Victorian";
  } else if (year <= 1901) {
    return "Late Victorian";
  } else if (year <= 1910) {
    return "Edwardian";
  } else {
    return "Later";
  }
}
