import { describe, it, expect } from "vitest";
import {
  VICTORIAN_COLORS,
  getNodeColor,
  getEdgeColor,
  getHighlightColor,
  getDimmedColor,
  interpolateColor,
} from "../colorPalettes";

// Helper to validate hex color format
const isValidHexColor = (color: string): boolean => /^#[0-9a-fA-F]{6}$/.test(color);

describe("VICTORIAN_COLORS", () => {
  it("exports hunter green palette", () => {
    expect(VICTORIAN_COLORS.hunter100).toBeDefined();
    expect(VICTORIAN_COLORS.hunter500).toBeDefined();
    expect(VICTORIAN_COLORS.hunter900).toBeDefined();
  });

  it("exports gold palette", () => {
    expect(VICTORIAN_COLORS.goldLight).toBeDefined();
    expect(VICTORIAN_COLORS.gold).toBeDefined();
    expect(VICTORIAN_COLORS.goldDark).toBeDefined();
    expect(VICTORIAN_COLORS.goldMuted).toBeDefined();
  });

  it("exports burgundy palette", () => {
    expect(VICTORIAN_COLORS.burgundyLight).toBeDefined();
    expect(VICTORIAN_COLORS.burgundy).toBeDefined();
    expect(VICTORIAN_COLORS.burgundyDark).toBeDefined();
  });

  it("exports paper palette", () => {
    expect(VICTORIAN_COLORS.paperWhite).toBeDefined();
    expect(VICTORIAN_COLORS.paperCream).toBeDefined();
    expect(VICTORIAN_COLORS.paperAged).toBeDefined();
    expect(VICTORIAN_COLORS.paperAntique).toBeDefined();
  });

  it("exports ink palette", () => {
    expect(VICTORIAN_COLORS.inkBlack).toBeDefined();
    expect(VICTORIAN_COLORS.inkDark).toBeDefined();
    expect(VICTORIAN_COLORS.inkMuted).toBeDefined();
  });

  it("all colors are valid hex format", () => {
    for (const [key, color] of Object.entries(VICTORIAN_COLORS)) {
      expect(isValidHexColor(color), `${key} should be valid hex`).toBe(true);
    }
  });
});

describe("getNodeColor", () => {
  describe("author nodes", () => {
    it("returns burgundy light for romantic era", () => {
      const color = getNodeColor("author", "romantic");
      expect(color).toBe(VICTORIAN_COLORS.burgundyLight);
    });

    it("returns hunter700 for victorian era", () => {
      const color = getNodeColor("author", "victorian");
      expect(color).toBe(VICTORIAN_COLORS.hunter700);
    });

    it("returns hunter500 for edwardian era", () => {
      const color = getNodeColor("author", "edwardian");
      expect(color).toBe(VICTORIAN_COLORS.hunter500);
    });

    it("returns hunter600 for pre_romantic era (default)", () => {
      const color = getNodeColor("author", "pre_romantic");
      expect(color).toBe(VICTORIAN_COLORS.hunter600);
    });

    it("returns hunter600 for post_1910 era (default)", () => {
      const color = getNodeColor("author", "post_1910");
      expect(color).toBe(VICTORIAN_COLORS.hunter600);
    });

    it("returns hunter600 for unknown era", () => {
      const color = getNodeColor("author", "unknown");
      expect(color).toBe(VICTORIAN_COLORS.hunter600);
    });

    it("returns hunter600 when era is undefined", () => {
      const color = getNodeColor("author");
      expect(color).toBe(VICTORIAN_COLORS.hunter600);
    });

    it("returns valid hex color", () => {
      const color = getNodeColor("author", "victorian");
      expect(isValidHexColor(color)).toBe(true);
    });
  });

  describe("publisher nodes", () => {
    it("returns gold light for TIER_1", () => {
      const color = getNodeColor("publisher", undefined, "TIER_1");
      expect(color).toBe(VICTORIAN_COLORS.goldLight);
    });

    it("returns gold muted for TIER_2", () => {
      const color = getNodeColor("publisher", undefined, "TIER_2");
      expect(color).toBe(VICTORIAN_COLORS.goldMuted);
    });

    it("returns gold muted for TIER_3", () => {
      const color = getNodeColor("publisher", undefined, "TIER_3");
      expect(color).toBe(VICTORIAN_COLORS.goldMuted);
    });

    it("returns gold muted for null tier", () => {
      const color = getNodeColor("publisher", undefined, null);
      expect(color).toBe(VICTORIAN_COLORS.goldMuted);
    });

    it("returns gold muted when tier is undefined", () => {
      const color = getNodeColor("publisher");
      expect(color).toBe(VICTORIAN_COLORS.goldMuted);
    });
  });

  describe("binder nodes", () => {
    it("returns burgundy dark for TIER_1", () => {
      const color = getNodeColor("binder", undefined, "TIER_1");
      expect(color).toBe(VICTORIAN_COLORS.burgundyDark);
    });

    it("returns burgundy for TIER_2", () => {
      const color = getNodeColor("binder", undefined, "TIER_2");
      expect(color).toBe(VICTORIAN_COLORS.burgundy);
    });

    it("returns burgundy for null tier", () => {
      const color = getNodeColor("binder", undefined, null);
      expect(color).toBe(VICTORIAN_COLORS.burgundy);
    });
  });

  describe("unknown node type", () => {
    it("returns default hunter600 for unknown type", () => {
      const color = getNodeColor("unknown" as never);
      expect(color).toBe(VICTORIAN_COLORS.hunter600);
    });
  });
});

