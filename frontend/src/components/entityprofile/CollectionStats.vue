<script setup lang="ts">
import type { ProfileStats } from "@/types/entityProfile";

defineProps<{
  stats: ProfileStats;
}>();

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});
</script>

<template>
  <section class="collection-stats">
    <h2 class="collection-stats__title">Collection Stats</h2>
    <dl class="collection-stats__grid">
      <div class="collection-stats__item">
        <dt>Total Books</dt>
        <dd>{{ stats.total_books }}</dd>
      </div>
      <div v-if="stats.total_estimated_value" class="collection-stats__item">
        <dt>Estimated Value</dt>
        <dd>{{ currencyFormatter.format(stats.total_estimated_value) }}</dd>
      </div>
      <div v-if="stats.first_editions > 0" class="collection-stats__item">
        <dt>First Editions</dt>
        <dd>{{ stats.first_editions }}</dd>
      </div>
      <div v-if="stats.date_range.length === 2" class="collection-stats__item">
        <dt>Date Range</dt>
        <dd>{{ stats.date_range[0] }} &ndash; {{ stats.date_range[1] }}</dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.collection-stats__title {
  font-size: 20px;
  margin: 0 0 16px;
}

.collection-stats__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 0;
}

.collection-stats__item {
  padding: 12px;
  background: var(--color-surface, #faf8f5);
  border-radius: 6px;
  border: 1px solid var(--color-border, #e8e4de);
}

.collection-stats__item dt {
  font-size: 12px;
  color: var(--color-text-muted, #8b8579);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.collection-stats__item dd {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

@media (max-width: 480px) {
  .collection-stats__grid {
    grid-template-columns: 1fr;
  }
}
</style>
