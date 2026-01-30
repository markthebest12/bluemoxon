<script setup lang="ts">
defineProps<{
  entityType: string;
  entityId: number;
}>();
</script>

<template>
  <div class="stale-banner" role="status">
    <span class="stale-banner__text"
      >Profile may be outdated. Your collection has changed since this was generated.</span
    >
    <!-- Regenerate button will be wired in Phase 2 (AI enrichment) -->
  </div>
</template>

<style scoped>
.stale-banner {
  padding: 12px 16px;
  background: var(--color-warning-bg, #fff8e1);
  border: 1px solid var(--color-warning, #f9a825);
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
}
</style>
