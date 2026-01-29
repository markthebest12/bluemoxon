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
import type { HistoricalEvent } from "@/types/socialCircles";
import { VICTORIAN_EVENTS } from "@/constants/socialCircles";

interface Props {
  minYear: number;
  maxYear: number;
  events?: readonly HistoricalEvent[];
}

const props = withDefaults(defineProps<Props>(), {
  events: () => VICTORIAN_EVENTS,
});

// Track which marker is being hovered or focused (by key, not object reference)
const hoveredEventKey = ref<string | null>(null);

function getEventKey(event: HistoricalEvent): string {
  return `${event.year}-${event.label}`;
}

// Filter events to only those within the visible range
const visibleEvents = computed(() => {
  if (props.maxYear < props.minYear) return [];
  return props.events.filter((event) => event.year >= props.minYear && event.year <= props.maxYear);
});

// Calculate horizontal position percentage for an event
function getPositionPercent(year: number): number {
  const range = props.maxYear - props.minYear;
  if (range <= 0) return 0;
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

// Generate unique tooltip ID for aria-describedby linkage
function getTooltipId(event: HistoricalEvent): string {
  const slugLabel = event.label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
  return `tooltip-${event.year}-${slugLabel}`;
}

function showTooltip(event: HistoricalEvent) {
  hoveredEventKey.value = getEventKey(event);
}

function hideTooltip() {
  hoveredEventKey.value = null;
}

function handleKeydown(e: KeyboardEvent, event: HistoricalEvent) {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    showTooltip(event);
  } else if (e.key === "Escape") {
    hideTooltip();
  }
}
</script>

<template>
  <div class="timeline-markers" role="list" aria-label="Historical timeline events">
    <div
      v-for="event in visibleEvents"
      :key="`${event.year}-${event.label}`"
      class="timeline-markers__marker"
      :class="getEventTypeClass(event.type)"
      :style="{ left: `${getPositionPercent(event.year)}%` }"
      role="listitem"
      :aria-label="getAriaLabel(event)"
      :aria-describedby="hoveredEventKey === getEventKey(event) ? getTooltipId(event) : undefined"
      tabindex="0"
      @mouseenter="showTooltip(event)"
      @mouseleave="hideTooltip"
      @focus="showTooltip(event)"
      @blur="hideTooltip"
      @keydown="handleKeydown($event, event)"
    >
      <div class="timeline-markers__line" />
      <span class="timeline-markers__year">{{ event.year }}</span>

      <!-- Tooltip -->
      <Transition name="marker-tooltip-fade">
        <div
          v-if="hoveredEventKey === getEventKey(event)"
          :id="getTooltipId(event)"
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
  top: 100%;
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
