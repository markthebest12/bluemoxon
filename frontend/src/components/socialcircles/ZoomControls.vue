<script setup lang="ts">
/**
 * ZoomControls - Zoom in/out/fit controls for the graph.
 */

interface Props {
  zoomLevel?: number;
  minZoom?: number;
  maxZoom?: number;
}

withDefaults(defineProps<Props>(), {
  zoomLevel: 1,
  minZoom: 0.1,
  maxZoom: 3,
});

const emit = defineEmits<{
  "zoom-in": [];
  "zoom-out": [];
  fit: [];
  "zoom-change": [level: number];
}>();

function formatZoom(level: number): string {
  return `${Math.round(level * 100)}%`;
}
</script>

<template>
  <div class="zoom-controls">
    <button
      class="zoom-controls__btn"
      title="Zoom In (+)"
      :disabled="zoomLevel >= maxZoom"
      @click="emit('zoom-in')"
    >
      +
    </button>

    <span class="zoom-controls__level">
      {{ formatZoom(zoomLevel) }}
    </span>

    <button
      class="zoom-controls__btn"
      title="Zoom Out (-)"
      :disabled="zoomLevel <= minZoom"
      @click="emit('zoom-out')"
    >
      −
    </button>

    <button
      class="zoom-controls__btn zoom-controls__btn--fit"
      title="Fit to View (0)"
      @click="emit('fit')"
    >
      ⊡
    </button>
  </div>
</template>

<style scoped>
.zoom-controls {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  background: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  padding: 0.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.zoom-controls__btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--color-victorian-paper-aged);
  border-radius: 4px;
  font-size: 1.25rem;
  color: var(--color-victorian-hunter-700);
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.zoom-controls__btn:hover:not(:disabled) {
  background: var(--color-victorian-paper-cream);
}

.zoom-controls__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.zoom-controls__btn--fit {
  margin-top: 0.5rem;
  border-top: 1px solid var(--color-victorian-paper-aged);
  padding-top: 0.5rem;
}

.zoom-controls__level {
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted);
  padding: 0.25rem 0;
}
</style>
