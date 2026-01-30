<script setup lang="ts">
import { computed, ref } from "vue";
import type { ProfileBook } from "@/types/entityProfile";

const props = defineProps<{
  books: ProfileBook[];
}>();

const hoveredBook = ref<ProfileBook | null>(null);
const tooltipX = ref(0);

const booksWithYears = computed(() => props.books.filter((b) => b.year != null));

const yearRange = computed(() => {
  if (booksWithYears.value.length === 0) return { min: 0, max: 0 };
  const years = booksWithYears.value.map((b) => b.year as number);
  const min = Math.min(...years);
  const max = Math.max(...years);
  // Add padding if all same year
  if (min === max) return { min: min - 5, max: max + 5 };
  return { min, max };
});

function getPosition(year: number): number {
  const { min, max } = yearRange.value;
  if (max === min) return 50;
  return ((year - min) / (max - min)) * 100;
}

function handleHover(book: ProfileBook, event: MouseEvent) {
  hoveredBook.value = book;
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  const parent = target.parentElement?.getBoundingClientRect();
  if (parent) {
    tooltipX.value = rect.left - parent.left + rect.width / 2;
  }
}

function handleLeave() {
  hoveredBook.value = null;
}
</script>

<template>
  <section v-if="booksWithYears.length > 0" class="publication-timeline">
    <h2 class="publication-timeline__title">Publication Timeline</h2>
    <div class="publication-timeline__chart">
      <div class="publication-timeline__track">
        <div
          v-for="book in booksWithYears"
          :key="book.id"
          class="publication-timeline__dot"
          :style="{ left: getPosition(book.year as number) + '%' }"
          @mouseenter="handleHover(book, $event)"
          @mouseleave="handleLeave"
        />
      </div>
      <div class="publication-timeline__labels">
        <span>{{ yearRange.min }}</span>
        <span>{{ yearRange.max }}</span>
      </div>
      <div
        v-if="hoveredBook"
        class="publication-timeline__tooltip"
        :style="{ left: tooltipX + 'px' }"
      >
        {{ hoveredBook.title }}
        <span v-if="hoveredBook.year"> ({{ hoveredBook.year }})</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.publication-timeline__title {
  font-size: 20px;
  margin: 0 0 16px;
}

.publication-timeline__chart {
  position: relative;
  padding: 20px 0;
}

.publication-timeline__track {
  position: relative;
  height: 4px;
  background: var(--color-border, #e8e4de);
  border-radius: 2px;
}

.publication-timeline__dot {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-accent-gold, #b8860b);
  cursor: pointer;
  transition: transform 150ms;
}

.publication-timeline__dot:hover {
  transform: translate(-50%, -50%) scale(1.5);
}

.publication-timeline__labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: var(--color-text-muted, #8b8579);
}

.publication-timeline__tooltip {
  position: absolute;
  top: -30px;
  transform: translateX(-50%);
  padding: 4px 8px;
  background: var(--color-text, #2c2420);
  color: #fff;
  font-size: 12px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
}
</style>
