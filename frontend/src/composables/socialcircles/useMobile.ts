// frontend/src/composables/socialcircles/useMobile.ts
/**
 * useMobile - Composable for mobile-specific state and behavior.
 * Detects viewport size, touch capability, and manages filter panel state.
 * Uses VueUse's useMediaQuery for reliable media query detection with SSR support.
 */

import { ref, computed, onMounted, type ComputedRef, type Ref } from "vue";
import { useMediaQuery } from "@vueuse/core";

export interface UseMobileReturn {
  /** True if viewport width is ≤768px */
  isMobile: ComputedRef<boolean>;
  /** True if viewport width is 769-1024px */
  isTablet: ComputedRef<boolean>;
  /** True if device has touch capability */
  isTouch: Ref<boolean>;
  /** True if filter panel is currently open */
  isFiltersOpen: Ref<boolean>;
  /** Open the filter panel */
  openFilters: () => void;
  /** Close the filter panel */
  closeFilters: () => void;
  /** Toggle the filter panel open/closed state */
  toggleFilters: () => void;
}

export function useMobile(): UseMobileReturn {
  // Use VueUse's useMediaQuery for SSR-safe and efficient media query detection.
  // These return false during SSR and update reactively on the client.
  const isMobileQuery = useMediaQuery("(max-width: 768px)");
  const isTabletQuery = useMediaQuery("(min-width: 769px) and (max-width: 1024px)");
  // Detect coarse pointer (touchscreens) - more reliable than touch events alone
  // since laptops with touchscreens have fine pointers (trackpad/mouse) as primary
  const isCoarsePointer = useMediaQuery("(pointer: coarse)");

  // Computed wrappers for consistent interface
  const isMobile = computed(() => isMobileQuery.value);
  const isTablet = computed(() => isTabletQuery.value);

  // Touch detection - initialized to false for SSR safety
  const isTouch = ref(false);

  // Filter panel state
  const isFiltersOpen = ref(false);

  onMounted(() => {
    // Detect touch capability using standard feature detection AND coarse pointer.
    // ontouchstart/maxTouchPoints alone give false positives on laptops with touchscreens.
    // Combined with (pointer: coarse), we only trigger touch mode for actual touch devices.
    const hasTouchEvents = "ontouchstart" in window || navigator.maxTouchPoints > 0;
    isTouch.value = hasTouchEvents && isCoarsePointer.value;
  });

  // No cleanup needed - VueUse handles media query listeners internally

  function openFilters(): void {
    isFiltersOpen.value = true;
  }

  function closeFilters(): void {
    isFiltersOpen.value = false;
  }

  function toggleFilters(): void {
    isFiltersOpen.value = !isFiltersOpen.value;
  }

  return {
    isMobile,
    isTablet,
    isTouch,
    isFiltersOpen,
    openFilters,
    closeFilters,
    toggleFilters,
  };
}
