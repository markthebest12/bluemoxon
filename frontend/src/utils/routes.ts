/**
 * Centralized route param helpers.
 *
 * Vue Router 4 requires string params. These helpers ensure consistent
 * String() coercion so numeric IDs from the API are never passed raw.
 */
import type { RouteLocationRaw } from "vue-router";

export function bookDetailRoute(id: number | string): RouteLocationRaw {
  return { name: "book-detail", params: { id: String(id) } };
}

export function entityProfileRoute(type: string, id: number | string): RouteLocationRaw {
  return { name: "entity-profile", params: { type, id: String(id) } };
}
