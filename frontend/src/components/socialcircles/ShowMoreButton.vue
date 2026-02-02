<script setup lang="ts">
defineProps<{
  statusText: string | null;
  isFullyExpanded: boolean;
  canShowLess: boolean;
}>();

defineEmits<{
  showMore: [];
  showLess: [];
}>();
</script>

<template>
  <div v-if="statusText || canShowLess" class="show-more-controls" data-testid="show-more-controls">
    <button
      v-if="canShowLess"
      class="show-more-btn"
      data-testid="show-less-btn"
      @click="$emit('showLess')"
    >
      <span class="show-more-btn__action">Show less</span>
    </button>
    <button
      v-if="!isFullyExpanded"
      class="show-more-btn"
      data-testid="show-more-btn"
      @click="$emit('showMore')"
    >
      {{ statusText }} — <span class="show-more-btn__action">Show more</span>
    </button>
    <span v-if="isFullyExpanded && canShowLess" class="show-more-status">
      {{ statusText }}
    </span>
  </div>
</template>

<style scoped>
.show-more-controls {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.show-more-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  background: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  font-size: 0.8125rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.show-more-btn:hover {
  background: var(--color-victorian-paper-cream, #f5f0e6);
}

.show-more-btn__action {
  font-weight: 600;
  color: var(--color-victorian-hunter-600, #2f5a4b);
}

.show-more-status {
  font-size: 0.8125rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
}
</style>
