import { describe, it, expect } from "vitest";
import { getToneStyle } from "../getToneStyle";
import type { Tone } from "@/types/entityProfile";

describe("getToneStyle", () => {
  const ALL_TONES: Tone[] = ["dramatic", "scandalous", "tragic", "intellectual", "triumphant"];

  it("returns a className and color for each tone", () => {
    for (const tone of ALL_TONES) {
      const style = getToneStyle(tone);
      expect(style.className).toBe(`tone--${tone}`);
      expect(style.color).toBeTruthy();
    }
  });

  it("returns distinct colors for each tone", () => {
    const colors = ALL_TONES.map((t) => getToneStyle(t).color);
    expect(new Set(colors).size).toBe(ALL_TONES.length);
  });

  it("returns fallback for unknown tone", () => {
    const style = getToneStyle("unknown" as Tone);
    expect(style.className).toBe("tone--unknown");
    expect(style.color).toBeTruthy();
  });
});
