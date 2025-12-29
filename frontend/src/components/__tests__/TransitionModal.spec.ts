import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import TransitionModal from "../TransitionModal.vue";

describe("TransitionModal", () => {
  beforeEach(() => {
    // Reset body overflow before each test
    document.body.style.overflow = "";
  });

  afterEach(() => {
    // Clean up after each test
    document.body.style.overflow = "";
  });

  it("locks scroll when opened", async () => {
    const wrapper = mount(TransitionModal, {
      props: { visible: true },
      global: {
        stubs: {
          Teleport: true,
          Transition: false,
        },
      },
    });
    expect(document.body.style.overflow).toBe("hidden");
    wrapper.unmount();
  });

  it("unlocks scroll when closed", async () => {
    const wrapper = mount(TransitionModal, {
      props: { visible: true },
      global: {
        stubs: {
          Teleport: true,
          Transition: false,
        },
      },
    });
    expect(document.body.style.overflow).toBe("hidden");

    await wrapper.setProps({ visible: false });
    expect(document.body.style.overflow).toBe("");
    wrapper.unmount();
  });

  it("keeps scroll locked when nested modal closes but parent open", async () => {
    const parent = mount(TransitionModal, {
      props: { visible: true },
      global: {
        stubs: {
          Teleport: true,
          Transition: false,
        },
      },
    });
    expect(document.body.style.overflow).toBe("hidden");

    const child = mount(TransitionModal, {
      props: { visible: true },
      global: {
        stubs: {
          Teleport: true,
          Transition: false,
        },
      },
    });
    expect(document.body.style.overflow).toBe("hidden");

    // Close child modal
    await child.setProps({ visible: false });
    // Parent still open, scroll should stay locked
    expect(document.body.style.overflow).toBe("hidden");

    // Close parent
    await parent.setProps({ visible: false });
    expect(document.body.style.overflow).toBe("");

    child.unmount();
    parent.unmount();
  });

  it("emits backdrop-click when clicking backdrop", async () => {
    const wrapper = mount(TransitionModal, {
      props: { visible: true },
      global: {
        stubs: {
          Teleport: true,
          Transition: false,
        },
      },
    });

    // Find the backdrop div and trigger click
    const backdrop = wrapper.find(".fixed");
    await backdrop.trigger("click");

    expect(wrapper.emitted("backdrop-click")).toBeTruthy();
    wrapper.unmount();
  });

  it("cleans up on unmount while visible", () => {
    const wrapper = mount(TransitionModal, {
      props: { visible: true },
      global: {
        stubs: {
          Teleport: true,
          Transition: false,
        },
      },
    });
    expect(document.body.style.overflow).toBe("hidden");

    wrapper.unmount();
    expect(document.body.style.overflow).toBe("");
  });

  it("handles rapid open/close without race conditions", async () => {
    const wrapper = mount(TransitionModal, {
      props: { visible: false },
      global: {
        stubs: {
          Teleport: true,
          Transition: false,
        },
      },
    });

    // Rapid toggling
    await wrapper.setProps({ visible: true });
    await wrapper.setProps({ visible: false });
    await wrapper.setProps({ visible: true });
    await wrapper.setProps({ visible: false });

    expect(document.body.style.overflow).toBe("");
    wrapper.unmount();
  });

  it("handles multiple independent modals correctly", async () => {
    const modal1 = mount(TransitionModal, {
      props: { visible: true },
      global: { stubs: { Teleport: true, Transition: false } },
    });
    const modal2 = mount(TransitionModal, {
      props: { visible: true },
      global: { stubs: { Teleport: true, Transition: false } },
    });
    const modal3 = mount(TransitionModal, {
      props: { visible: true },
      global: { stubs: { Teleport: true, Transition: false } },
    });

    expect(document.body.style.overflow).toBe("hidden");

    // Close in different order than opened
    await modal2.setProps({ visible: false });
    expect(document.body.style.overflow).toBe("hidden");

    await modal1.setProps({ visible: false });
    expect(document.body.style.overflow).toBe("hidden");

    await modal3.setProps({ visible: false });
    expect(document.body.style.overflow).toBe("");

    modal1.unmount();
    modal2.unmount();
    modal3.unmount();
  });
});
