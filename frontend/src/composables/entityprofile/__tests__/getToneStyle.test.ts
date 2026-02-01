import { describe, it, expect } from "vitest";
import { getToneStyle } from "../getToneStyle";
import type { Tone } from "@/types/entityProfile";

describe("getToneStyle", () => {
  const ALL_TONES: Tone[] = ["dramatic", "scandalous", "tragic", "intellectual", "triumphant"];

  it("returns a className and color for each tone", () => {
    for (const tone of ALL_TONES) {
      const style = getToneStyle(tone);
      expect(style.className).toBe(`tone--${tone}`);
      expect(style.color).toBe(`var(--color-tone-${tone})`);
    }
  });

  it("returns fallback for unknown tone", () => {
    const style = getToneStyle("unknown" as Tone);
    expect(style.className).toBe("tone--unknown");
    expect(style.color).toBe("var(--color-tone-unknown, #b8860b)");
  });
});
