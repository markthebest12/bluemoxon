/**
 * useMiniMap - Manages mini-map state and interactions for the network graph.
 * Provides viewport tracking, panning, and visibility toggle.
 */

import { ref, watch, onUnmounted, type Ref, type ShallowRef } from "vue";
import type { Core as CytoscapeCore } from "cytoscape";

interface Bounds {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function useMiniMap(cy: Ref<CytoscapeCore | null> | ShallowRef<CytoscapeCore | null>) {
  const isVisible = ref(true);
  const viewportBounds = ref<Bounds | null>(null);
  const graphBounds = ref<Bounds | null>(null);

  /**
   * Update viewport and graph bounds based on current cytoscape state.
   * Called on viewport changes (pan, zoom) and when cy instance changes.
   */
  function updateViewport(): void {
    if (!cy.value) return;

    const extent = cy.value.extent();
    graphBounds.value = {
      x: extent.x1,
      y: extent.y1,
      w: extent.w,
      h: extent.h,
    };

    const pan = cy.value.pan();
    const zoom = cy.value.zoom();
    const container = cy.value.container();
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    viewportBounds.value = {
      x: -pan.x / zoom,
      y: -pan.y / zoom,
      w: width / zoom,
      h: height / zoom,
    };
  }

  /**
   * Pan the graph to center on the given coordinates.
   * Used when clicking on the mini-map to navigate.
   */
  function panTo(x: number, y: number): void {
    if (!cy.value) return;
    cy.value.pan({ x: -x * cy.value.zoom(), y: -y * cy.value.zoom() });
  }

  /**
   * Toggle mini-map visibility.
   */
  function toggle(): void {
    isVisible.value = !isVisible.value;
  }

  /**
   * Show the mini-map.
   */
  function show(): void {
    isVisible.value = true;
  }

  /**
   * Hide the mini-map.
   */
  function hide(): void {
    isVisible.value = false;
  }

  // Set up event listeners when cy is available
  watch(
    cy,
    (newCy, oldCy) => {
      if (oldCy) {
        oldCy.off("viewport", updateViewport);
      }
      if (newCy) {
        newCy.on("viewport", updateViewport);
        updateViewport();
      }
    },
    { immediate: true }
  );

  onUnmounted(() => {
    if (cy.value) {
      cy.value.off("viewport", updateViewport);
    }
  });

  return {
    isVisible,
    viewportBounds,
    graphBounds,
    updateViewport,
    panTo,
    toggle,
    show,
    hide,
  };
}
