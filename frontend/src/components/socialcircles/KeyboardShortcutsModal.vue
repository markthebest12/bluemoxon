<!-- frontend/src/components/socialcircles/KeyboardShortcutsModal.vue -->
<script setup lang="ts">
/**
 * KeyboardShortcutsModal - Modal displaying available keyboard shortcuts.
 * Teleported to body for proper z-index handling.
 * Closes on Esc key or backdrop click.
 */

import { ref, watch, onMounted, onUnmounted } from "vue";
import { useFocusTrap } from "@vueuse/integrations/useFocusTrap";

interface Props {
  isOpen: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  close: [];
}>();

const SHORTCUTS = [
  { key: "?", description: "Show this help" },
  { key: "Esc", description: "Close panel / Clear selection" },
  { key: "F", description: "Toggle filter panel" },
  { key: "L", description: "Cycle layout modes" },
  { key: "R", description: "Reset view" },
  { key: "+/-", description: "Zoom in/out" },
  { key: "Space", description: "Play/pause timeline" },
  { key: "←/→", description: "Step timeline" },
] as const;

const modalRef = ref<HTMLElement | null>(null);
const { activate, deactivate } = useFocusTrap(modalRef, { immediate: false });

function handleBackdropClick(event: MouseEvent) {
  if (event.target === event.currentTarget) {
    emit("close");
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && props.isOpen) {
    event.preventDefault();
    emit("close");
  }
}

watch(
  () => props.isOpen,
  (isOpen) => {
    if (isOpen) {
      activate();
    } else {
      deactivate();
    }
  }
);

onMounted(() => {
  window.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeydown);
  deactivate();
});
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="isOpen"
        ref="modalRef"
        class="keyboard-shortcuts-modal__backdrop"
        role="dialog"
        aria-modal="true"
        aria-labelledby="keyboard-shortcuts-title"
        @click="handleBackdropClick"
      >
        <div class="keyboard-shortcuts-modal">
          <!-- Ornate border frame -->
          <div class="keyboard-shortcuts-modal__frame">
            <!-- Header -->
            <header class="keyboard-shortcuts-modal__header">
              <h2 id="keyboard-shortcuts-title" class="keyboard-shortcuts-modal__title">
                Keyboard Shortcuts
              </h2>
              <button
                class="keyboard-shortcuts-modal__close"
                aria-label="Close shortcuts modal"
                @click="emit('close')"
              >
                <span aria-hidden="true">&#x2715;</span>
              </button>
            </header>

            <!-- Shortcuts list -->
            <div class="keyboard-shortcuts-modal__content">
              <dl class="keyboard-shortcuts-modal__list">
                <div
                  v-for="shortcut in SHORTCUTS"
                  :key="shortcut.key"
                  class="keyboard-shortcuts-modal__item"
                >
                  <dt class="keyboard-shortcuts-modal__key">
                    <kbd>{{ shortcut.key }}</kbd>
                  </dt>
                  <dd class="keyboard-shortcuts-modal__description">
                    {{ shortcut.description }}
                  </dd>
                </div>
              </dl>
            </div>

            <!-- Footer -->
            <footer class="keyboard-shortcuts-modal__footer">
              <span class="keyboard-shortcuts-modal__hint">Press ? anytime to view shortcuts</span>
            </footer>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.keyboard-shortcuts-modal__backdrop {
  position: fixed;
  inset: 0;
  z-index: 9000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(26, 26, 24, 0.6);
  backdrop-filter: blur(2px);
}

.keyboard-shortcuts-modal {
  position: relative;
  width: 100%;
  max-width: 420px;
  margin: 1rem;
}

