import type { Tone } from "@/types/entityProfile";

export interface ToneStyle {
  className: string;
  color: string;
}

// Keep in sync with Tone type (types/entityProfile.ts) and --color-tone-* in main.css
const KNOWN_TONES = new Set(["dramatic", "scandalous", "tragic", "intellectual", "triumphant"]);

const FALLBACK_COLOR = "#b8860b";

export function getToneStyle(tone: Tone): ToneStyle {
  const isKnown = KNOWN_TONES.has(tone);
  return {
    className: `tone--${tone}`,
    color: isKnown ? `var(--color-tone-${tone})` : `var(--color-tone-${tone}, ${FALLBACK_COLOR})`,
  };
}
