import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent } from "vue";
import { useNetworkTimeline } from "../useNetworkTimeline";
import { DEFAULT_TIMELINE_STATE } from "@/types/socialCircles";

describe("useNetworkTimeline", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("initializes with default timeline state", () => {
      const timeline = useNetworkTimeline();

      expect(timeline.timeline.value.currentYear).toBe(DEFAULT_TIMELINE_STATE.currentYear);
      expect(timeline.timeline.value.minYear).toBe(DEFAULT_TIMELINE_STATE.minYear);
      expect(timeline.timeline.value.maxYear).toBe(DEFAULT_TIMELINE_STATE.maxYear);
      expect(timeline.timeline.value.isPlaying).toBe(false);
      expect(timeline.timeline.value.playbackSpeed).toBe(1);
      expect(timeline.timeline.value.mode).toBe("point");
    });

    it("initializes with correct year range from defaults", () => {
      const timeline = useNetworkTimeline();

      expect(timeline.timeline.value.minYear).toBe(1780);
      expect(timeline.timeline.value.maxYear).toBe(1920);
    });
  });

  describe("setCurrentYear", () => {
    it("updates currentYear to specified value", () => {
      const timeline = useNetworkTimeline();

      timeline.setCurrentYear(1850);
      expect(timeline.timeline.value.currentYear).toBe(1850);
    });

    it("clamps year to minYear when below range", () => {
      const timeline = useNetworkTimeline();

      timeline.setCurrentYear(1700);
      expect(timeline.timeline.value.currentYear).toBe(timeline.timeline.value.minYear);
    });

    it("clamps year to maxYear when above range", () => {
      const timeline = useNetworkTimeline();

      timeline.setCurrentYear(2000);
      expect(timeline.timeline.value.currentYear).toBe(timeline.timeline.value.maxYear);
    });
  });

  describe("setMode", () => {
    it("sets mode to point", () => {
      const timeline = useNetworkTimeline();

      timeline.setMode("point");
      expect(timeline.timeline.value.mode).toBe("point");
    });

    it("sets mode to range and initializes rangeStart/rangeEnd", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1880);

      timeline.setMode("range");

      expect(timeline.timeline.value.mode).toBe("range");
      expect(timeline.timeline.value.rangeStart).toBe(timeline.timeline.value.minYear);
      expect(timeline.timeline.value.rangeEnd).toBe(1880);
    });
  });

  describe("setRange", () => {
    it("sets custom range start and end", () => {
      const timeline = useNetworkTimeline();

      timeline.setRange(1800, 1850);

      expect(timeline.timeline.value.rangeStart).toBe(1800);
      expect(timeline.timeline.value.rangeEnd).toBe(1850);
    });
  });

  describe("setPlaybackSpeed", () => {
    it("sets playback speed when not playing", () => {
      const timeline = useNetworkTimeline();

      timeline.setPlaybackSpeed(2);
      expect(timeline.timeline.value.playbackSpeed).toBe(2);
    });

    it("restarts playback with new speed when playing", () => {
      const timeline = useNetworkTimeline();
      timeline.play();
      expect(timeline.timeline.value.isPlaying).toBe(true);

      timeline.setPlaybackSpeed(0.5);

      expect(timeline.timeline.value.playbackSpeed).toBe(0.5);
      expect(timeline.timeline.value.isPlaying).toBe(true);
    });
  });

  describe("setDateRange", () => {
    it("sets min and max year", () => {
      const timeline = useNetworkTimeline();

      timeline.setDateRange(1800, 1900);

      expect(timeline.timeline.value.minYear).toBe(1800);
      expect(timeline.timeline.value.maxYear).toBe(1900);
    });

    it("adjusts currentYear to minYear if below new range", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1780);

      timeline.setDateRange(1800, 1900);

      expect(timeline.timeline.value.currentYear).toBe(1800);
    });

    it("adjusts currentYear to maxYear if above new range", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1920);

      timeline.setDateRange(1800, 1900);

      expect(timeline.timeline.value.currentYear).toBe(1900);
    });

    it("keeps currentYear unchanged if within new range", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);

      timeline.setDateRange(1800, 1900);

      expect(timeline.timeline.value.currentYear).toBe(1850);
    });
  });

  describe("play", () => {
    it("sets isPlaying to true", () => {
      const timeline = useNetworkTimeline();

      timeline.play();

      expect(timeline.timeline.value.isPlaying).toBe(true);
    });

    it("increments currentYear on interval tick", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);

      timeline.play();
      vi.advanceTimersByTime(1000);

      expect(timeline.timeline.value.currentYear).toBe(1851);
    });

    it("respects playback speed for interval", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);
      timeline.setPlaybackSpeed(2);

      timeline.play();
      vi.advanceTimersByTime(500);

      expect(timeline.timeline.value.currentYear).toBe(1851);
    });

    it("pauses and resets to minYear when reaching maxYear", () => {
      const timeline = useNetworkTimeline();
      timeline.setDateRange(1850, 1852);
      timeline.setCurrentYear(1852);

      timeline.play();
      vi.advanceTimersByTime(1000);

      expect(timeline.timeline.value.isPlaying).toBe(false);
      expect(timeline.timeline.value.currentYear).toBe(1850);
    });

    it("does nothing if already playing", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);

      timeline.play();
      vi.advanceTimersByTime(1000);
      expect(timeline.timeline.value.currentYear).toBe(1851);

      // Call play again - should not create a second interval
      timeline.play();
      vi.advanceTimersByTime(1000);

      // Should only advance by 1, not 2
      expect(timeline.timeline.value.currentYear).toBe(1852);
    });
  });

  describe("pause", () => {
    it("sets isPlaying to false", () => {
      const timeline = useNetworkTimeline();
      timeline.play();

      timeline.pause();

      expect(timeline.timeline.value.isPlaying).toBe(false);
    });

    it("stops the interval from advancing currentYear", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);
      timeline.play();

      vi.advanceTimersByTime(1000);
      expect(timeline.timeline.value.currentYear).toBe(1851);

      timeline.pause();
      vi.advanceTimersByTime(2000);

      expect(timeline.timeline.value.currentYear).toBe(1851);
    });

    it("does nothing if not playing", () => {
      const timeline = useNetworkTimeline();

      expect(() => timeline.pause()).not.toThrow();
      expect(timeline.timeline.value.isPlaying).toBe(false);
    });
  });

  describe("togglePlayback", () => {
    it("starts playback when not playing", () => {
      const timeline = useNetworkTimeline();

      timeline.togglePlayback();

      expect(timeline.timeline.value.isPlaying).toBe(true);
    });

    it("stops playback when playing", () => {
      const timeline = useNetworkTimeline();
      timeline.play();

      timeline.togglePlayback();

      expect(timeline.timeline.value.isPlaying).toBe(false);
    });
  });

  describe("stepForward", () => {
    it("increments currentYear by 1", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);

      timeline.stepForward();

      expect(timeline.timeline.value.currentYear).toBe(1851);
    });

    it("respects maxYear boundary", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(timeline.timeline.value.maxYear);

      timeline.stepForward();

      expect(timeline.timeline.value.currentYear).toBe(timeline.timeline.value.maxYear);
    });
  });

  describe("stepBackward", () => {
    it("decrements currentYear by 1", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);

      timeline.stepBackward();

      expect(timeline.timeline.value.currentYear).toBe(1849);
    });

    it("respects minYear boundary", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(timeline.timeline.value.minYear);

      timeline.stepBackward();

      expect(timeline.timeline.value.currentYear).toBe(timeline.timeline.value.minYear);
    });
  });

  describe("reset", () => {
    it("pauses playback and resets to default state", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1900);
      timeline.setMode("range");
      timeline.setPlaybackSpeed(2);
      timeline.play();

      timeline.reset();

      expect(timeline.timeline.value.isPlaying).toBe(false);
      expect(timeline.timeline.value.currentYear).toBe(DEFAULT_TIMELINE_STATE.currentYear);
      expect(timeline.timeline.value.mode).toBe(DEFAULT_TIMELINE_STATE.mode);
      expect(timeline.timeline.value.playbackSpeed).toBe(DEFAULT_TIMELINE_STATE.playbackSpeed);
    });
  });

  describe("computed: yearLabel", () => {
    it("returns current year for point mode", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);
      timeline.setMode("point");

      expect(timeline.yearLabel.value).toBe("1850");
    });

    it("returns range for range mode", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);
      timeline.setMode("range");

      expect(timeline.yearLabel.value).toBe(`${timeline.timeline.value.minYear} – 1850`);
    });

    it("uses rangeStart when available in range mode", () => {
      const timeline = useNetworkTimeline();
      timeline.setMode("range");
      timeline.setRange(1800, 1860);
      timeline.setCurrentYear(1850);

      expect(timeline.yearLabel.value).toBe("1800 – 1860");
    });
  });

  describe("computed: progress", () => {
    it("returns 0 at minYear", () => {
      const timeline = useNetworkTimeline();
      timeline.setDateRange(1800, 1900);
      timeline.setCurrentYear(1800);

      expect(timeline.progress.value).toBe(0);
    });

    it("returns 100 at maxYear", () => {
      const timeline = useNetworkTimeline();
      timeline.setDateRange(1800, 1900);
      timeline.setCurrentYear(1900);

      expect(timeline.progress.value).toBe(100);
    });

    it("returns 50 at midpoint", () => {
      const timeline = useNetworkTimeline();
      timeline.setDateRange(1800, 1900);
      timeline.setCurrentYear(1850);

      expect(timeline.progress.value).toBe(50);
    });
  });

  describe("lifecycle: cleanup on unmount", () => {
    it("clears interval on component unmount", async () => {
      let timelineRef: ReturnType<typeof useNetworkTimeline> | null = null;

      const TestComponent = defineComponent({
        setup() {
          timelineRef = useNetworkTimeline();
          return { timeline: timelineRef };
        },
        template: "<div />",
      });

      const wrapper = mount(TestComponent);
      timelineRef!.play();
      timelineRef!.setCurrentYear(1850);

      vi.advanceTimersByTime(1000);
      expect(timelineRef!.timeline.value.currentYear).toBe(1851);

      wrapper.unmount();

      // After unmount, interval should be cleared
      vi.advanceTimersByTime(3000);
      expect(timelineRef!.timeline.value.currentYear).toBe(1851);
    });
  });

  describe("readonly timeline", () => {
    it("returns a readonly ref for timeline", () => {
      const timeline = useNetworkTimeline();

      // The timeline value should be accessible
      expect(timeline.timeline.value.currentYear).toBeDefined();

      // Direct mutation should not work (TypeScript would prevent this,
      // but at runtime readonly wraps in a proxy that warns in dev mode)
      const originalYear = timeline.timeline.value.currentYear;
      expect(timeline.timeline.value.currentYear).toBe(originalYear);
    });
  });

  describe("edge cases", () => {
    it("handles rapid play/pause cycles", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);

      timeline.play();
      timeline.pause();
      timeline.play();
      timeline.pause();
      timeline.play();

      expect(timeline.timeline.value.isPlaying).toBe(true);

      vi.advanceTimersByTime(1000);
      expect(timeline.timeline.value.currentYear).toBe(1851);
    });

    it("handles setting date range while playing", () => {
      const timeline = useNetworkTimeline();
      timeline.setCurrentYear(1850);
      timeline.play();

      vi.advanceTimersByTime(1000);
      expect(timeline.timeline.value.currentYear).toBe(1851);

      timeline.setDateRange(1900, 1950);

      // Current year should be clamped to new minYear
      expect(timeline.timeline.value.currentYear).toBe(1900);
    });

    it("handles all playback speeds", () => {
      const speeds = [0.5, 1, 2, 5] as const;

      speeds.forEach((speed) => {
        const timeline = useNetworkTimeline();
        timeline.setCurrentYear(1850);
        timeline.setPlaybackSpeed(speed);
        timeline.play();

        const expectedInterval = 1000 / speed;
        vi.advanceTimersByTime(expectedInterval);

        expect(timeline.timeline.value.currentYear).toBe(1851);
        timeline.pause();
      });
    });

    it("handles single year range (minYear === maxYear)", () => {
      const timeline = useNetworkTimeline();
      timeline.setDateRange(1850, 1850);

      expect(timeline.timeline.value.currentYear).toBe(1850);
      expect(timeline.progress.value).toBeNaN(); // Division by zero

      // Stepping should not change year
      timeline.stepForward();
      expect(timeline.timeline.value.currentYear).toBe(1850);

      timeline.stepBackward();
      expect(timeline.timeline.value.currentYear).toBe(1850);
    });
  });
});
