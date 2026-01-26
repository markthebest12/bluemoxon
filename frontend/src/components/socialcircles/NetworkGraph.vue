<!-- frontend/src/components/socialcircles/NetworkGraph.vue -->
<script setup lang="ts">
/**
 * NetworkGraph - Cytoscape.js wrapper for the social circles visualization.
 *
 * This component renders the network graph and handles:
 * - Graph initialization and cleanup
 * - Node/edge rendering with Victorian theme
 * - User interactions (click, hover, zoom, pan)
 * - Layout management
 */

import { ref, onMounted, onUnmounted } from "vue";

// Props
interface Props {
  elements?: unknown[];
  selectedNode?: unknown;
  selectedEdge?: unknown;
  highlightedNodes?: string[];
  highlightedEdges?: string[];
}

defineProps<Props>();

// Emits
defineEmits<{
  "node-selected": [nodeId: string];
  "node-hovered": [nodeId: string | null];
  "edge-hovered": [edgeId: string | null];
}>();

// Refs
const containerRef = ref<HTMLDivElement | null>(null);
const isInitialized = ref(false);

// Lifecycle
onMounted(() => {
  // Cytoscape initialization will go here
  // containerRef.value will be used to mount the graph
  if (containerRef.value) {
    isInitialized.value = true;
  }
});

onUnmounted(() => {
  // Cleanup will go here
});

// Expose for parent component access
defineExpose({
  containerRef,
});
</script>

<template>
  <div
    ref="containerRef"
    class="network-graph"
    :class="{ 'network-graph--initialized': isInitialized }"
  >
    <div v-if="!isInitialized" class="network-graph__loading">Initializing graph...</div>
  </div>
</template>

<style scoped>
.network-graph {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background-color: var(--color-victorian-paper-cream, #f8f5f0);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
}

.network-graph__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-victorian-ink-muted, #5c5c58);
}
</style>
