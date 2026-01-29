<script setup lang="ts">
/**
 * FindSimilarButton - Button to find nodes with similar connections.
 */

import type { NodeId } from "@/types/socialCircles";

interface Props {
  nodeId: NodeId;
  disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
  disabled: false,
});

defineEmits<{
  "find-similar": [nodeId: NodeId];
}>();
</script>

<template>
  <button
    class="find-similar-btn"
    :disabled="disabled"
    title="Find people with similar connections"
    @click="$emit('find-similar', nodeId)"
  >
    Find Similar
  </button>
</template>

<style scoped>
.find-similar-btn {
  padding: 0.5rem 1rem;
  background: var(--color-victorian-hunter-600);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.find-similar-btn:hover:not(:disabled) {
  background: var(--color-victorian-hunter-700);
}

.find-similar-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
