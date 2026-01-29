// frontend/src/composables/socialcircles/useEscapeKey.ts
/**
 * useEscapeKey - Shared composable for ESC key handling.
 * Registers a global keydown listener that calls the callback when Escape is pressed.
 * Automatically cleans up on component unmount.
 */

import { onMounted, onUnmounted } from "vue";

export function useEscapeKey(onEscape: () => void): void {
  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === "Escape") {
      onEscape();
    }
  }

  onMounted(() => {
    window.addEventListener("keydown", handleKeydown);
  });

  onUnmounted(() => {
    window.removeEventListener("keydown", handleKeydown);
  });
}
