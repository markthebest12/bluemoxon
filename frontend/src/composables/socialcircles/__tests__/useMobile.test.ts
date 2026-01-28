// frontend/src/composables/socialcircles/__tests__/useMobile.test.ts

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent, nextTick, ref, type Ref } from "vue";

// Mock useMediaQuery from @vueuse/core
const mockIsMobile: Ref<boolean> = ref(false);
const mockIsTablet: Ref<boolean> = ref(false);

vi.mock("@vueuse/core", () => ({
  useMediaQuery: vi.fn((query: string) => {
    if (query === "(max-width: 768px)") {
      return mockIsMobile;
    }
    if (query === "(min-width: 769px) and (max-width: 1024px)") {
      return mockIsTablet;
    }
    return ref(false);
  }),
}));

// Import after mock is set up
import { useMobile } from "../useMobile";

describe("useMobile", () => {
  // Store original window properties
  const originalOntouchstart = Object.getOwnPropertyDescriptor(window, "ontouchstart");
  const originalNavigator = window.navigator;

  beforeEach(() => {
    // Reset mock values
    mockIsMobile.value = false;
    mockIsTablet.value = false;
  });

  afterEach(() => {
    // Restore ontouchstart
    if (originalOntouchstart) {
      Object.defineProperty(window, "ontouchstart", originalOntouchstart);
    } else {
      // Remove the property if it didn't exist originally
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (window as any).ontouchstart;
    }

    // Restore navigator
    Object.defineProperty(window, "navigator", {
      value: originalNavigator,
      configurable: true,
      writable: true,
    });
  });

  it("detects desktop viewport", () => {
    mockIsMobile.value = false;
    mockIsTablet.value = false;

    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;

    expect(vm.isMobile).toBe(false);
    expect(vm.isTablet).toBe(false);

    wrapper.unmount();
  });

  it("detects mobile viewport", () => {
    mockIsMobile.value = true;
    mockIsTablet.value = false;

    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;

    expect(vm.isMobile).toBe(true);

    wrapper.unmount();
  });

  it("detects tablet viewport", () => {
    mockIsMobile.value = false;
    mockIsTablet.value = true;

    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;

    expect(vm.isTablet).toBe(true);

    wrapper.unmount();
  });

  it("toggleFilters switches isFiltersOpen", () => {
    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;

    expect(vm.isFiltersOpen).toBe(false);
    vm.toggleFilters();
    expect(vm.isFiltersOpen).toBe(true);
    vm.toggleFilters();
    expect(vm.isFiltersOpen).toBe(false);

    wrapper.unmount();
  });

  it("openFilters sets isFiltersOpen to true", () => {
    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;

    expect(vm.isFiltersOpen).toBe(false);
    vm.openFilters();
    expect(vm.isFiltersOpen).toBe(true);

    wrapper.unmount();
  });

  it("closeFilters sets isFiltersOpen to false", () => {
    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;

    vm.openFilters();
    expect(vm.isFiltersOpen).toBe(true);
    vm.closeFilters();
    expect(vm.isFiltersOpen).toBe(false);

    wrapper.unmount();
  });

  it("detects touch capability via ontouchstart", async () => {
    // Set ontouchstart before mounting
    Object.defineProperty(window, "ontouchstart", {
      value: () => {},
      configurable: true,
      writable: true,
    });

    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    await nextTick();

    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;
    expect(vm.isTouch).toBe(true);

    wrapper.unmount();
  });

  it("detects touch capability via maxTouchPoints", async () => {
    // Remove ontouchstart to test maxTouchPoints path
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (window as any).ontouchstart;

    // Mock navigator with maxTouchPoints
    Object.defineProperty(window, "navigator", {
      value: { ...originalNavigator, maxTouchPoints: 5 },
      configurable: true,
      writable: true,
    });

    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    await nextTick();

    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;
    expect(vm.isTouch).toBe(true);

    wrapper.unmount();
  });

  it("detects non-touch device", async () => {
    // Remove ontouchstart
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (window as any).ontouchstart;

    // Mock navigator with no touch points
    Object.defineProperty(window, "navigator", {
      value: { ...originalNavigator, maxTouchPoints: 0 },
      configurable: true,
      writable: true,
    });

    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    await nextTick();

    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;
    expect(vm.isTouch).toBe(false);

    wrapper.unmount();
  });

  it("responds to media query changes", async () => {
    mockIsMobile.value = false;

    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;

    expect(vm.isMobile).toBe(false);

    // Simulate viewport change
    mockIsMobile.value = true;
    await nextTick();

    expect(vm.isMobile).toBe(true);

    wrapper.unmount();
  });

  it("returns all expected properties", () => {
    const TestComponent = defineComponent({
      setup() {
        const result = useMobile();
        // Verify all properties exist
        expect(result).toHaveProperty("isMobile");
        expect(result).toHaveProperty("isTablet");
        expect(result).toHaveProperty("isTouch");
        expect(result).toHaveProperty("isFiltersOpen");
        expect(result).toHaveProperty("openFilters");
        expect(result).toHaveProperty("closeFilters");
        expect(result).toHaveProperty("toggleFilters");

        // Verify types
        expect(typeof result.openFilters).toBe("function");
        expect(typeof result.closeFilters).toBe("function");
        expect(typeof result.toggleFilters).toBe("function");

        return result;
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    wrapper.unmount();
  });

  it("multiple calls to openFilters remain idempotent", () => {
    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;

    vm.openFilters();
    vm.openFilters();
    vm.openFilters();

    expect(vm.isFiltersOpen).toBe(true);

    wrapper.unmount();
  });

  it("multiple calls to closeFilters remain idempotent", () => {
    const TestComponent = defineComponent({
      setup() {
        return useMobile();
      },
      template: "<div />",
    });

    const wrapper = mount(TestComponent);
    const vm = wrapper.vm as unknown as ReturnType<typeof useMobile>;

    vm.openFilters();
    vm.closeFilters();
    vm.closeFilters();
    vm.closeFilters();

    expect(vm.isFiltersOpen).toBe(false);

    wrapper.unmount();
  });
});