.keyboard-shortcuts-modal__frame {
  background: var(--color-victorian-paper-white, #fdfcfa);
  border: 2px solid var(--color-victorian-gold-dark, #a67c00);
  border-radius: 4px;
  box-shadow:
    0 0 0 1px var(--color-victorian-paper-antique, #e8e1d5),
    0 0 0 4px var(--color-victorian-paper-cream, #f8f5f0),
    0 0 0 5px var(--color-victorian-gold-muted, #b8956e),
    0 8px 32px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}

.keyboard-shortcuts-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  background: linear-gradient(
    180deg,
    var(--color-victorian-paper-cream, #f8f5f0) 0%,
    var(--color-victorian-paper-white, #fdfcfa) 100%
  );
  border-bottom: 1px solid var(--color-victorian-paper-antique, #e8e1d5);
}

.keyboard-shortcuts-modal__title {
  margin: 0;
  font-family: "Cormorant Garamond", Georgia, serif;
  font-size: 1.375rem;
  font-weight: 600;
  color: var(--color-victorian-ink-dark, #2d2d2a);
  letter-spacing: 0.02em;
}

.keyboard-shortcuts-modal__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  background: none;
  border: 1px solid transparent;
  border-radius: 4px;
  color: var(--color-victorian-ink-muted, #5c5c58);
  font-size: 1rem;
  cursor: pointer;
  transition:
    background 150ms ease-out,
    border-color 150ms ease-out,
    color 150ms ease-out;
}

.keyboard-shortcuts-modal__close:hover {
  background: var(--color-victorian-paper-aged, #f0ebe3);
  border-color: var(--color-victorian-paper-antique, #e8e1d5);
  color: var(--color-victorian-ink-dark, #2d2d2a);
}

.keyboard-shortcuts-modal__close:focus-visible {
  outline: 2px solid var(--color-victorian-hunter-500, #3a6b5c);
  outline-offset: 2px;
}

.keyboard-shortcuts-modal__content {
  padding: 1.25rem;
}

.keyboard-shortcuts-modal__list {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.75rem 1.5rem;
  margin: 0;
}

.keyboard-shortcuts-modal__item {
  display: contents;
}

.keyboard-shortcuts-modal__key {
  text-align: right;
}

.keyboard-shortcuts-modal__key kbd {
  display: inline-block;
  min-width: 2rem;
  padding: 0.25rem 0.5rem;
  background: linear-gradient(
    180deg,
    var(--color-victorian-paper-white, #fdfcfa) 0%,
    var(--color-victorian-paper-aged, #f0ebe3) 100%
  );
  border: 1px solid var(--color-victorian-paper-antique, #e8e1d5);
  border-radius: 3px;
  box-shadow:
    0 1px 0 var(--color-victorian-paper-antique, #e8e1d5),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  font-family: "Cormorant Garamond", Georgia, serif;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-victorian-ink-dark, #2d2d2a);
  text-align: center;
  white-space: nowrap;
}

.keyboard-shortcuts-modal__description {
  margin: 0;
  padding: 0.25rem 0;
  font-family: Georgia, serif;
  font-size: 0.9375rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  line-height: 1.4;
}

.keyboard-shortcuts-modal__footer {
  padding: 0.75rem 1.25rem;
  background: var(--color-victorian-paper-cream, #f8f5f0);
  border-top: 1px solid var(--color-victorian-paper-antique, #e8e1d5);
  text-align: center;
}

.keyboard-shortcuts-modal__hint {
  font-family: Georgia, serif;
  font-size: 0.8125rem;
  font-style: italic;
  color: var(--color-victorian-ink-muted, #5c5c58);
}

/* Transitions */
.modal-enter-active {
  transition: opacity 200ms ease-out;
}

.modal-leave-active {
  transition: opacity 150ms ease-in;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .keyboard-shortcuts-modal__frame {
  transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-leave-active .keyboard-shortcuts-modal__frame {
  transition: transform 150ms cubic-bezier(0.4, 0, 1, 1);
}

.modal-enter-from .keyboard-shortcuts-modal__frame,
.modal-leave-to .keyboard-shortcuts-modal__frame {
  transform: scale(0.95) translateY(-8px);
}

/* Dark mode adjustments */
:global(.dark) .keyboard-shortcuts-modal__frame {
  background: var(--color-surface-secondary, #2d3028);
  border-color: var(--color-victorian-gold-muted, #b8956e);
  box-shadow:
    0 0 0 1px var(--color-border-default, #3d4a3d),
    0 0 0 4px var(--color-surface-elevated, #343a30),
    0 0 0 5px var(--color-victorian-gold-dark, #a67c00),
    0 8px 32px rgba(0, 0, 0, 0.5);
}

:global(.dark) .keyboard-shortcuts-modal__header {
  background: linear-gradient(
    180deg,
    var(--color-surface-elevated, #343a30) 0%,
    var(--color-surface-secondary, #2d3028) 100%
  );
  border-bottom-color: var(--color-border-default, #3d4a3d);
}

:global(.dark) .keyboard-shortcuts-modal__title {
  color: var(--color-text-primary, #e8e1d5);
}

:global(.dark) .keyboard-shortcuts-modal__close {
  color: var(--color-text-muted, #9a958c);
}

:global(.dark) .keyboard-shortcuts-modal__close:hover {
  background: var(--color-surface-elevated, #343a30);
  border-color: var(--color-border-default, #3d4a3d);
  color: var(--color-text-primary, #e8e1d5);
}

:global(.dark) .keyboard-shortcuts-modal__key kbd {
  background: linear-gradient(
    180deg,
    var(--color-surface-elevated, #343a30) 0%,
    var(--color-surface-secondary, #2d3028) 100%
  );
  border-color: var(--color-border-default, #3d4a3d);
  box-shadow:
    0 1px 0 var(--color-border-default, #3d4a3d),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  color: var(--color-victorian-gold, #c9a227);
}

:global(.dark) .keyboard-shortcuts-modal__description {
  color: var(--color-text-secondary, #c9c3b8);
}

:global(.dark) .keyboard-shortcuts-modal__footer {
  background: var(--color-surface-elevated, #343a30);
  border-top-color: var(--color-border-default, #3d4a3d);
}

:global(.dark) .keyboard-shortcuts-modal__hint {
  color: var(--color-text-muted, #9a958c);
}

/* Mobile adjustments */
@media (max-width: 480px) {
  .keyboard-shortcuts-modal {
    max-width: none;
    margin: 0.5rem;
  }

  .keyboard-shortcuts-modal__list {
    gap: 0.5rem 1rem;
  }

  .keyboard-shortcuts-modal__key kbd {
    min-width: 1.75rem;
    padding: 0.2rem 0.4rem;
    font-size: 0.8125rem;
  }

  .keyboard-shortcuts-modal__description {
    font-size: 0.875rem;
  }
}
</style>
