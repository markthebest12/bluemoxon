import type { Router } from "vue-router";

/**
 * Normalizes era value by stripping date range parentheses.
 * Stats API returns era with dates like "Victorian (1837-1901)"
 * but the books API expects just "Victorian".
 *
 * @param era The era value, possibly with parentheses
 * @returns The era name without date range
 */
export function normalizeEra(era: string): string {
  if (era.includes("(")) {
    return era.split("(")[0].trim();
  }
  return era;
}

/**
 * Determines if user wants to open link in new tab based on modifier keys.
 * - Ctrl+Click (Win/Linux) = new tab
 * - Cmd+Click (Mac) = new tab
 */
export function wantsNewTab(event?: Event | null): boolean {
  const mouseEvent = event as MouseEvent | undefined;
  return Boolean(mouseEvent?.ctrlKey || mouseEvent?.metaKey);
}

/**
 * Navigate to filtered books list.
 * - Normal click: same tab (standard web behavior)
 * - Ctrl/Cmd+Click: new tab (user choice)
 *
 * @param router Vue Router instance
 * @param filter Query parameters for /books route
 * @param nativeEvent Original DOM event (for modifier key detection)
 */
export function navigateToBooks(
  router: Router,
  filter: Record<string, string | number>,
  nativeEvent?: Event | null
): void {
  // Normalize era filter to strip parenthetical date ranges
  // e.g., "Victorian (1837-1901)" -> "Victorian"
  const normalizedFilter = { ...filter };
  if (typeof normalizedFilter.era === "string") {
    normalizedFilter.era = normalizeEra(normalizedFilter.era);
  }

  if (wantsNewTab(nativeEvent)) {
    const route = router.resolve({ path: "/books", query: normalizedFilter });
    const newWindow = window.open(route.href, "_blank", "noopener");
    if (!newWindow) {
      // Popup blocked - fall back to same tab
      void router.push({ path: "/books", query: normalizedFilter });
    }
  } else {
    void router.push({ path: "/books", query: normalizedFilter });
  }
}
