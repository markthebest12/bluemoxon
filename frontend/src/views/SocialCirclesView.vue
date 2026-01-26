<!-- frontend/src/views/SocialCirclesView.vue -->
<script setup lang="ts">
/**
 * Social Circles - Interactive Network Visualization
 *
 * Main view for the Victorian Social Circles feature.
 * Shows connections between authors, publishers, and binders.
 */

import { ref } from 'vue';

// Placeholder - will be replaced with actual composables
const isLoading = ref(true);
const error = ref<string | null>(null);

// Simulate loading for now
setTimeout(() => {
  isLoading.value = false;
}, 1000);
</script>

<template>
  <div class="social-circles-view">
    <!-- Header -->
    <header class="social-circles-header">
      <h1 class="text-2xl font-serif text-victorian-hunter-700">
        Victorian Social Circles
      </h1>
      <p class="text-sm text-victorian-ink-muted">
        Explore the connections between authors, publishers, and binders
      </p>
    </header>

    <!-- Loading State -->
    <div v-if="isLoading" class="social-circles-loading">
      <div class="animate-pulse flex flex-col items-center gap-4">
        <div class="w-16 h-16 bg-victorian-hunter-200 rounded-full" />
        <p class="text-victorian-ink-muted">Loading network...</p>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="social-circles-error">
      <p class="text-victorian-burgundy">{{ error }}</p>
      <button
        class="mt-4 px-4 py-2 bg-victorian-hunter-600 text-white rounded hover:bg-victorian-hunter-700"
      >
        Retry
      </button>
    </div>

    <!-- Main Content (placeholder) -->
    <div v-else class="social-circles-content">
      <p class="text-center text-victorian-ink-muted py-20">
        Network graph will render here
      </p>
    </div>
  </div>
</template>

<style scoped>
.social-circles-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--color-victorian-paper-cream);
}

.social-circles-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--color-victorian-paper-aged);
  background-color: var(--color-victorian-paper-white);
}

.social-circles-loading,
.social-circles-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 2rem;
}

.social-circles-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}
</style>
