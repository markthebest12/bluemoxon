/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck - Test mocks don't need full type compliance
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ref, nextTick } from "vue";
import { useMiniMap } from "../useMiniMap";

// Type for event handlers in cytoscape
type EventHandler = () => void;

// Mock cytoscape instance
function createMockCy() {
  const listeners: Record<string, EventHandler[]> = {};
  return {
    extent: vi.fn(() => ({ x1: 0, y1: 0, w: 1000, h: 800 })),
    pan: vi.fn(() => ({ x: 100, y: 50 })),
    zoom: vi.fn(() => 1),
    container: vi.fn(() => ({ clientWidth: 800, clientHeight: 600 })),
    on: vi.fn((event: string, handler: EventHandler) => {
      if (!listeners[event]) listeners[event] = [];
      listeners[event].push(handler);
    }),
    off: vi.fn((event: string, handler: EventHandler) => {
      if (listeners[event]) {
        listeners[event] = listeners[event].filter((h) => h !== handler);
      }
    }),
    emit: (event: string) => {
      listeners[event]?.forEach((h) => h());
    },
  };
}

describe("useMiniMap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("initializes with isVisible true", () => {
    const cy = ref(null);
    const { isVisible } = useMiniMap(cy);
    expect(isVisible.value).toBe(true);
  });

  it("toggle switches visibility", () => {
    const cy = ref(null);
    const { isVisible, toggle } = useMiniMap(cy);
    toggle();
    expect(isVisible.value).toBe(false);
    toggle();
    expect(isVisible.value).toBe(true);
  });

  it("show sets isVisible to true", () => {
    const cy = ref(null);
    const { isVisible, hide, show } = useMiniMap(cy);
    hide();
    expect(isVisible.value).toBe(false);
    show();
    expect(isVisible.value).toBe(true);
  });

  it("hide sets isVisible to false", () => {
    const cy = ref(null);
    const { isVisible, hide } = useMiniMap(cy);
    expect(isVisible.value).toBe(true);
    hide();
    expect(isVisible.value).toBe(false);
  });

  it("updates viewport bounds when cy is set", async () => {
    const mockCy = createMockCy();
    const cy = ref(null);
    const { viewportBounds, graphBounds } = useMiniMap(cy);

    // Initially null
    expect(graphBounds.value).toBeNull();
    expect(viewportBounds.value).toBeNull();

    // Set cy instance - triggers watch with immediate: true behavior
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    cy.value = mockCy as any;
    await nextTick();

    expect(graphBounds.value).not.toBeNull();
    expect(viewportBounds.value).not.toBeNull();
  });

  it("calculates graphBounds correctly from extent", async () => {
    const mockCy = createMockCy();
    mockCy.extent.mockReturnValue({ x1: 10, y1: 20, w: 500, h: 400 });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cy = ref(mockCy as any);
    const { graphBounds } = useMiniMap(cy);
    await nextTick();

    expect(graphBounds.value).toEqual({
      x: 10,
      y: 20,
      w: 500,
      h: 400,
    });
  });

  it("calculates viewportBounds correctly from pan, zoom, and container", async () => {
    const mockCy = createMockCy();
    mockCy.pan.mockReturnValue({ x: -200, y: -100 });
    mockCy.zoom.mockReturnValue(2);
    mockCy.container.mockReturnValue({ clientWidth: 800, clientHeight: 600 });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cy = ref(mockCy as any);
    const { viewportBounds } = useMiniMap(cy);
    await nextTick();

    // x = -pan.x / zoom = 200 / 2 = 100
    // y = -pan.y / zoom = 100 / 2 = 50
    // w = width / zoom = 800 / 2 = 400
    // h = height / zoom = 600 / 2 = 300
    expect(viewportBounds.value).toEqual({
      x: 100,
      y: 50,
      w: 400,
      h: 300,
    });
  });

  it("registers viewport event listener", async () => {
    const mockCy = createMockCy();
    const cy = ref(null);
    useMiniMap(cy);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    cy.value = mockCy as any;
    await nextTick();

    expect(mockCy.on).toHaveBeenCalledWith("viewport", expect.any(Function));
  });

  it("unregisters viewport event listener when cy changes", async () => {
    const mockCy1 = createMockCy();
    const mockCy2 = createMockCy();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cy = ref(mockCy1 as any);
    useMiniMap(cy);
    await nextTick();

    // Change to new cy instance
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    cy.value = mockCy2 as any;
    await nextTick();

    expect(mockCy1.off).toHaveBeenCalledWith("viewport", expect.any(Function));
    expect(mockCy2.on).toHaveBeenCalledWith("viewport", expect.any(Function));
  });

  it("panTo calls cy.pan with correct coordinates", async () => {
    const mockCy = createMockCy();
    mockCy.zoom.mockReturnValue(2);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cy = ref(mockCy as any);
    const { panTo } = useMiniMap(cy);
    await nextTick();

    // Reset mock to ignore initialization calls
    mockCy.pan.mockClear();

    panTo(100, 50);

    // Expected: { x: -x * zoom, y: -y * zoom } = { x: -200, y: -100 }
    expect(mockCy.pan).toHaveBeenCalledWith({ x: -200, y: -100 });
  });

  it("handles null cy gracefully", () => {
    const cy = ref(null);
    const { updateViewport, panTo, viewportBounds, graphBounds } = useMiniMap(cy);

    // Should not throw
    updateViewport();
    panTo(100, 50);

    expect(viewportBounds.value).toBeNull();
    expect(graphBounds.value).toBeNull();
  });

  it("handles null container gracefully", async () => {
    const mockCy = createMockCy();
    mockCy.container.mockReturnValue(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cy = ref(mockCy as any);
    const { viewportBounds, graphBounds } = useMiniMap(cy);
    await nextTick();

    // graphBounds should still be set from extent
    expect(graphBounds.value).not.toBeNull();
    // viewportBounds should remain null since container is null
    expect(viewportBounds.value).toBeNull();
  });

  it("updates bounds when viewport event is emitted", async () => {
    const mockCy = createMockCy();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cy = ref(mockCy as any);
    const { viewportBounds } = useMiniMap(cy);
    await nextTick();

    // Clear calls from initialization
    mockCy.extent.mockClear();
    mockCy.pan.mockClear();

    // Simulate viewport change
    mockCy.emit("viewport");

    expect(mockCy.extent).toHaveBeenCalled();
    expect(mockCy.pan).toHaveBeenCalled();
    expect(viewportBounds.value).not.toBeNull();
  });

  it("updates when zoom changes", async () => {
    const mockCy = createMockCy();
    mockCy.pan.mockReturnValue({ x: -100, y: -100 });
    mockCy.zoom.mockReturnValue(1);
    mockCy.container.mockReturnValue({ clientWidth: 800, clientHeight: 600 });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cy = ref(mockCy as any);
    const { viewportBounds } = useMiniMap(cy);
    await nextTick();

    const initialBounds = { ...viewportBounds.value };

    // Simulate zoom change
    mockCy.zoom.mockReturnValue(2);
    mockCy.emit("viewport");

    // Width and height should be halved due to 2x zoom
    expect(viewportBounds.value?.w).toBe(initialBounds.w! / 2);
    expect(viewportBounds.value?.h).toBe(initialBounds.h! / 2);
  });
});
