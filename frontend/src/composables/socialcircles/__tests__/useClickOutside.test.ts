// frontend/src/composables/socialcircles/__tests__/useClickOutside.test.ts
import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent, ref, nextTick } from "vue";
import { useClickOutside } from "../useClickOutside";

describe("useClickOutside", () => {
  it("should call callback when clicking outside the element", async () => {
    const callback = vi.fn();
    const TestComponent = defineComponent({
      setup() {
        const elementRef = ref<HTMLElement | null>(null);
        useClickOutside(elementRef, callback);
        return { elementRef };
      },
      template: `
        <div>
          <div ref="elementRef" data-testid="inside">Inside</div>
          <div data-testid="outside">Outside</div>
        </div>
      `,
    });

    const wrapper = mount(TestComponent, { attachTo: document.body });
    await nextTick();

    // Click outside the element
    const outsideEl = wrapper.find('[data-testid="outside"]');
    await outsideEl.trigger("click");

    // Also dispatch on document to simulate real behavior
    document.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(callback).toHaveBeenCalled();

    wrapper.unmount();
  });

  it("should NOT call callback when clicking inside the element", async () => {
    const callback = vi.fn();
    const TestComponent = defineComponent({
      setup() {
        const elementRef = ref<HTMLElement | null>(null);
        useClickOutside(elementRef, callback);
        return { elementRef };
      },
      template: `
        <div>
          <div ref="elementRef" data-testid="inside">
            <button data-testid="inner-button">Click me</button>
          </div>
          <div data-testid="outside">Outside</div>
        </div>
      `,
    });

    const wrapper = mount(TestComponent, { attachTo: document.body });
    await nextTick();

    // Click inside the element
    const insideEl = wrapper.find('[data-testid="inner-button"]');
    (insideEl.element as HTMLElement).click();

    expect(callback).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("should remove listener on unmount", async () => {
    const callback = vi.fn();
    const TestComponent = defineComponent({
      setup() {
        const elementRef = ref<HTMLElement | null>(null);
        useClickOutside(elementRef, callback);
        return { elementRef };
      },
      template: '<div ref="elementRef">Test</div>',
    });

    const wrapper = mount(TestComponent, { attachTo: document.body });
    await nextTick();

    // Unmount the component
    wrapper.unmount();

    // Click should not trigger callback after unmount
    document.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(callback).not.toHaveBeenCalled();
  });

  it("should not call callback if ref is null", async () => {
    const callback = vi.fn();
    const TestComponent = defineComponent({
      setup() {
        const elementRef = ref<HTMLElement | null>(null);
        // Don't assign ref to any element
        useClickOutside(elementRef, callback);
        return {};
      },
      template: "<div>No ref assigned</div>",
    });

    const wrapper = mount(TestComponent, { attachTo: document.body });
    await nextTick();

    // Click anywhere
    document.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    // Should not crash, but also should not call callback since ref is null
    expect(callback).not.toHaveBeenCalled();

    wrapper.unmount();
  });
});
