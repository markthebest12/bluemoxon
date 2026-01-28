import type { NodeType } from "@/types/socialCircles";

export interface TierDisplay {
  label: string;
  stars: number;
  tooltip: string;
}

const TIER_MAP: Record<string, TierDisplay> = {
  TIER_1: { label: "Premier", stars: 3, tooltip: "Tier 1 - Premier Figure" },
  TIER_2: { label: "Established", stars: 2, tooltip: "Tier 2 - Established Figure" },
  TIER_3: { label: "Known", stars: 1, tooltip: "Tier 3 - Known Figure" },
};

export function formatTier(tier: string | null): TierDisplay {
  return TIER_MAP[tier ?? ""] || { label: "Unranked", stars: 0, tooltip: "Unranked" };
}

export function calculateStrength(sharedBooks: number): number {
  return Math.min(Math.max(sharedBooks, 0), 5);
}

export function renderStrength(strength: number, max: number = 5): string {
  const capped = Math.min(Math.max(strength, 0), max);
  const filled = "●".repeat(capped);
  const unfilled = "○".repeat(max - capped);
  return filled + unfilled;
}

const PLACEHOLDER_NAMES: Record<NodeType, string[]> = {
  author: [
    "generic-victorian-portrait-1.svg",
    "generic-victorian-portrait-2.svg",
    "generic-victorian-portrait-3.svg",
    "generic-victorian-portrait-4.svg",
  ],
  publisher: [
    "london-bookshop-exterior.svg",
    "victorian-printing-press.svg",
    "publisher-office-interior.svg",
    "victorian-publisher-logo.svg",
  ],
  binder: [
    "bookbinding-tools.svg",
    "leather-workshop.svg",
    "bindery-workbench.svg",
    "victorian-bindery-scene.svg",
  ],
};

export function getPlaceholderImage(type: NodeType, entityId: number): string {
  const names = PLACEHOLDER_NAMES[type];
  if (!names || names.length === 0) {
    return "/images/entity-placeholders/fallback.svg";
  }
  const index = entityId % names.length;
  return `/images/entity-placeholders/${type}s/${names[index]}`;
}
