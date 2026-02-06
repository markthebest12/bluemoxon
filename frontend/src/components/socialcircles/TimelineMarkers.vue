<script setup lang="ts">
/**
 * TimelineMarkers - Historical event markers on the timeline slider.
 *
 * Features:
 * - Markers positioned correctly along timeline based on year
 * - Tooltip shows event label on hover or keyboard focus
 * - Only shows events within visible range [minYear, maxYear]
 * - Different colors/styles for event types (political, literary, cultural)
 * - Victorian styling for markers
 * - Keyboard accessible (Tab, Enter/Space to activate)
 * - Dynamic tooltip positioning to prevent edge clipping
 */

import { computed, ref } from "vue";
import { useElementSize } from "@vueuse/core";
import type { HistoricalEvent } from "@/types/socialCircles";
import { VICTORIAN_EVENTS } from "@/constants/socialCircles";

interface Props {
  minYear: number;
  maxYear: number;
  sliderYear?: number;
  events?: readonly HistoricalEvent[];
}

const props = withDefaults(defineProps<Props>(), {
  sliderYear: undefined,
  events: () => VICTORIAN_EVENTS,
});

// Reactive container width for pixel-based label spacing
const containerRef = ref<HTMLElement>();
const { width: containerWidth } = useElementSize(containerRef);

// Track which marker is being hovered or focused (by ID string)
const hoveredEventKey = ref<string | null>(null);

// Single identity function used for both v-for keys and tooltip DOM IDs
function getEventId(event: HistoricalEvent): string {
  const slugLabel = event.label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
  return `tooltip-${event.year}-${slugLabel}`;
}

// Enriched event with precomputed _id and label visibility flag
type EnrichedEvent = HistoricalEvent & { _id: string; _showLabel: boolean };

// Minimum pixel spacing between year labels to prevent overlap.
// Converted dynamically to a percentage based on actual container width
// so label density stays consistent across viewports.
const MIN_LABEL_PX = 60;

// Epsilon for floating point comparison tolerance
const EPSILON = 0.001;

// Filter events to only those within the visible range, with precomputed IDs
// and label visibility flags to prevent overlapping year text.
const visibleEvents = computed<EnrichedEvent[]>(() => {
  if (props.maxYear < props.minYear) return [];
  const filtered = props.events
    .filter((event) => event.year >= props.minYear && event.year <= props.maxYear)
    .map((e) => ({ ...e, _id: getEventId(e), _showLabel: false }));

  // Sort by year to evaluate label spacing left-to-right
  filtered.sort((a, b) => a.year - b.year);

  // Convert pixel threshold to percentage based on actual container width
  const minSpacing = containerWidth.value > 0 ? (MIN_LABEL_PX / containerWidth.value) * 100 : 4;

  const sliderPercent =
    props.sliderYear !== undefined ? getPositionPercent(props.sliderYear) : null;

  let lastShownPercent = -Infinity;
  for (const event of filtered) {
    const percent = getPositionPercent(event.year);
    const tooCloseToSlider =
      sliderPercent !== null && Math.abs(percent - sliderPercent) < minSpacing;
    if (!tooCloseToSlider && percent - lastShownPercent >= minSpacing - EPSILON) {
      event._showLabel = true;
      lastShownPercent = percent;
    }
  }

  return filtered;
});

// Calculate horizontal position percentage for an event
function getPositionPercent(year: number): number {
  const range = props.maxYear - props.minYear;
  // Edge case: when minYear === maxYear, all events map to same position (50%)
  if (range === 0) return 50;
  if (range < 0) return 0;
  return ((year - props.minYear) / range) * 100;
}

// Tooltip alignment thresholds (percentage of timeline width)
const TOOLTIP_EDGE_THRESHOLD_LEFT = 15;
const TOOLTIP_EDGE_THRESHOLD_RIGHT = 85;

// Determine tooltip alignment class based on marker position
function getTooltipAlignClass(year: number): string {
  const percent = getPositionPercent(year);
  if (percent < TOOLTIP_EDGE_THRESHOLD_LEFT) return "timeline-markers__tooltip--align-left";
  if (percent > TOOLTIP_EDGE_THRESHOLD_RIGHT) return "timeline-markers__tooltip--align-right";
  return "";
}

// Get color class based on event type
function getEventTypeClass(type: HistoricalEvent["type"]): string {
  return `timeline-markers__marker--${type}`;
}

// Build aria-label for a marker
function getAriaLabel(event: HistoricalEvent): string {
  return `${event.year}: ${event.label} (${event.type})`;
}

