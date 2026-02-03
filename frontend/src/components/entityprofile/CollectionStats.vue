<script setup lang="ts">
import { computed } from "vue";
import type { ProfileStats } from "@/types/entityProfile";
import { getConditionColor, formatConditionGrade } from "@/utils/conditionColors";

const props = defineProps<{
  stats: ProfileStats;
}>();

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const conditionEntries = computed(() =>
  Object.entries(props.stats.condition_distribution).filter(([, count]) => count > 0)
);

const hasConditionData = computed(() => conditionEntries.value.length > 0);

const isSingleCondition = computed(() => conditionEntries.value.length === 1);
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

    <section
      v-if="hasConditionData"
      class="collection-stats__condition"
      data-testid="condition-breakdown"
    >
      <h3 class="collection-stats__condition-title">Condition Breakdown</h3>

      <p v-if="isSingleCondition" class="collection-stats__condition-single">
        All books: {{ formatConditionGrade(conditionEntries[0][0]) }} ({{ conditionEntries[0][1] }})
      </p>

      <template v-else>
        <div class="collection-stats__condition-bar" data-testid="condition-bar">
          <div
            v-for="[grade, count] in conditionEntries"
            :key="grade"
            class="collection-stats__condition-segment"
            data-testid="condition-segment"
            :style="{
              flexGrow: count,
              minWidth: '3%',
              backgroundColor: getConditionColor(grade),
            }"
          />
        </div>

        <div class="collection-stats__condition-legend" data-testid="condition-legend">
          <span
            v-for="[grade, count] in conditionEntries"
            :key="grade"
            class="collection-stats__condition-legend-item"
          >
            <span
              class="collection-stats__condition-swatch"
              :style="{ backgroundColor: getConditionColor(grade) }"
            />
            {{ formatConditionGrade(grade) }}
            <span class="collection-stats__condition-count">{{ count }}</span>
          </span>
        </div>
      </template>
    </section>
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

.collection-stats__condition {
  margin-top: 20px;
}

.collection-stats__condition-title {
  font-size: 14px;
  color: var(--color-text-muted, #8b8579);
  text-transform: uppercase;
  margin: 0 0 10px;
}

.collection-stats__condition-single {
  font-size: 14px;
  color: var(--color-text, #3d3929);
  margin: 0;
}

.collection-stats__condition-bar {
  display: flex;
  height: 16px;
  border-radius: 4px;
  overflow: hidden;
  gap: 1px;
}

.collection-stats__condition-segment {
  transition: opacity 0.2s;
}

.collection-stats__condition-segment:hover {
  opacity: 0.8;
}

.collection-stats__condition-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
}

.collection-stats__condition-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text, #3d3929);
}

.collection-stats__condition-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.collection-stats__condition-count {
  color: var(--color-text-muted, #8b8579);
}

@media (max-width: 480px) {
  .collection-stats__grid {
    grid-template-columns: 1fr;
  }
}
</style>
