<script setup lang="ts">
/**
 * EmptyState - Shown when no results match filters.
 */

const emit = defineEmits<{
  "reset-filters": [];
}>();
</script>

<template>
  <div class="empty-state">
    <div class="empty-state__icon">🔍</div>
    <h3 class="empty-state__title">No connections found</h3>
    <p class="empty-state__text">
      Try adjusting your filters or search criteria to see more results.
    </p>
    <button class="empty-state__btn" @click="emit('reset-filters')">Reset Filters</button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  text-align: center;
  background: var(--color-victorian-paper-cream, #f8f5f0);
}

.empty-state__icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state__title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-victorian-hunter-700, #254a3d);
  margin-bottom: 0.5rem;
}

.empty-state__text {
  font-size: 0.875rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  max-width: 300px;
  margin-bottom: 1.5rem;
}

.empty-state__btn {
  padding: 0.5rem 1rem;
  background: var(--color-victorian-hunter-600, #2f5a4b);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.empty-state__btn:hover {
  background: var(--color-victorian-hunter-700, #254a3d);
}
</style>
