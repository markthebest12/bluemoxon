/**
 * Shared composable for model display labels.
 * Fetches labels from the public /config/model-labels endpoint once and caches at module level.
 * Falls back to built-in defaults on error.
 */

import { ref } from "vue";
import { api } from "@/services/api";

/** Built-in defaults — used when API is unavailable */
const DEFAULT_LABELS: Record<string, string> = {
  sonnet: "Sonnet 4.5",
  opus: "Opus 4.6",
  haiku: "Haiku 3.5",
};

// Module-level cache — shared across all component instances
const cachedLabels = ref<Record<string, string>>({ ...DEFAULT_LABELS });
const loaded = ref(false);
const error = ref<string | null>(null);
let fetchPromise: Promise<void> | null = null;

async function fetchLabels(): Promise<void> {
  try {
    const { data } = await api.get<{ labels: Record<string, string> }>("/config/model-labels");
    if (data.labels) {
      cachedLabels.value = data.labels;
    }
    loaded.value = true;
  } catch {
    // Fall back to defaults
    error.value = "Failed to load model labels";
    loaded.value = true;
  }
}

/**
 * Format a full Bedrock/Anthropic model ID into a human-readable display name.
 * Examples:
 *   "us.anthropic.claude-sonnet-4-5-20250929-v1:0" → "Claude Sonnet 4.5"
 *   "claude-3-5-sonnet-20241022" → "Claude 3.5 Sonnet"
 *   "opus" → "Claude Opus 4.6" (using registry labels)
 */
function createFormatModelId(labels: typeof cachedLabels) {
  return function formatModelId(modelId: string): string {
    if (!modelId) return "Unknown";

    // Direct key match from registry (e.g. "opus" → "Opus 4.6")
    const registryLabel = labels.value[modelId];
    if (registryLabel) {
      return `Claude ${registryLabel}`;
    }

    // Parse versioned Bedrock IDs: us.anthropic.claude-{family}-{version}-{date}-v{n}:{m}
    const bedrockMatch = modelId.match(
      /claude-(\w+)-(\d+)-(\d+)-\d{8}(?:-v\d+:\d+)?$/
    );
    if (bedrockMatch) {
      const family = bedrockMatch[1].charAt(0).toUpperCase() + bedrockMatch[1].slice(1);
      const version = `${bedrockMatch[2]}.${bedrockMatch[3]}`;
      return `Claude ${family} ${version}`;
    }

    // Parse legacy IDs: claude-{major}-{minor}-{family}-{date}
    const legacyMatch = modelId.match(/claude-(\d+)-(\d+)-(\w+)-\d{8}/);
    if (legacyMatch) {
      const version = `${legacyMatch[1]}.${legacyMatch[2]}`;
      const family = legacyMatch[3].charAt(0).toUpperCase() + legacyMatch[3].slice(1);
      return `Claude ${version} ${family}`;
    }

    // Extract family name from dotted/hyphenated ID as last resort
    const families = ["opus", "sonnet", "haiku"];
    for (const family of families) {
      if (modelId.toLowerCase().includes(family)) {
        return `Claude ${family.charAt(0).toUpperCase() + family.slice(1)}`;
      }
    }

    // Completely unknown — use last segment
    const segments = modelId.split(/[.\-/]/);
    return segments[segments.length - 1];
  };
}

/** Reset cache for testing */
export function _resetModelLabelsCache(): void {
  cachedLabels.value = { ...DEFAULT_LABELS };
  loaded.value = false;
  error.value = null;
  fetchPromise = null;
}

/**
 * Returns reactive model labels. First caller triggers a single API fetch;
 * subsequent callers reuse the cached result.
 */
export function useModelLabels() {
  if (!fetchPromise) {
    fetchPromise = fetchLabels();
  }
  return {
    labels: cachedLabels,
    modelLabels: cachedLabels, // backward-compat alias for AnalysisSection
    loaded,
    error,
    formatModelId: createFormatModelId(cachedLabels),
  };
}
