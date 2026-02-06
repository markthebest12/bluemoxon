import { ref } from "vue";
import { api } from "@/services/api";

/**
 * Module-level cache so every consumer shares a single fetch.
 * Once loaded, the labels never change for the lifetime of the page.
 */
const labels = ref<Record<string, string>>({});
const loaded = ref(false);
const loading = ref(false);
const error = ref<string | null>(null);

async function fetchLabels(): Promise<void> {
  if (loaded.value || loading.value) return;
  loading.value = true;
  error.value = null;
  try {
    const res = await api.get("/config/model-labels");
    labels.value = res.data.labels;
    loaded.value = true;
  } catch (_e) {
    error.value = "Failed to load model labels";
    // Provide sensible fallbacks so the UI is never blank
    labels.value = {
      sonnet: "Sonnet",
      opus: "Opus",
      haiku: "Haiku",
    };
  } finally {
    loading.value = false;
  }
}

/**
 * Format a raw Bedrock model ID string into a human-readable label.
 *
 * Tries the registry-backed labels first (key lookup), then falls back to
 * regex parsing of the full model ID for legacy/unknown IDs stored in the DB.
 */
function formatModelId(modelId: string): string {
  // Try exact key match against registry labels (e.g. "opus" → "Opus 4.6")
  if (labels.value[modelId]) {
    return `Claude ${labels.value[modelId]}`;
  }

  // Parse versioned format: "-opus-4-6-20251101" or "-sonnet-4-5-20250929"
  const versionPattern = /-(opus|sonnet|haiku)-(\d+)(?:-(\d+))?-\d{8}/i;
  const match = modelId.match(versionPattern);
  if (match) {
    const [, model, major, minor] = match;
    const modelName = model.charAt(0).toUpperCase() + model.slice(1).toLowerCase();
    const version = minor ? `${major}.${minor}` : major;
    return `Claude ${modelName} ${version}`;
  }

  // Legacy format: "claude-3-5-sonnet-date"
  const legacyPattern = /claude-(\d+)-(\d+)-(opus|sonnet|haiku)/i;
  const legacyMatch = modelId.match(legacyPattern);
  if (legacyMatch) {
    const [, major, minor, model] = legacyMatch;
    const modelName = model.charAt(0).toUpperCase() + model.slice(1).toLowerCase();
    return `Claude ${major}.${minor} ${modelName}`;
  }

  // Simple fallback
  if (modelId.includes("opus")) return "Claude Opus";
  if (modelId.includes("sonnet")) return "Claude Sonnet";
  if (modelId.includes("haiku")) return "Claude Haiku";

  return modelId.split(".").pop() || modelId;
}

/**
 * Composable returning reactive model labels from the public API.
 * Triggers a fetch on first use; subsequent calls share the cached result.
 */
export function useModelLabels() {
  // Kick off fetch if not already done
  void fetchLabels();
  return { labels, loaded, loading, error, formatModelId };
}

/** Reset cache — useful for tests. */
export function _resetModelLabelsCache(): void {
  labels.value = {};
  loaded.value = false;
  loading.value = false;
  error.value = null;
}
