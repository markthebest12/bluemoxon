import type { Tone } from "@/types/entityProfile";

export interface ToneStyle {
  className: string;
  color: string;
}

const TONE_COLORS: Record<string, string> = {
  dramatic: "#c0392b",
  scandalous: "#e74c3c",
  tragic: "#7f8c8d",
  intellectual: "#2c3e50",
  triumphant: "#d4a017",
};

const FALLBACK_COLOR = "#b8860b";

export function useToneStyle(tone: Tone): ToneStyle {
  return {
    className: `tone--${tone}`,
    color: TONE_COLORS[tone] ?? FALLBACK_COLOR,
  };
}
