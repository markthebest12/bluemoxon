<script setup lang="ts">
/**
 * TimelineSlider - Timeline control for temporal filtering.
 * Supports point mode (single year) and range mode (date span).
 *
 * Supports v-model pattern via modelValue/update:modelValue.
 * Also maintains backwards compatibility with currentYear prop.
 */

import { ref, computed, watch } from "vue";
import TimelineMarkers from "@/components/socialcircles/TimelineMarkers.vue";

// Module-level flag to prevent warning spam
let hasWarned = false;

interface Props {
  minYear?: number;
  maxYear?: number;
  /** v-model binding for year value */
  modelValue?: number;
  /** @deprecated Use modelValue instead. Kept for backwards compatibility. */
  currentYear?: number;
  mode?: "point" | "range";
  isPlaying?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  minYear: 1780,
  maxYear: 1920,
  modelValue: undefined,
  currentYear: undefined,
  mode: "point",
  isPlaying: false,
});

// Immediate deprecation check in setup body
if (
  import.meta.env.DEV &&
  !hasWarned &&
  props.currentYear !== undefined &&
  props.modelValue === undefined
) {
  console.warn(
    "TimelineSlider: 'currentYear' prop is deprecated. Use v-model instead: <TimelineSlider v-model=\"year\" />"
  );
  hasWarned = true;
}

const emit = defineEmits<{
  /** v-model update event */
  "update:modelValue": [year: number];
  /** @deprecated Use update:modelValue instead */
  "year-change": [year: number];
  "mode-change": [mode: "point" | "range"];
  play: [];
  pause: [];
}>();

// Computed for the effective year value (supports both v-model and legacy prop)
const effectiveYear = computed(() => props.modelValue ?? props.currentYear ?? props.minYear);

const localYear = ref(effectiveYear.value);

// Sync localYear when parent's year prop changes (supports both patterns)
watch(effectiveYear, (newYear) => {
  localYear.value = newYear;
});

// Emit both new and legacy events for backwards compatibility
function updateYear(year: number) {
  emit("update:modelValue", year);
  emit("year-change", year);
}

const sliderPercent = computed(() => {
  const range = props.maxYear - props.minYear;
  if (range === 0) return 0;
  return ((localYear.value - props.minYear) / range) * 100;
});

const showMinLabel = computed(() => sliderPercent.value > 10);
const showMaxLabel = computed(() => sliderPercent.value < 90);

const yearLabel = computed(() => {
  return props.mode === "point" ? `${localYear.value}` : `${props.minYear} - ${localYear.value}`;
});

function handlePlay() {
  if (props.isPlaying) {
    emit("pause");
  } else {
    emit("play");
  }
}
</script>

<template>
  <div class="timeline-slider">
    <div class="timeline-slider__controls">
      <div class="timeline-slider__mode">
        <button
          :class="['timeline-slider__mode-btn', { active: mode === 'point' }]"
          @click="emit('mode-change', 'point')"
        >
          Point
        </button>
        <button
          :class="['timeline-slider__mode-btn', { active: mode === 'range' }]"
          @click="emit('mode-change', 'range')"
        >
          Range
        </button>
      </div>

      <button class="timeline-slider__play" @click="handlePlay">
        {{ isPlaying ? "⏸" : "▶" }}
      </button>
    </div>

    <!-- Year display moved ABOVE track to avoid overlapping with marker year labels below -->
    <div class="timeline-slider__current">
      {{ yearLabel }}
    </div>

    <div class="timeline-slider__track">
      <span v-show="showMinLabel" class="timeline-slider__label">{{ minYear }}</span>
      <div class="timeline-slider__input-wrapper">
        <input
          v-model.number="localYear"
          type="range"
          :min="minYear"
          :max="maxYear"
          class="timeline-slider__input"
          aria-label="Timeline year selector"
          @change="updateYear(localYear)"
        />
        <TimelineMarkers :min-year="minYear" :max-year="maxYear" :slider-year="localYear" />
      </div>
      <span v-show="showMaxLabel" class="timeline-slider__label">{{ maxYear }}</span>
    </div>
  </div>
</template>

<style scoped>
.timeline-slider {
  background: var(--color-victorian-paper-white, #fdfcfa);
  border-top: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  padding: 1rem 1.5rem;
}

.timeline-slider__controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.timeline-slider__mode {
  display: flex;
  gap: 0.5rem;
}

.timeline-slider__mode-btn {
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  border: 1px solid var(--color-victorian-paper-aged);
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
}

.timeline-slider__mode-btn.active {
  background: var(--color-victorian-hunter-600);
  color: white;
  border-color: var(--color-victorian-hunter-600);
}

.timeline-slider__play {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--color-victorian-gold);
  background: var(--color-victorian-gold-light);
  cursor: pointer;
  font-size: 0.875rem;
}

.timeline-slider__track {
  display: flex;
  align-items: center;
  gap: 1rem;
  /* Reserve space for TimelineMarkers year labels positioned below the slider.
     Markers container is 40px tall + 4px top offset = 44px needed.
     Extra height ensures hover animation (line grows 12px→16px) keeps labels visible. */
  padding-bottom: 44px;
}

.timeline-slider__input-wrapper {
  position: relative;
  flex: 1;
}

.timeline-slider__input {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  background: var(--color-victorian-paper-aged);
  border-radius: 2px;
}

.timeline-slider__input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-victorian-hunter-600);
  cursor: pointer;
}

.timeline-slider__label {
  font-size: 0.75rem;
  color: var(--color-victorian-ink-muted);
  min-width: 40px;
}

.timeline-slider__current {
  text-align: center;
  font-weight: 600;
  color: var(--color-victorian-hunter-700);
  margin-bottom: 0.5rem;
}
</style>
