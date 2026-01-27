<script setup lang="ts">
/**
 * TimelineSlider - Timeline control for temporal filtering.
 * Supports point mode (single year) and range mode (date span).
 */

import { ref, computed, watch } from "vue";

interface Props {
  minYear?: number;
  maxYear?: number;
  currentYear?: number;
  mode?: "point" | "range";
  isPlaying?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  minYear: 1780,
  maxYear: 1920,
  currentYear: 1850,
  mode: "point",
  isPlaying: false,
});

const emit = defineEmits<{
  "year-change": [year: number];
  "mode-change": [mode: "point" | "range"];
  play: [];
  pause: [];
}>();

const localYear = ref(props.currentYear);

// Sync localYear when parent's currentYear prop changes
watch(
  () => props.currentYear,
  (newYear) => {
    localYear.value = newYear;
  }
);

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

    <div class="timeline-slider__track">
      <span class="timeline-slider__label">{{ minYear }}</span>
      <input
        v-model.number="localYear"
        type="range"
        :min="minYear"
        :max="maxYear"
        class="timeline-slider__input"
        aria-label="Timeline year selector"
        @input="emit('year-change', localYear)"
      />
      <span class="timeline-slider__label">{{ maxYear }}</span>
    </div>

    <div class="timeline-slider__current">
      {{ yearLabel }}
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
}

.timeline-slider__input {
  flex: 1;
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
  margin-top: 0.5rem;
}
</style>
