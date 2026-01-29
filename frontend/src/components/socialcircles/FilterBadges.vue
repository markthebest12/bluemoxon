<script setup lang="ts">
/**
 * FilterBadges - Displays count badges for filter options.
 *
 * Two usage modes:
 * 1. Simple: Pass a `count` prop directly
 * 2. Computed: Pass `nodes` and `nodeType` to compute counts internally
 *
 * Badge displays a count number in a compact pill shape.
 * Dims when count is 0.
 */

import { computed } from "vue";

import type { ApiNode, NodeType } from "@/types/socialCircles";

interface Props {
  /** Direct count value (simple mode) */
  count?: number;
  /** Nodes array for computed counts */
  nodes?: ApiNode[];
  /** Node type to count (required when using nodes) */
  nodeType?: NodeType;
}

const props = defineProps<Props>();

const displayCount = computed(() => {
  // Simple mode: use count prop directly
  if (props.count !== undefined) {
    return props.count;
  }

  // Computed mode: calculate from nodes
  if (props.nodes && props.nodeType) {
    return props.nodes.filter((n) => n.type === props.nodeType).length;
  }

  return 0;
});

const isEmpty = computed(() => displayCount.value === 0);
</script>

<template>
  <span class="filter-badge" :class="{ 'filter-badge--empty': isEmpty }">
    {{ displayCount }}
  </span>
</template>

<style scoped>
.filter-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.25rem;
  height: 1.25rem;
  padding: 0 0.375rem;
  font-size: 0.6875rem;
  font-weight: 600;
  line-height: 1;
  color: var(--color-victorian-hunter-700, #254a3d);
  background-color: var(--color-victorian-hunter-100, #e8f0ed);
  border-radius: 999px;
  transition:
    opacity 0.15s ease,
    background-color 0.15s ease;
}

.filter-badge--empty {
  color: var(--color-victorian-ink-muted, #5c5c58);
  background-color: var(--color-victorian-paper-aged, #e8e1d5);
  opacity: 0.6;
}
</style>
