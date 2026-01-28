import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import TimelineSlider from "../TimelineSlider.vue";

describe("TimelineSlider", () => {
  describe("v-model support", () => {
    it("should use modelValue when provided", () => {
      const wrapper = mount(TimelineSlider, {
        props: { modelValue: 1860, minYear: 1800, maxYear: 1900 },
      });

      const slider = wrapper.find('input[type="range"]');
      expect((slider.element as HTMLInputElement).value).toBe("1860");
    });

    it("should emit update:modelValue on year change", async () => {
      const wrapper = mount(TimelineSlider, {
        props: { modelValue: 1850, minYear: 1800, maxYear: 1900 },
      });

      const slider = wrapper.find('input[type="range"]');
      await slider.setValue(1875);

      expect(wrapper.emitted("update:modelValue")).toBeTruthy();
      expect(wrapper.emitted("update:modelValue")![0]).toEqual([1875]);
    });

    it("should also emit year-change for backwards compatibility", async () => {
      const wrapper = mount(TimelineSlider, {
        props: { modelValue: 1850, minYear: 1800, maxYear: 1900 },
      });

      const slider = wrapper.find('input[type="range"]');
      await slider.setValue(1875);

      expect(wrapper.emitted("year-change")).toBeTruthy();
      expect(wrapper.emitted("year-change")![0]).toEqual([1875]);
    });

    it("should update when modelValue prop changes", async () => {
      const wrapper = mount(TimelineSlider, {
        props: { modelValue: 1850, minYear: 1800, maxYear: 1900 },
      });

      await wrapper.setProps({ modelValue: 1880 });

      const slider = wrapper.find('input[type="range"]');
      expect((slider.element as HTMLInputElement).value).toBe("1880");
    });
  });

  describe("backwards compatibility", () => {
    it("should support legacy currentYear prop", () => {
      const wrapper = mount(TimelineSlider, {
        props: { currentYear: 1870, minYear: 1800, maxYear: 1900 },
      });

      const slider = wrapper.find('input[type="range"]');
      expect((slider.element as HTMLInputElement).value).toBe("1870");
    });

    it("should prefer modelValue over currentYear when both provided", () => {
      const wrapper = mount(TimelineSlider, {
        props: {
          modelValue: 1860,
          currentYear: 1870,
          minYear: 1800,
          maxYear: 1900,
        },
      });

      const slider = wrapper.find('input[type="range"]');
      expect((slider.element as HTMLInputElement).value).toBe("1860");
    });

    it("should fall back to minYear when no year props provided", () => {
      const wrapper = mount(TimelineSlider, {
        props: { minYear: 1820, maxYear: 1900 },
      });

      const slider = wrapper.find('input[type="range"]');
      expect((slider.element as HTMLInputElement).value).toBe("1820");
    });
  });

  describe("play/pause", () => {
    it("should emit play when clicked while not playing", async () => {
      const wrapper = mount(TimelineSlider, {
        props: { modelValue: 1850, minYear: 1800, maxYear: 1900, isPlaying: false },
      });

      const playButton = wrapper.find(".timeline-slider__play");
      await playButton.trigger("click");

      expect(wrapper.emitted("play")).toBeTruthy();
    });

    it("should emit pause when clicked while playing", async () => {
      const wrapper = mount(TimelineSlider, {
        props: { modelValue: 1850, minYear: 1800, maxYear: 1900, isPlaying: true },
      });

      const playButton = wrapper.find(".timeline-slider__play");
      await playButton.trigger("click");

      expect(wrapper.emitted("pause")).toBeTruthy();
    });
  });

  describe("mode toggle", () => {
    it("should emit mode-change when switching modes", async () => {
      const wrapper = mount(TimelineSlider, {
        props: { modelValue: 1850, minYear: 1800, maxYear: 1900, mode: "point" },
      });

      const modeButtons = wrapper.findAll(".timeline-slider__mode-btn");
      await modeButtons[1].trigger("click"); // Click "Range" button

      expect(wrapper.emitted("mode-change")).toBeTruthy();
      expect(wrapper.emitted("mode-change")![0]).toEqual(["range"]);
    });
  });
});
