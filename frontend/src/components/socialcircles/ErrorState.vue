<script setup lang="ts">
/**
 * ErrorState - Error display with retry option.
 */

interface Props {
  message?: string;
  retryable?: boolean;
}

withDefaults(defineProps<Props>(), {
  message: 'An error occurred while loading the network.',
  retryable: true,
});

const emit = defineEmits<{
  retry: [];
}>();
</script>

<template>
  <div class="error-state">
    <div class="error-state__icon">⚠️</div>
    <h3 class="error-state__title">Something went wrong</h3>
    <p class="error-state__message">{{ message }}</p>
    <button
      v-if="retryable"
      class="error-state__btn"
      @click="emit('retry')"
    >
      Try Again
    </button>
  </div>
</template>

<style scoped>
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  text-align: center;
  background: var(--color-victorian-paper-cream, #f8f5f0);
}

.error-state__icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.error-state__title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-victorian-burgundy, #722f37);
  margin-bottom: 0.5rem;
}

.error-state__message {
  font-size: 0.875rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  max-width: 400px;
  margin-bottom: 1.5rem;
}

.error-state__btn {
  padding: 0.5rem 1.5rem;
  background: var(--color-victorian-burgundy, #722f37);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.error-state__btn:hover {
  background: var(--color-victorian-burgundy-dark, #5c262e);
}
</style>
