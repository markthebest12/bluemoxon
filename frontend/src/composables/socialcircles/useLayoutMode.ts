/**
 * useLayoutMode - Composable for managing graph layout mode.
 * Handles layout transitions with animation state tracking.
 */

import { ref, readonly, type Ref, type ShallowRef } from "vue";
import type { Core as CytoscapeCore } from "cytoscape";
import type { LayoutMode } from "@/types/socialCircles";
import { getLayoutConfig, AVAILABLE_LAYOUTS } from "@/utils/socialCircles/layoutConfigs";

export function useLayoutMode(cy: Ref<CytoscapeCore | null> | ShallowRef<CytoscapeCore | null>) {
  const currentMode = ref<LayoutMode>("force");
  const isAnimating = ref(false);

  /**
   * Set the layout mode and run the layout animation.
   * No-op if cytoscape is not initialized or animation is in progress.
   */
  function setMode(mode: LayoutMode): void {
    if (!cy.value || isAnimating.value) return;
    if (!AVAILABLE_LAYOUTS.includes(mode)) return;

    currentMode.value = mode;
    isAnimating.value = true;

    const baseConfig = getLayoutConfig(mode);
    const config = {
      ...baseConfig,
      stop: () => {
        isAnimating.value = false;
      },
    };

    cy.value.layout(config).run();
  }

  /**
   * Cycle through available layout modes in order.
   */
  function cycleMode(): void {
    const currentIndex = AVAILABLE_LAYOUTS.indexOf(currentMode.value);
    const nextIndex = (currentIndex + 1) % AVAILABLE_LAYOUTS.length;
    setMode(AVAILABLE_LAYOUTS[nextIndex]);
  }

  /**
   * Reset to default layout mode (force-directed).
   */
  function resetMode(): void {
    setMode("force");
  }

  return {
    currentMode: readonly(currentMode),
    isAnimating: readonly(isAnimating),
    setMode,
    cycleMode,
    resetMode,
    LAYOUT_MODES: AVAILABLE_LAYOUTS,
  };
}
