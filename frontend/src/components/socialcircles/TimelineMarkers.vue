<script setup lang="ts">
/**
 * TimelineMarkers - Historical event markers on the timeline slider.
 *
 * Features:
 * - Markers positioned correctly along timeline based on year
 * - Tooltip shows event label on hover
 * - Only shows events within visible range [minYear, maxYear]
 * - Different colors/styles for event types (political, literary, cultural)
 * - Victorian styling for markers
 */

import { computed, ref } from "vue";

export interface HistoricalEvent {
  year: number;
  label: string;
  type: "political" | "literary" | "cultural";
}

interface Props {
  minYear: number;
  maxYear: number;
  events?: HistoricalEvent[];
}

const VICTORIAN_EVENTS: HistoricalEvent[] = [
  { year: 1837, label: "Victoria's Coronation", type: "political" },
  { year: 1851, label: "Great Exhibition", type: "cultural" },
  { year: 1859, label: "Origin of Species", type: "literary" },
  { year: 1901, label: "Victoria Dies", type: "political" },
];

const props = withDefaults(defineProps<Props>(), {
  events: () => VICTORIAN_EVENTS,
});

// Track which marker is being hovered
const hoveredEvent = ref<HistoricalEvent | null>(null);

// Filter events to only those within the visible range
const visibleEvents = computed(() => {
  return props.events.filter((event) => event.year >= props.minYear && event.year <= props.maxYear);
});

// Calculate horizontal position percentage for an event
function getPositionPercent(year: number): number {
  const range = props.maxYear - props.minYear;
  if (range === 0) return 0;
  return ((year - props.minYear) / range) * 100;
}

// Get color class based on event type
function getEventTypeClass(type: HistoricalEvent["type"]): string {
  return `timeline-markers__marker--${type}`;
}

function handleMouseEnter(event: HistoricalEvent) {
  hoveredEvent.value = event;
}

function handleMouseLeave() {
  hoveredEvent.value = null;
}
</script>

<template>
  <div class="timeline-markers">
    <div
      v-for="event in visibleEvents"
      :key="`${event.year}-${event.label}`"
      class="timeline-markers__marker"
      :class="getEventTypeClass(event.type)"
      :style="{ left: `${getPositionPercent(event.year)}%` }"
      @mouseenter="handleMouseEnter(event)"
      @mouseleave="handleMouseLeave"
    >
      <div class="timeline-markers__line" />
      <span class="timeline-markers__year">{{ event.year }}</span>

      <!-- Tooltip -->
      <Transition name="marker-tooltip-fade">
        <div v-if="hoveredEvent === event" class="timeline-markers__tooltip">
          <span class="timeline-markers__tooltip-type">{{ event.type }}</span>
          <span class="timeline-markers__tooltip-label">{{ event.label }}</span>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.timeline-markers {
  position: relative;
  width: 100%;
  height: 32px;
  margin-top: 0.25rem;
}

.timeline-markers__marker {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  transform: translateX(-50%);
  cursor: pointer;
}

.timeline-markers__line {
  width: 2px;
  height: 12px;
  border-radius: 1px;
}

.timeline-markers__year {
  font-size: 0.625rem;
  margin-top: 2px;
  font-family: Georgia, serif;
  color: var(--color-victorian-ink-muted, #5c5c58);
}

/* Event type colors */
.timeline-markers__marker--political .timeline-markers__line {
  background-color: var(--color-victorian-burgundy, #722f37);
}

.timeline-markers__marker--political .timeline-markers__year {
  color: var(--color-victorian-burgundy, #722f37);
}

.timeline-markers__marker--literary .timeline-markers__line {
  background-color: var(--color-victorian-hunter-600, #2f5a4b);
}

.timeline-markers__marker--literary .timeline-markers__year {
  color: var(--color-victorian-hunter-600, #2f5a4b);
}

.timeline-markers__marker--cultural .timeline-markers__line {
  background-color: var(--color-victorian-gold-dark, #8b6914);
}

.timeline-markers__marker--cultural .timeline-markers__year {
  color: var(--color-victorian-gold-dark, #8b6914);
}

/* Hover state */
.timeline-markers__marker:hover .timeline-markers__line {
  height: 16px;
  transition: height 150ms ease;
}

.timeline-markers__marker:hover .timeline-markers__year {
  font-weight: 600;
}

/* Tooltip */
.timeline-markers__tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 8px;
  padding: 0.5rem 0.75rem;
  background-color: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e4d9);
  border-radius: 4px;
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.1),
    0 1px 2px rgba(0, 0, 0, 0.06);
  white-space: nowrap;
  z-index: 10;
  font-family: Georgia, serif;
}

.timeline-markers__tooltip::after {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: var(--color-victorian-paper-white, #fdfcfa);
}

.timeline-markers__tooltip::before {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 7px solid transparent;
  border-top-color: var(--color-victorian-paper-aged, #e8e4d9);
}

.timeline-markers__tooltip-type {
  display: block;
  font-size: 0.5625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin-bottom: 0.125rem;
}

.timeline-markers__tooltip-label {
  display: block;
  font-size: 0.8125rem;
  color: var(--color-victorian-ink, #3a3a38);
  font-weight: 500;
}

/* Tooltip fade animation */
.marker-tooltip-fade-enter-active,
.marker-tooltip-fade-leave-active {
  transition:
    opacity 150ms ease,
    transform 150ms ease;
}

.marker-tooltip-fade-enter-from,
.marker-tooltip-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(4px);
}
</style>
