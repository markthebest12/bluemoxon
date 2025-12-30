<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    count?: number;
  }>(),
  { count: 0 }
);

const formattedCount = computed(() => props.count.toLocaleString());
const label = computed(() => (props.count === 1 ? "book" : "books"));
</script>

<script lang="ts">
import { computed } from "vue";
</script>

<template>
  <div
    class="book-count-badge inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm border bg-[var(--color-victorian-gold)]/10 border-[var(--color-victorian-gold)]/30 dark:bg-[var(--color-victorian-gold)]/15 dark:border-[var(--color-victorian-gold)]/40"
  >
    <span
      data-testid="flourish"
      class="hidden sm:inline text-[var(--color-victorian-gold)] opacity-60 dark:opacity-80"
      >✦</span
    >
    <span class="font-medium text-[var(--color-text-primary)]">{{ formattedCount }}</span>
    <span data-testid="books-label" class="hidden sm:inline text-[var(--color-text-secondary)]">{{
      label
    }}</span>
    <span
      data-testid="flourish"
      class="hidden sm:inline text-[var(--color-victorian-gold)] opacity-60 dark:opacity-80"
      >✦</span
    >
  </div>
</template>
