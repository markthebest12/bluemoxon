/**
 * Composable for managing scroll lock on document body.
 *
 * Uses Set-based tracking with unique Symbol IDs to handle:
 * - Multiple independent modals
 * - Nested modals
 * - Proper cleanup on unmount
 * - No counter arithmetic bugs
 */

import { onUnmounted } from "vue";

// Module-level Set tracks all active locks by unique Symbol ID
const activeLocks = new Set<symbol>();

export function useScrollLock() {
  // Each composable instance gets a unique ID
  const lockId = Symbol();

  function lock() {
    activeLocks.add(lockId);
    document.body.style.overflow = "hidden";
  }

  function unlock() {
    activeLocks.delete(lockId);
    if (activeLocks.size === 0) {
      document.body.style.overflow = "";
    }
  }

  // Auto-cleanup on component unmount
  onUnmounted(() => {
    if (activeLocks.has(lockId)) {
      unlock();
    }
  });

  return { lock, unlock };
}
