<script setup lang="ts">
/**
 * ConnectionTooltip - Hover tooltip showing connection details.
 */

interface Props {
  visible?: boolean;
  x?: number;
  y?: number;
  sourceNode?: string;
  targetNode?: string;
  connectionType?: string;
  strength?: number;
  evidence?: string;
}

withDefaults(defineProps<Props>(), {
  visible: false,
  x: 0,
  y: 0,
  sourceNode: "",
  targetNode: "",
  connectionType: "",
  strength: undefined,
  evidence: undefined,
});
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="connection-tooltip" :style="{ left: `${x}px`, top: `${y}px` }">
      <div class="connection-tooltip__header">
        <span class="connection-tooltip__type">{{ connectionType }}</span>
      </div>
      <div class="connection-tooltip__content">
        <p class="connection-tooltip__nodes">{{ sourceNode }} → {{ targetNode }}</p>
        <p v-if="evidence" class="connection-tooltip__evidence">
          {{ evidence }}
        </p>
        <p v-if="strength" class="connection-tooltip__strength">Strength: {{ strength }}/10</p>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.connection-tooltip {
  position: fixed;
  z-index: 1000;
  background: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-gold, #c9a227);
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  padding: 0.75rem;
  min-width: 200px;
  max-width: 300px;
  pointer-events: none;
  transform: translate(-50%, -100%) translateY(-8px);
}

.connection-tooltip__header {
  border-bottom: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  padding-bottom: 0.5rem;
  margin-bottom: 0.5rem;
}

.connection-tooltip__type {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-victorian-hunter-600, #2f5a4b);
}

.connection-tooltip__nodes {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.connection-tooltip__evidence {
  font-size: 0.875rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  font-style: italic;
}

.connection-tooltip__strength {
  font-size: 0.75rem;
  color: var(--color-victorian-gold-dark, #a67c00);
  margin-top: 0.5rem;
}
</style>
