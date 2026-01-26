/**
 * useNetworkKeyboard - Keyboard navigation and shortcuts.
 */

import { onMounted, onUnmounted } from "vue";
import { KEYBOARD_SHORTCUTS } from "@/constants/socialCircles";

export interface KeyboardHandlers {
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onFit?: () => void;
  onTogglePlay?: () => void;
  onEscape?: () => void;
  onSearch?: () => void;
  onExport?: () => void;
  onShare?: () => void;
  onHelp?: () => void;
  onNextNode?: () => void;
  onPrevNode?: () => void;
  onOpenDetails?: () => void;
}

export function useNetworkKeyboard(handlers: KeyboardHandlers) {
  function handleKeyDown(event: KeyboardEvent) {
    // Ignore if user is typing in an input
    const target = event.target as HTMLElement;
    if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
      return;
    }

    const key = event.key;
    const shortcuts = KEYBOARD_SHORTCUTS;

    // Helper to check if key matches a shortcut (handles readonly tuple types)
    const matches = (keys: readonly string[], k: string): boolean =>
      (keys as readonly string[]).includes(k);

    // Zoom
    if (matches(shortcuts.zoomIn, key) && handlers.onZoomIn) {
      event.preventDefault();
      handlers.onZoomIn();
      return;
    }
    if (matches(shortcuts.zoomOut, key) && handlers.onZoomOut) {
      event.preventDefault();
      handlers.onZoomOut();
      return;
    }
    if (matches(shortcuts.fitToView, key) && handlers.onFit) {
      event.preventDefault();
      handlers.onFit();
      return;
    }

    // Playback
    if (matches(shortcuts.togglePlay, key) && handlers.onTogglePlay) {
      event.preventDefault();
      handlers.onTogglePlay();
      return;
    }

    // Navigation
    if (matches(shortcuts.escape, key) && handlers.onEscape) {
      event.preventDefault();
      handlers.onEscape();
      return;
    }
    if (matches(shortcuts.nextNode, key) && handlers.onNextNode) {
      event.preventDefault();
      handlers.onNextNode();
      return;
    }
    if (matches(shortcuts.prevNode, key) && handlers.onPrevNode) {
      event.preventDefault();
      handlers.onPrevNode();
      return;
    }
    if (matches(shortcuts.openDetails, key) && handlers.onOpenDetails) {
      event.preventDefault();
      handlers.onOpenDetails();
      return;
    }

    // Actions
    if (matches(shortcuts.search, key) && handlers.onSearch) {
      event.preventDefault();
      handlers.onSearch();
      return;
    }
    if (matches(shortcuts.export, key) && handlers.onExport) {
      event.preventDefault();
      handlers.onExport();
      return;
    }
    if (matches(shortcuts.share, key) && handlers.onShare) {
      event.preventDefault();
      handlers.onShare();
      return;
    }
    if (matches(shortcuts.help, key) && handlers.onHelp) {
      event.preventDefault();
      handlers.onHelp();
      return;
    }
  }

  onMounted(() => {
    window.addEventListener("keydown", handleKeyDown);
  });

  onUnmounted(() => {
    window.removeEventListener("keydown", handleKeyDown);
  });

  return {
    // Expose shortcuts for help modal
    shortcuts: KEYBOARD_SHORTCUTS,
  };
}
