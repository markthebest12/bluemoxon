import type { ApiNode } from "@/types/socialCircles";

/** Maximum number of results returned by node filter functions. */
export const MAX_FILTER_RESULTS = 20;

/**
 * Filter nodes by a search query string, returning at most MAX_FILTER_RESULTS.
 * When the query is empty (or nullish at runtime), returns the first
 * MAX_FILTER_RESULTS nodes.
 *
 * Performance: O(n) per call. Currently acceptable for dataset sizes in the
 * hundreds; callers that bind this to reactive inputs should consider debounce
 * if dataset sizes grow significantly.
 */
export function filterNodesByQuery(nodes: ApiNode[], query: string): ApiNode[] {
  if (!query) return nodes.slice(0, MAX_FILTER_RESULTS);

  const normalised = query.trim().toLowerCase();
  if (!normalised) return nodes.slice(0, MAX_FILTER_RESULTS);

  const results: ApiNode[] = [];
  for (const n of nodes) {
    if (n.name?.toLowerCase().includes(normalised)) {
      results.push(n);
      if (results.length >= MAX_FILTER_RESULTS) break;
    }
  }
  return results;
}
