<script setup lang="ts">
defineProps<{
  count: number;
}>();
</script>

<template>
  <div
    class="book-count-badge inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm border"
    style="
      background-color: rgba(201, 162, 39, 0.1);
      border-color: rgba(201, 162, 39, 0.3);
    "
  >
    <span data-testid="flourish" class="hidden sm:inline text-[var(--victorian-gold)] opacity-60"
      >✦</span
    >
    <span class="font-medium text-[var(--color-text-primary)]">{{ count }}</span>
    <span
      data-testid="books-label"
      class="hidden sm:inline text-[var(--color-text-secondary)]"
      >books</span
    >
    <span data-testid="flourish" class="hidden sm:inline text-[var(--victorian-gold)] opacity-60"
      >✦</span
    >
  </div>
</template>
