<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  data: Record<number, number>;
}>();

const sortedYears = computed(() =>
  Object.entries(props.data)
    .map(([year, count]) => ({ year: Number(year), count }))
    .sort((a, b) => a.year - b.year)
);

const maxCount = computed(() => Math.max(...sortedYears.value.map((y) => y.count), 1));

const shouldShow = computed(() => sortedYears.value.length >= 2);

const MAX_BAR_HEIGHT = 120;

function barHeight(count: number): number {
  return Math.round((count / maxCount.value) * MAX_BAR_HEIGHT);
}
</script>

<template>
  <section v-if="shouldShow" class="acquisition-timeline" data-testid="acquisition-timeline">
    <h3 class="acquisition-timeline__title">Acquisition History</h3>
    <div class="acquisition-timeline__chart">
      <div v-for="entry in sortedYears" :key="entry.year" class="acquisition-timeline__column">
        <span class="acquisition-timeline__count">{{ entry.count }}</span>
        <div
          class="acquisition-timeline__bar"
          data-testid="acquisition-bar"
          :style="{ height: barHeight(entry.count) + 'px' }"
        />
        <span class="acquisition-timeline__year">{{ entry.year }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.acquisition-timeline {
  margin-top: 24px;
}

.acquisition-timeline__title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--color-text, #2c2420);
}

.acquisition-timeline__chart {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 8px 0;
}

.acquisition-timeline__column {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.acquisition-timeline__count {
  font-size: 11px;
  color: var(--color-text-muted, #8b8579);
  margin-bottom: 4px;
}

.acquisition-timeline__bar {
  width: 100%;
  max-width: 40px;
  min-height: 4px;
  background: #a0522d;
  border-radius: 3px 3px 0 0;
  transition: height 300ms ease;
}

.acquisition-timeline__year {
  font-size: 11px;
  color: var(--color-text-muted, #8b8579);
  margin-top: 4px;
  white-space: nowrap;
}

@media (max-width: 480px) {
  .acquisition-timeline__chart {
    gap: 4px;
  }

  .acquisition-timeline__bar {
    max-width: 28px;
  }

  .acquisition-timeline__year {
    font-size: 10px;
  }
}
</style>
