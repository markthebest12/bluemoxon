import { describe, it, expect } from "vitest";
import { useToneStyle } from "../useToneStyle";
import type { Tone } from "@/types/entityProfile";

describe("useToneStyle", () => {
  const ALL_TONES: Tone[] = ["dramatic", "scandalous", "tragic", "intellectual", "triumphant"];

  it("returns a className and color for each tone", () => {
    for (const tone of ALL_TONES) {
      const style = useToneStyle(tone);
      expect(style.className).toBe(`tone--${tone}`);
      expect(style.color).toBeTruthy();
    }
  });

  it("returns distinct colors for each tone", () => {
    const colors = ALL_TONES.map((t) => useToneStyle(t).color);
    expect(new Set(colors).size).toBe(ALL_TONES.length);
  });

  it("returns fallback for unknown tone", () => {
    const style = useToneStyle("unknown" as Tone);
    expect(style.className).toBe("tone--unknown");
    expect(style.color).toBeTruthy();
  });
});
