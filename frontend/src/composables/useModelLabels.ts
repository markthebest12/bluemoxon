/**
 * Shared composable for model display labels.
 * Fetches labels from /admin/model-config once and caches at module level.
 * Non-admin users get a silent 403 → falls back to built-in defaults.
 */

import { ref } from "vue";
import { api } from "@/services/api";

/** Built-in defaults — used when API is unavailable or user is non-admin */
const DEFAULT_LABELS: Record<string, string> = {
  sonnet: "Sonnet 4.5",
  opus: "Opus 4.6",
  haiku: "Haiku 3.5",
};

// Module-level cache — shared across all component instances
const cachedLabels = ref<Record<string, string>>({ ...DEFAULT_LABELS });
let fetchPromise: Promise<void> | null = null;

async function fetchLabels(): Promise<void> {
  try {
    const { data } = await api.get<{ model_labels: Record<string, string> }>("/admin/model-config");
    if (data.model_labels) {
      cachedLabels.value = data.model_labels;
    }
  } catch {
    // Silently fall back to defaults — non-admin users can't access this endpoint
  }
}

/**
 * Returns reactive model labels. First caller triggers a single API fetch;
 * subsequent callers reuse the cached result.
 */
export function useModelLabels() {
  if (!fetchPromise) {
    fetchPromise = fetchLabels();
  }
  return { modelLabels: cachedLabels };
}
