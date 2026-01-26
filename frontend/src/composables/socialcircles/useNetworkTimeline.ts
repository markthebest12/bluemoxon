/**
 * useNetworkTimeline - Manages timeline state and playback.
 */

import { ref, computed, readonly, onUnmounted } from "vue";
import type { TimelineState, TimelineMode, PlaybackSpeed } from "@/types/socialCircles";
import { DEFAULT_TIMELINE_STATE } from "@/types/socialCircles";

export function useNetworkTimeline() {
  const timeline = ref<TimelineState>({ ...DEFAULT_TIMELINE_STATE });
  let playbackInterval: ReturnType<typeof setInterval> | null = null;

  // Computed
  const yearLabel = computed(() => {
    const t = timeline.value;
    if (t.mode === "point") {
      return `${t.currentYear}`;
    }
    return `${t.rangeStart || t.minYear} – ${t.rangeEnd || t.currentYear}`;
  });

  const progress = computed(() => {
    const t = timeline.value;
    return ((t.currentYear - t.minYear) / (t.maxYear - t.minYear)) * 100;
  });

  // Actions
  function setCurrentYear(year: number) {
    timeline.value.currentYear = Math.max(
      timeline.value.minYear,
      Math.min(timeline.value.maxYear, year)
    );
  }

  function setMode(mode: TimelineMode) {
    timeline.value.mode = mode;
    if (mode === "range") {
      timeline.value.rangeStart = timeline.value.minYear;
      timeline.value.rangeEnd = timeline.value.currentYear;
    }
  }

  function setRange(start: number, end: number) {
    timeline.value.rangeStart = start;
    timeline.value.rangeEnd = end;
  }

  function setPlaybackSpeed(speed: PlaybackSpeed) {
    timeline.value.playbackSpeed = speed;
    if (timeline.value.isPlaying) {
      pause();
      play();
    }
  }

  function setDateRange(minYear: number, maxYear: number) {
    timeline.value.minYear = minYear;
    timeline.value.maxYear = maxYear;
    if (timeline.value.currentYear < minYear) {
      timeline.value.currentYear = minYear;
    }
    if (timeline.value.currentYear > maxYear) {
      timeline.value.currentYear = maxYear;
    }
  }

  function play() {
    if (playbackInterval) return;

    timeline.value.isPlaying = true;
    const intervalMs = 1000 / timeline.value.playbackSpeed;

    playbackInterval = setInterval(() => {
      const t = timeline.value;
      if (t.currentYear >= t.maxYear) {
        pause();
        timeline.value.currentYear = t.minYear;
      } else {
        timeline.value.currentYear++;
      }
    }, intervalMs);
  }

  function pause() {
    timeline.value.isPlaying = false;
    if (playbackInterval) {
      clearInterval(playbackInterval);
      playbackInterval = null;
    }
  }

  function togglePlayback() {
    if (timeline.value.isPlaying) {
      pause();
    } else {
      play();
    }
  }

  function stepForward() {
    setCurrentYear(timeline.value.currentYear + 1);
  }

  function stepBackward() {
    setCurrentYear(timeline.value.currentYear - 1);
  }

  function reset() {
    pause();
    timeline.value = { ...DEFAULT_TIMELINE_STATE };
  }

  // Cleanup
  onUnmounted(() => {
    pause();
  });

  return {
    timeline: readonly(timeline),
    yearLabel,
    progress,
    setCurrentYear,
    setMode,
    setRange,
    setPlaybackSpeed,
    setDateRange,
    play,
    pause,
    togglePlayback,
    stepForward,
    stepBackward,
    reset,
  };
}
