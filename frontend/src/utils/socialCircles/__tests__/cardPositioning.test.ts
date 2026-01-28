import { describe, it, expect } from "vitest";
import { getBestCardPosition } from "../cardPositioning";

describe("getBestCardPosition", () => {
  const cardSize = { width: 280, height: 400 };
  const viewport = { width: 1200, height: 800 };

  it("places card bottom-right when node is top-left", () => {
    const nodePos = { x: 100, y: 100 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe("bottom-right");
    expect(result.position.x).toBeGreaterThan(nodePos.x);
    expect(result.position.y).toBeGreaterThan(nodePos.y);
  });

  it("places card bottom-left when node is top-right", () => {
    const nodePos = { x: 1100, y: 100 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe("bottom-left");
    expect(result.position.x).toBeLessThan(nodePos.x);
  });

  it("places card top-right when node is bottom-left", () => {
    const nodePos = { x: 100, y: 700 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe("top-right");
    expect(result.position.y).toBeLessThan(nodePos.y);
  });

  it("places card top-left when node is bottom-right", () => {
    const nodePos = { x: 1100, y: 700 };
    const result = getBestCardPosition(nodePos, cardSize, viewport);
    expect(result.quadrant).toBe("top-left");
  });

  it("respects margin parameter", () => {
    const nodePos = { x: 600, y: 400 };
    const margin = 30;
    const result = getBestCardPosition(nodePos, cardSize, viewport, margin);
    const distanceX = Math.abs(result.position.x - nodePos.x);
    const distanceY = Math.abs(result.position.y - nodePos.y);
    expect(distanceX).toBeGreaterThanOrEqual(margin);
    expect(distanceY).toBeGreaterThanOrEqual(margin);
  });

  it("clamps position to viewport bounds", () => {
    const nodePos = { x: 50, y: 50 }; // Very close to edge
    const result = getBestCardPosition(nodePos, cardSize, viewport, 20);
    expect(result.position.x).toBeGreaterThanOrEqual(20);
    expect(result.position.y).toBeGreaterThanOrEqual(20);
  });

  describe("tiny viewport edge cases", () => {
    it("clamps to margin when viewport is smaller than card width", () => {
      const tinyViewport = { width: 300, height: 800 }; // Card is 280px wide
      const nodePos = { x: 150, y: 400 };
      const margin = 20;
      const result = getBestCardPosition(nodePos, cardSize, tinyViewport, margin);
      // With 300px viewport, 280px card, 20px margin: max x = 300 - 280 - 20 = 0
      // So it should clamp to margin (20)
      expect(result.position.x).toBe(margin);
    });

    it("clamps to margin when viewport is smaller than card height", () => {
      const tinyViewport = { width: 1200, height: 420 }; // Card is 400px tall
      const nodePos = { x: 600, y: 200 };
      const margin = 20;
      const result = getBestCardPosition(nodePos, cardSize, tinyViewport, margin);
      // With 420px viewport, 400px card, 20px margin: max y = 420 - 400 - 20 = 0
      // So it should clamp to margin (20)
      expect(result.position.y).toBe(margin);
    });

    it("handles mobile viewport (320px wide)", () => {
      const mobileViewport = { width: 320, height: 568 };
      const nodePos = { x: 160, y: 284 }; // Center of mobile viewport
      const margin = 10;
      const result = getBestCardPosition(nodePos, cardSize, mobileViewport, margin);
      // Card won't fit horizontally (280 + 2*10 = 300 < 320 but barely)
      // Position should be clamped to valid range
      expect(result.position.x).toBeGreaterThanOrEqual(margin);
      expect(result.position.x).toBeLessThanOrEqual(mobileViewport.width - cardSize.width - margin);
    });

    it("handles viewport exactly equal to card size plus margins", () => {
      const exactViewport = { width: 320, height: 440 }; // 280 + 20*2, 400 + 20*2
      const nodePos = { x: 160, y: 220 };
      const margin = 20;
      const result = getBestCardPosition(nodePos, cardSize, exactViewport, margin);
      // Only one valid position: (20, 20)
      expect(result.position.x).toBe(margin);
      expect(result.position.y).toBe(margin);
    });
  });
});
