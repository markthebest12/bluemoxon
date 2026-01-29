// frontend/src/composables/socialcircles/__tests__/useEscapeKey.test.ts

import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent } from "vue";
import { useEscapeKey } from "../useEscapeKey";

describe("useEscapeKey", () => {
  it("should call callback when Escape is pressed", () => {
    const callback = vi.fn();
    const TestComponent = defineComponent({
      setup() {
        useEscapeKey(callback);
        return {};
      },
      template: "<div />",
    });

    mount(TestComponent);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("should not call callback for other keys", () => {
    const callback = vi.fn();
    const TestComponent = defineComponent({
      setup() {
        useEscapeKey(callback);
        return {};
      },
      template: "<div />",
    });

    mount(TestComponent);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    expect(callback).not.toHaveBeenCalled();

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
    expect(callback).not.toHaveBeenCalled();
  });

  it("should remove listener on unmount", () => {
    const callback = vi.fn();
    const TestComponent = defineComponent({
      setup() {
        useEscapeKey(callback);
        return {};
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);

    // Callback should be called before unmount
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(callback).toHaveBeenCalledTimes(1);

    // Unmount the component
    wrapper.unmount();

    // Callback should not be called after unmount
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(callback).toHaveBeenCalledTimes(1);
  });
});
