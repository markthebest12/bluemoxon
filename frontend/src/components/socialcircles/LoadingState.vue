<script setup lang="ts">
/**
 * LoadingState - Skeleton loader for the graph.
 */
</script>

<template>
  <div class="loading-state">
    <div class="loading-state__spinner">
      <div class="loading-state__ring"></div>
    </div>
    <p class="loading-state__text">Loading social circles...</p>
    <p class="loading-state__subtext">
      Analyzing connections between authors, publishers, and binders
    </p>
  </div>
</template>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  background: var(--color-victorian-paper-cream, #f8f5f0);
}

.loading-state__spinner {
  width: 64px;
  height: 64px;
  margin-bottom: 1.5rem;
}

.loading-state__ring {
  width: 100%;
  height: 100%;
  border: 3px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-top-color: var(--color-victorian-hunter-600, #2f5a4b);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-state__text {
  font-size: 1.125rem;
  font-weight: 500;
  color: var(--color-victorian-hunter-700, #254a3d);
  margin-bottom: 0.5rem;
}

.loading-state__subtext {
  font-size: 0.875rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
}
</style>
