import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import AddToWatchlistModal from "../AddToWatchlistModal.vue";

vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("AddToWatchlistModal", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("renders modal with form fields", () => {
    const wrapper = mount(AddToWatchlistModal, {
      global: {
        stubs: {
          Teleport: true,
        },
      },
    });
    expect(wrapper.text()).toContain("Add to Watchlist");
    expect(wrapper.text()).toContain("Title");
    expect(wrapper.text()).toContain("Author");
  });

  it("emits close when cancel clicked", async () => {
    const wrapper = mount(AddToWatchlistModal, {
      global: {
        stubs: {
          Teleport: true,
        },
      },
    });
    const cancelButton = wrapper
      .findAll('button[type="button"]')
      .find((btn) => btn.text() === "Cancel");
    await cancelButton!.trigger("click");
    expect(wrapper.emitted("close")).toBeTruthy();
  });

  it("validates required fields before submit", async () => {
    const wrapper = mount(AddToWatchlistModal, {
      global: {
        stubs: {
          Teleport: true,
        },
      },
    });
    const form = wrapper.find("form");
    await form.trigger("submit");
    expect(wrapper.text()).toContain("Title is required");
  });
});
