// frontend/src/composables/socialcircles/useClickOutside.ts
/**
 * useClickOutside - Detects clicks outside a referenced element.
 * Used to close panels when user clicks outside them (#1407).
 */

import { onMounted, onUnmounted, type Ref } from "vue";

export function useClickOutside(elementRef: Ref<HTMLElement | null>, callback: () => void): void {
  function handleClick(event: MouseEvent) {
    const el = elementRef.value;
    if (!el) return;

    // Check if click was outside the element
    if (!el.contains(event.target as Node)) {
      callback();
    }
  }

  onMounted(() => {
    // Use capture phase to catch clicks before they're stopped by other handlers
    document.addEventListener("click", handleClick, true);
  });

  onUnmounted(() => {
    document.removeEventListener("click", handleClick, true);
  });
}
