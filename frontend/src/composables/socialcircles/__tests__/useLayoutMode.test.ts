// frontend/src/composables/socialcircles/__tests__/useLayoutMode.test.ts
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck - Test mocks don't need full type compliance
/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi } from "vitest";
import { ref } from "vue";
import { useLayoutMode } from "../useLayoutMode";

function createMockCy() {
  const runFn = vi.fn();
  return {
    layout: vi.fn(() => ({
      run: runFn,
    })),
    _runFn: runFn,
  };
}

describe("useLayoutMode", () => {
  it("initializes with force mode", () => {
    const cy = ref(null);
    const { currentMode } = useLayoutMode(cy);
    expect(currentMode.value).toBe("force");
  });

  it("initializes with isAnimating as false", () => {
    const cy = ref(null);
    const { isAnimating } = useLayoutMode(cy);
    expect(isAnimating.value).toBe(false);
  });

  it("setMode changes current mode", () => {
    const mockCy = createMockCy();
    const cy = ref(mockCy as any);
    const { currentMode, setMode } = useLayoutMode(cy);

    setMode("circle");

    expect(currentMode.value).toBe("circle");
  });

  it("setMode calls cy.layout with correct config for circle", () => {
    const mockCy = createMockCy();
    const cy = ref(mockCy as any);
    const { setMode } = useLayoutMode(cy);

    setMode("circle");

    expect(mockCy.layout).toHaveBeenCalledWith(expect.objectContaining({ name: "circle" }));
    expect(mockCy._runFn).toHaveBeenCalled();
  });

  it("setMode calls cy.layout with correct config for grid", () => {
    const mockCy = createMockCy();
    const cy = ref(mockCy as any);
    const { setMode } = useLayoutMode(cy);

    setMode("grid");

    expect(mockCy.layout).toHaveBeenCalledWith(expect.objectContaining({ name: "grid" }));
  });

  it("setMode calls cy.layout with correct config for hierarchical (dagre)", () => {
    const mockCy = createMockCy();
    const cy = ref(mockCy as any);
    const { setMode } = useLayoutMode(cy);

    setMode("hierarchical");

    expect(mockCy.layout).toHaveBeenCalledWith(expect.objectContaining({ name: "dagre" }));
  });

  it("setMode calls cy.layout with correct config for force (cose)", () => {
    const mockCy = createMockCy();
    const cy = ref(mockCy as any);
    const { currentMode, setMode } = useLayoutMode(cy);

    // First change to something else
    setMode("circle");
    // Simulate animation completing
    const layoutCall = mockCy.layout.mock.calls[0][0];
    layoutCall.stop?.();

    // Now set to force
    setMode("force");

    expect(currentMode.value).toBe("force");
    expect(mockCy.layout).toHaveBeenLastCalledWith(expect.objectContaining({ name: "cose" }));
  });

  it("cycleMode cycles through all modes", () => {
    const mockCy = createMockCy();
    const cy = ref(mockCy as any);
    const { currentMode, cycleMode } = useLayoutMode(cy);

    expect(currentMode.value).toBe("force");

    // Cycle to circle
    cycleMode();
    // Simulate animation completing
    let layoutCall = mockCy.layout.mock.calls[0][0];
    layoutCall.stop?.();
    expect(currentMode.value).toBe("circle");

    // Cycle to grid
    cycleMode();
    layoutCall = mockCy.layout.mock.calls[1][0];
    layoutCall.stop?.();
    expect(currentMode.value).toBe("grid");

    // Cycle to hierarchical
    cycleMode();
    layoutCall = mockCy.layout.mock.calls[2][0];
    layoutCall.stop?.();
    expect(currentMode.value).toBe("hierarchical");

    // Cycle back to force (wraps around)
    cycleMode();
    expect(currentMode.value).toBe("force");
  });

  it("setMode does nothing when cy is null", () => {
    const cy = ref(null);
    const { currentMode, setMode } = useLayoutMode(cy);

    setMode("circle");

    // Mode doesn't change since cy is null
    expect(currentMode.value).toBe("force");
  });

  it("setMode does nothing when animating", () => {
    const mockCy = createMockCy();
    const cy = ref(mockCy as any);
    const { isAnimating, setMode, currentMode } = useLayoutMode(cy);

    // First setMode triggers animation
    setMode("circle");
    expect(currentMode.value).toBe("circle");
    expect(isAnimating.value).toBe(true);

    // Try to change while animating - should be prevented
    setMode("grid");
    expect(currentMode.value).toBe("circle"); // Still circle, not grid

    // Layout should only have been called once (for circle)
    expect(mockCy.layout).toHaveBeenCalledTimes(1);
  });

  it("isAnimating becomes false after layout stop callback", () => {
    const mockCy = createMockCy();
    const cy = ref(mockCy as any);
    const { isAnimating, setMode } = useLayoutMode(cy);

    expect(isAnimating.value).toBe(false);

    setMode("circle");
    expect(isAnimating.value).toBe(true);

    // Get the stop callback from the layout config
    const layoutCall = mockCy.layout.mock.calls[0][0];
    expect(layoutCall.stop).toBeDefined();

    // Simulate animation completing
    layoutCall.stop();
    expect(isAnimating.value).toBe(false);
  });

  it("exports LAYOUT_MODES constant", () => {
    const cy = ref(null);
    const { LAYOUT_MODES } = useLayoutMode(cy);
    expect(LAYOUT_MODES).toContain("force");
    expect(LAYOUT_MODES).toContain("circle");
    expect(LAYOUT_MODES).toContain("grid");
    expect(LAYOUT_MODES).toContain("hierarchical");
  });

  it("LAYOUT_MODES has expected length", () => {
    const cy = ref(null);
    const { LAYOUT_MODES } = useLayoutMode(cy);
    expect(LAYOUT_MODES).toHaveLength(4);
  });

  it("resetMode sets mode back to force", () => {
    const mockCy = createMockCy();
    const cy = ref(mockCy as any);
    const { currentMode, setMode, resetMode } = useLayoutMode(cy);

    // Change to circle
    setMode("circle");
    // Simulate animation completing
    const layoutCall = mockCy.layout.mock.calls[0][0];
    layoutCall.stop?.();
    expect(currentMode.value).toBe("circle");

    // Reset to force
    resetMode();
    expect(currentMode.value).toBe("force");
  });

  it("setMode ignores invalid layout modes", () => {
    const mockCy = createMockCy();
    const cy = ref(mockCy as any);
    const { currentMode, setMode } = useLayoutMode(cy);

    // Try to set an invalid mode
    setMode("invalid-mode" as any);

    // Mode should remain unchanged
    expect(currentMode.value).toBe("force");
    expect(mockCy.layout).not.toHaveBeenCalled();
  });

  it("currentMode is readonly", () => {
    const cy = ref(null);
    const { currentMode } = useLayoutMode(cy);

    // Attempting to directly modify should not work (TypeScript would catch this)
    // We can verify it's a readonly ref by checking __v_isReadonly
    expect((currentMode as any).__v_isReadonly).toBe(true);
  });

  it("isAnimating is readonly", () => {
    const cy = ref(null);
    const { isAnimating } = useLayoutMode(cy);

    // Verify it's a readonly ref
    expect((isAnimating as any).__v_isReadonly).toBe(true);
  });
});
