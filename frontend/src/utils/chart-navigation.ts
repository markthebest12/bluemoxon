import type { Router } from "vue-router";

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
  if (wantsNewTab(nativeEvent)) {
    const route = router.resolve({ path: "/books", query: filter });
    const newWindow = window.open(route.href, "_blank", "noopener");
    if (!newWindow) {
      // Popup blocked - fall back to same tab
      void router.push({ path: "/books", query: filter });
    }
  } else {
    void router.push({ path: "/books", query: filter });
  }
}
