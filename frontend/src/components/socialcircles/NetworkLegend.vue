<script setup lang="ts">
/**
 * NetworkLegend - Visual encoding guide for the graph.
 */

const nodeTypes = [
  { shape: 'circle', color: 'var(--color-victorian-hunter-600)', label: 'Author' },
  { shape: 'square', color: 'var(--color-victorian-gold)', label: 'Publisher' },
  { shape: 'diamond', color: 'var(--color-victorian-burgundy)', label: 'Binder' },
];

const connectionTypes = [
  { style: 'solid', color: 'var(--color-victorian-gold)', label: 'Published by' },
  { style: 'solid', color: 'var(--color-victorian-hunter-500)', label: 'Shared publisher' },
  { style: 'dashed', color: 'var(--color-victorian-burgundy)', label: 'Bound by' },
];
</script>

<template>
  <div class="network-legend">
    <div class="network-legend__section">
      <span class="network-legend__title">Nodes</span>
      <div class="network-legend__items">
        <div v-for="node in nodeTypes" :key="node.label" class="network-legend__item">
          <span
            class="network-legend__shape"
            :class="`network-legend__shape--${node.shape}`"
            :style="{ backgroundColor: node.color }"
          />
          <span class="network-legend__label">{{ node.label }}</span>
        </div>
      </div>
    </div>
    <div class="network-legend__section">
      <span class="network-legend__title">Connections</span>
      <div class="network-legend__items">
        <div v-for="conn in connectionTypes" :key="conn.label" class="network-legend__item">
          <span
            class="network-legend__line"
            :class="`network-legend__line--${conn.style}`"
            :style="{ backgroundColor: conn.color }"
          />
          <span class="network-legend__label">{{ conn.label }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.network-legend {
  position: absolute;
  bottom: 1rem;
  right: 1rem;
  display: flex;
  gap: 1.5rem;
  background: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged);
  border-radius: 4px;
  padding: 0.75rem 1rem;
  font-size: 0.75rem;
}

.network-legend__title {
  font-weight: 600;
  color: var(--color-victorian-ink-muted);
  text-transform: uppercase;
  display: block;
  margin-bottom: 0.5rem;
}

.network-legend__items {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.network-legend__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.network-legend__shape {
  width: 12px;
  height: 12px;
}

.network-legend__shape--circle {
  border-radius: 50%;
}

.network-legend__shape--square {
  border-radius: 2px;
}

.network-legend__shape--diamond {
  transform: rotate(45deg);
  width: 10px;
  height: 10px;
}

.network-legend__line {
  width: 20px;
  height: 2px;
}

.network-legend__line--dashed {
  background: repeating-linear-gradient(
    to right,
    currentColor,
    currentColor 4px,
    transparent 4px,
    transparent 8px
  );
}

.network-legend__label {
  color: var(--color-victorian-ink-dark);
}
</style>