function showTooltip(id: string) {
  hoveredEventKey.value = id;
}

function hideTooltip() {
  hoveredEventKey.value = null;
}

// Toggle tooltip on click (enables touch device dismissal)
function handleClick(id: string) {
  if (hoveredEventKey.value === id) {
    hoveredEventKey.value = null;
  } else {
    hoveredEventKey.value = id;
  }
}

function handleKeydown(e: KeyboardEvent, id: string) {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    showTooltip(id);
  } else if (e.key === "Escape") {
    hideTooltip();
  }
}
</script>

<template>
  <div
    ref="containerRef"
    class="timeline-markers"
    role="list"
    aria-label="Historical timeline events"
  >
    <div
      v-for="event in visibleEvents"
      :key="event._id"
      class="timeline-markers__marker"
      :class="getEventTypeClass(event.type)"
      :style="{ left: `${getPositionPercent(event.year)}%` }"
      role="listitem"
      :aria-label="getAriaLabel(event)"
      :aria-describedby="hoveredEventKey === event._id ? event._id : undefined"
      tabindex="0"
      @mouseenter="showTooltip(event._id)"
      @mouseleave="hideTooltip"
      @focus="showTooltip(event._id)"
      @blur="hideTooltip"
      @click="handleClick(event._id)"
      @keydown="handleKeydown($event, event._id)"
    >
      <div class="timeline-markers__line" />
      <span
        v-show="event._showLabel || hoveredEventKey === event._id"
        class="timeline-markers__year"
        >{{ event.year }}</span
      >

      <!-- Tooltip -->
      <Transition name="marker-tooltip-fade">
        <div
          v-if="hoveredEventKey === event._id"
          :id="event._id"
          class="timeline-markers__tooltip"
          :class="getTooltipAlignClass(event.year)"
          role="tooltip"
        >
          <span class="timeline-markers__tooltip-type">{{ event.type }}</span>
          <span class="timeline-markers__tooltip-label">{{ event.label }}</span>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.timeline-markers {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  height: 32px;
}

.timeline-markers__marker {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  transform: translateX(-50%);
  cursor: pointer;
}

/* Focus styles for keyboard navigation (combined :focus and :focus-visible) */
.timeline-markers__marker:focus .timeline-markers__line,
.timeline-markers__marker:focus-visible .timeline-markers__line {
  height: 16px;
  outline: 2px solid var(--color-victorian-hunter-600, #2f5a4b);
  outline-offset: 2px;
  border-radius: 2px;
}

.timeline-markers__marker:focus .timeline-markers__year,
.timeline-markers__marker:focus-visible .timeline-markers__year {
  font-weight: 600;
}

/* Hide focus ring on mouse click for browsers supporting :focus-visible */
.timeline-markers__marker:focus:not(:focus-visible) {
  outline: none;
}

.timeline-markers__marker:focus:not(:focus-visible) .timeline-markers__line {
  outline: none;
  height: 12px;
}

.timeline-markers__marker:focus:not(:focus-visible) .timeline-markers__year {
  font-weight: normal;
}

.timeline-markers__line {
  width: 2px;
  height: 12px;
  border-radius: 1px;
  transition: height 150ms ease;
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
  max-width: 200px;
  white-space: normal;
  z-index: 10;
  font-family: Georgia, serif;
}

/* Tooltip edge alignment: left edge */
.timeline-markers__tooltip--align-left {
  left: 0;
  transform: translateX(0);
}

/* Tooltip edge alignment: right edge */
.timeline-markers__tooltip--align-right {
  left: auto;
  right: 0;
  transform: translateX(0);
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

/* Adjust arrow position for left-aligned tooltips */
.timeline-markers__tooltip--align-left::after,
.timeline-markers__tooltip--align-left::before {
  left: 12px;
  transform: translateX(0);
}

/* Adjust arrow position for right-aligned tooltips */
.timeline-markers__tooltip--align-right::after,
.timeline-markers__tooltip--align-right::before {
  left: auto;
  right: 12px;
  transform: translateX(0);
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

/* Left-aligned fade animation */
.timeline-markers__tooltip--align-left.marker-tooltip-fade-enter-from,
.timeline-markers__tooltip--align-left.marker-tooltip-fade-leave-to {
  transform: translateX(0) translateY(4px);
}

/* Right-aligned fade animation */
.timeline-markers__tooltip--align-right.marker-tooltip-fade-enter-from,
.timeline-markers__tooltip--align-right.marker-tooltip-fade-leave-to {
  transform: translateX(0) translateY(4px);
}
</style>
