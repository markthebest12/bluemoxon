<script setup lang="ts">
import { ref, watch } from "vue";

interface Props {
  modelValue: boolean;
  title?: string;
  maxHeight?: string;
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
}

const props = withDefaults(defineProps<Props>(), {
  title: undefined,
  maxHeight: "80vh",
});

const emit = defineEmits<Emits>();

// Touch gesture tracking
const touchStartY = ref(0);
const touchCurrentY = ref(0);
const isDragging = ref(false);
const sheetTranslateY = ref(0);

const SWIPE_THRESHOLD = 100; // pixels to trigger close

function close() {
  emit("update:modelValue", false);
}

function handleTouchStart(event: TouchEvent) {
  touchStartY.value = event.touches[0].clientY;
  touchCurrentY.value = event.touches[0].clientY;
  isDragging.value = true;
}

function handleTouchMove(event: TouchEvent) {
  if (!isDragging.value) return;

  touchCurrentY.value = event.touches[0].clientY;
  const deltaY = touchCurrentY.value - touchStartY.value;

  // Only allow dragging downward (positive deltaY)
  if (deltaY > 0) {
    sheetTranslateY.value = deltaY;
    // Prevent default to stop page scrolling while dragging
    event.preventDefault();
  }
}

function handleTouchEnd() {
  if (!isDragging.value) return;

  isDragging.value = false;

  // If dragged past threshold, close the sheet
  if (sheetTranslateY.value > SWIPE_THRESHOLD) {
    close();
  }

  // Reset translation
  sheetTranslateY.value = 0;
}

// Reset state when sheet closes
watch(
  () => props.modelValue,
  (newValue) => {
    if (!newValue) {
      sheetTranslateY.value = 0;
      isDragging.value = false;
    }
  }
);
</script>

<template>
  <Teleport to="body">
    <Transition name="bottom-sheet">
      <div v-if="modelValue" class="bottom-sheet-overlay" @click="close">
        <div
          class="bottom-sheet"
          :style="{
            maxHeight: maxHeight,
            transform: isDragging ? `translateY(${sheetTranslateY}px)` : undefined,
            transition: isDragging ? 'none' : undefined,
          }"
          @click.stop
          @touchstart="handleTouchStart"
          @touchmove.passive="handleTouchMove"
          @touchend="handleTouchEnd"
        >
          <div class="bottom-sheet-handle" />
          <div v-if="title" class="bottom-sheet-header">
            <h3>{{ title }}</h3>
            <button class="bottom-sheet-close" aria-label="Close" @click="close">&times;</button>
          </div>
          <div class="bottom-sheet-content">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.bottom-sheet-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.bottom-sheet {
  width: 100%;
  max-width: 100%;
  background-color: var(--color-background, #fff);
  border-radius: 16px 16px 0 0;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  /* Safe area for iOS notch/home indicator */
  padding-bottom: env(safe-area-inset-bottom, 0);
  transition:
    transform 0.3s ease-out,
    opacity 0.3s ease-out;
}

.bottom-sheet-handle {
  width: 36px;
  height: 4px;
  background-color: var(--color-border, #d1d5db);
  border-radius: 2px;
  margin: 12px auto 8px;
  flex-shrink: 0;
}

.bottom-sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px 16px;
  border-bottom: 1px solid var(--color-border, #e5e7eb);
  flex-shrink: 0;
}

.bottom-sheet-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text, #1f2937);
}

.bottom-sheet-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--color-text-secondary, #6b7280);
  cursor: pointer;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.bottom-sheet-close:hover {
  background-color: var(--color-background-hover, #f3f4f6);
}

.bottom-sheet-close:focus-visible {
  outline: 2px solid var(--color-primary, #3b82f6);
  outline-offset: 2px;
}

.bottom-sheet-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  /* Prevent content from being cut off by safe area */
  padding-bottom: calc(16px + env(safe-area-inset-bottom, 0));
}

/* Transition animations */
.bottom-sheet-enter-active,
.bottom-sheet-leave-active {
  transition: opacity 0.3s ease;
}

.bottom-sheet-enter-active .bottom-sheet,
.bottom-sheet-leave-active .bottom-sheet {
  transition: transform 0.3s ease-out;
}

.bottom-sheet-enter-from,
.bottom-sheet-leave-to {
  opacity: 0;
}

.bottom-sheet-enter-from .bottom-sheet,
.bottom-sheet-leave-to .bottom-sheet {
  transform: translateY(100%);
}
</style>
