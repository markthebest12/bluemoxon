<script setup lang="ts">
defineProps<{
  count: number;
}>();

defineEmits<{
  expand: [];
}>();
</script>

<template>
  <button
    v-if="count > 0"
    class="expand-badge"
    data-testid="expand-badge"
    :title="`Show ${count} more connections`"
    @click.stop="$emit('expand')"
  >
    +{{ count }}
  </button>
</template>

<style scoped>
.expand-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 20px;
  padding: 0 6px;
  background: var(--color-accent-gold, #b8860b);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease;
  position: absolute;
  top: -8px;
  right: -8px;
}

.expand-badge:hover {
  background: color-mix(in srgb, var(--color-accent-gold, #b8860b) 85%, black);
}
</style>
