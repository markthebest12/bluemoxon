<script setup lang="ts">
defineProps<{
  entityType: string;
  entityId: number;
  regenerating: boolean;
}>();

const emit = defineEmits<{
  regenerate: [];
}>();
</script>

<template>
  <div class="stale-banner" role="status">
    <span class="stale-banner__text"
      >Profile may be outdated. Your collection has changed since this was generated.</span
    >
    <button class="stale-banner__button" :disabled="regenerating" @click="emit('regenerate')">
      {{ regenerating ? "Regenerating..." : "Regenerate" }}
    </button>
  </div>
</template>

<style scoped>
.stale-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  background: var(--color-warning-bg, #fff8e1);
  border: 1px solid var(--color-warning, #f9a825);
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
}

.stale-banner__button {
  white-space: nowrap;
  padding: 6px 12px;
  background: var(--color-warning, #f9a825);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
}

.stale-banner__button:hover:not(:disabled) {
  opacity: 0.9;
}

.stale-banner__button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