describe("getEdgeColor", () => {
  it("returns gold for publisher connection", () => {
    const color = getEdgeColor("publisher");
    expect(color).toBe(VICTORIAN_COLORS.gold);
  });

  it("returns hunter500 for shared_publisher connection", () => {
    const color = getEdgeColor("shared_publisher");
    expect(color).toBe(VICTORIAN_COLORS.hunter500);
  });

  it("returns burgundy for binder connection", () => {
    const color = getEdgeColor("binder");
    expect(color).toBe(VICTORIAN_COLORS.burgundy);
  });

  it("returns ink muted for unknown connection type", () => {
    const color = getEdgeColor("unknown" as never);
    expect(color).toBe(VICTORIAN_COLORS.inkMuted);
  });

  it("returns valid hex colors for all types", () => {
    expect(isValidHexColor(getEdgeColor("publisher"))).toBe(true);
    expect(isValidHexColor(getEdgeColor("shared_publisher"))).toBe(true);
    expect(isValidHexColor(getEdgeColor("binder"))).toBe(true);
  });
});

describe("getHighlightColor", () => {
  it("returns gold light for selected", () => {
    const color = getHighlightColor("selected");
    expect(color).toBe(VICTORIAN_COLORS.goldLight);
  });

  it("returns hunter400 for hovered", () => {
    const color = getHighlightColor("hovered");
    expect(color).toBe(VICTORIAN_COLORS.hunter400);
  });

  it("returns hunter300 for connected", () => {
    const color = getHighlightColor("connected");
    expect(color).toBe(VICTORIAN_COLORS.hunter300);
  });

  it("returns ink muted for unknown type", () => {
    const color = getHighlightColor("unknown" as never);
    expect(color).toBe(VICTORIAN_COLORS.inkMuted);
  });

  it("returns valid hex colors for all types", () => {
    expect(isValidHexColor(getHighlightColor("selected"))).toBe(true);
    expect(isValidHexColor(getHighlightColor("hovered"))).toBe(true);
    expect(isValidHexColor(getHighlightColor("connected"))).toBe(true);
  });
});

describe("getDimmedColor", () => {
  it("returns paper antique", () => {
    const color = getDimmedColor();
    expect(color).toBe(VICTORIAN_COLORS.paperAntique);
  });

  it("returns valid hex color", () => {
    expect(isValidHexColor(getDimmedColor())).toBe(true);
  });
});

describe("interpolateColor", () => {
  it("returns first color when factor is 0", () => {
    const result = interpolateColor("#000000", "#ffffff", 0);
    expect(result.toLowerCase()).toBe("#000000");
  });

  it("returns second color when factor is 1", () => {
    const result = interpolateColor("#000000", "#ffffff", 1);
    expect(result.toLowerCase()).toBe("#ffffff");
  });

  it("returns midpoint color when factor is 0.5", () => {
    const result = interpolateColor("#000000", "#ffffff", 0.5);
    // Mid-gray between black and white
    expect(result.toLowerCase()).toBe("#808080");
  });

  it("interpolates red channel correctly", () => {
    const result = interpolateColor("#ff0000", "#000000", 0.5);
    expect(result.toLowerCase()).toBe("#800000");
  });

  it("interpolates green channel correctly", () => {
    const result = interpolateColor("#00ff00", "#000000", 0.5);
    expect(result.toLowerCase()).toBe("#008000");
  });

  it("interpolates blue channel correctly", () => {
    const result = interpolateColor("#0000ff", "#000000", 0.5);
    expect(result.toLowerCase()).toBe("#000080");
  });

  it("handles mixed color interpolation", () => {
    // Red to blue at 0.5 should give purple-ish
    const result = interpolateColor("#ff0000", "#0000ff", 0.5);
    expect(result.toLowerCase()).toBe("#800080");
  });

  it("returns valid hex color", () => {
    const result = interpolateColor(VICTORIAN_COLORS.hunter500, VICTORIAN_COLORS.goldLight, 0.3);
    expect(isValidHexColor(result)).toBe(true);
  });

  it("works with Victorian palette colors", () => {
    const result = interpolateColor(VICTORIAN_COLORS.burgundy, VICTORIAN_COLORS.goldLight, 0.5);
    expect(isValidHexColor(result)).toBe(true);
    // Result should be somewhere between burgundy and gold
    expect(result).not.toBe(VICTORIAN_COLORS.burgundy);
    expect(result).not.toBe(VICTORIAN_COLORS.goldLight);
  });

  it("handles quarter interpolation", () => {
    const result = interpolateColor("#000000", "#ffffff", 0.25);
    expect(result.toLowerCase()).toBe("#404040");
  });

  it("handles three-quarter interpolation", () => {
    const result = interpolateColor("#000000", "#ffffff", 0.75);
    expect(result.toLowerCase()).toBe("#bfbfbf");
  });
});
