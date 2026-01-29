<script setup lang="ts">
/**
 * LayoutSwitcher - Button group to switch between graph layout modes.
 *
 * Displays four layout options in a horizontal button group with Victorian styling.
 * Active mode is visually highlighted. Tooltips show layout descriptions.
 */

import type { LayoutMode } from "@/types/socialCircles";

const LAYOUT_MODES: readonly LayoutMode[] = ["force", "circle", "grid", "hierarchical"];

const LAYOUT_LABELS: Record<LayoutMode, string> = {
  force: "Force",
  circle: "Circle",
  grid: "Grid",
  hierarchical: "Hierarchy",
};

const LAYOUT_DESCRIPTIONS: Record<LayoutMode, string> = {
  force: "Physics-based layout",
  circle: "Circular arrangement",
  grid: "Grid layout",
  hierarchical: "Tree structure",
};

// Simple SVG icons for each layout mode
const LAYOUT_ICONS: Record<LayoutMode, string> = {
  force: "⚛", // Atom-like symbol for physics
  circle: "◎", // Concentric circles
  grid: "▦", // Grid pattern
  hierarchical: "⊥", // Tree-like symbol
};

interface Props {
  modelValue: LayoutMode;
  disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
  disabled: false,
});

const emit = defineEmits<{
  "update:modelValue": [mode: LayoutMode];
}>();

function selectMode(mode: LayoutMode) {
  emit("update:modelValue", mode);
}
</script>

<template>
  <div
    class="layout-switcher"
    :class="{ 'layout-switcher--disabled': disabled }"
    data-testid="layout-switcher"
  >
    <button
      v-for="mode in LAYOUT_MODES"
      :key="mode"
      type="button"
      class="layout-switcher__btn"
      :class="{ 'layout-switcher__btn--active': modelValue === mode }"
      :title="LAYOUT_DESCRIPTIONS[mode]"
      :disabled="disabled"
      :data-testid="`layout-btn-${mode}`"
      @click="selectMode(mode)"
    >
      <span class="layout-switcher__icon">{{ LAYOUT_ICONS[mode] }}</span>
      <span class="layout-switcher__label">{{ LAYOUT_LABELS[mode] }}</span>
    </button>
  </div>
</template>

<style scoped>
.layout-switcher {
  display: inline-flex;
  background: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  overflow: hidden;
}

.layout-switcher--disabled {
  opacity: 0.5;
  pointer-events: none;
}

.layout-switcher__btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: none;
  border-right: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  font-size: 0.8125rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.layout-switcher__btn:last-child {
  border-right: none;
}

.layout-switcher__btn:hover:not(:disabled):not(.layout-switcher__btn--active) {
  background: var(--color-victorian-paper-cream, #f5f0e6);
}

.layout-switcher__btn:disabled {
  cursor: not-allowed;
}

.layout-switcher__btn--active {
  background: var(--color-victorian-hunter-600, #2f5a4b);
  color: white;
}

.layout-switcher__btn--active:hover {
  background: var(--color-victorian-hunter-700, #254a3d);
}

.layout-switcher__icon {
  font-size: 1rem;
  line-height: 1;
}

.layout-switcher__label {
  font-weight: 500;
}
</style>
