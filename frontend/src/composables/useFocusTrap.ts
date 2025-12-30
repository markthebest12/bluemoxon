import { onUnmounted, type Ref } from "vue";
import { createFocusTrap, type FocusTrap, type Options } from "focus-trap";

/**
 * Creates a focus trap for modal accessibility.
 * Uses focus-trap directly instead of @vueuse/integrations to avoid
 * bundle bloat from multiple VueUse versions.
 */
export function useFocusTrap(target: Ref<HTMLElement | null>, options: Partial<Options> = {}) {
  let trap: FocusTrap | null = null;

  function activate() {
    if (!target.value) {
      if (import.meta.env.DEV) {
        console.warn("useFocusTrap: Cannot activate - target element is null");
      }
      return;
    }

    // Clean up existing trap
    if (trap) {
      try {
        trap.deactivate();
      } catch {
        // Ignore deactivation errors during cleanup
      }
    }

    try {
      trap = createFocusTrap(target.value, {
        escapeDeactivates: false,
        allowOutsideClick: true,
        fallbackFocus: () => target.value || document.body,
        ...options,
      });
      trap.activate();
    } catch (e) {
      // In development, make errors visible
      if (import.meta.env.DEV) {
        console.error("Focus trap activation failed:", e);
      } else if (import.meta.env.MODE !== "test") {
        console.warn("Focus trap activation failed:", e);
      }
      // Don't re-throw - graceful degradation is better than breaking the modal
    }
  }

  function deactivate() {
    if (!trap) return;

    try {
      trap.deactivate();
      trap = null;
    } catch (e) {
      if (import.meta.env.DEV) {
        console.error("Focus trap deactivation failed:", e);
      }
      trap = null;
    }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    deactivate();
  });

  return { activate, deactivate };
}
