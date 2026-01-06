import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { ref } from "vue";

// Create shared mock state
const mockToasts = ref<Array<{ id: number; type: string; message: string }>>([]);
const mockPauseTimer = vi.fn();
const mockResumeTimer = vi.fn();

vi.mock("@/composables/useToast", () => ({
  useToast: () => ({
    toasts: mockToasts,
    showError: (message: string) => {
      mockToasts.value.push({ id: Date.now(), type: "error", message });
    },
    showSuccess: (message: string) => {
      mockToasts.value.push({ id: Date.now(), type: "success", message });
    },
    dismiss: (id: number) => {
      mockToasts.value = mockToasts.value.filter((t) => t.id !== id);
    },
    pauseTimer: mockPauseTimer,
    resumeTimer: mockResumeTimer,
    _reset: () => {
      mockToasts.value = [];
    },
  }),
}));

import ToastContainer from "../ToastContainer.vue";
import { useToast } from "@/composables/useToast";

describe("ToastContainer", () => {
  beforeEach(() => {
    mockToasts.value = [];
    mockPauseTimer.mockClear();
    mockResumeTimer.mockClear();
  });

  describe("rendering", () => {
    it("should render nothing when no toasts", () => {
      const wrapper = mount(ToastContainer);
      expect(wrapper.findAll('[role="alert"]')).toHaveLength(0);
      expect(wrapper.findAll('[role="status"]')).toHaveLength(0);
    });

    it("should render error toast with correct styling", async () => {
      const wrapper = mount(ToastContainer);
      const { showError } = useToast();

      showError("Test error message");
      await flushPromises();

      const toast = wrapper.find('[role="alert"]');
      expect(toast.exists()).toBe(true);
      expect(toast.text()).toContain("Test error message");
      expect(toast.classes()).toContain("toast-error");
    });

    it("should render success toast with correct styling", async () => {
      const wrapper = mount(ToastContainer);
      const { showSuccess } = useToast();

      showSuccess("Success message");
      await flushPromises();

      const toast = wrapper.find('[role="status"]');
      expect(toast.exists()).toBe(true);
      expect(toast.text()).toContain("Success message");
      expect(toast.classes()).toContain("toast-success");
    });

    it("should render multiple toasts", async () => {
      const wrapper = mount(ToastContainer);
      const { showError, showSuccess } = useToast();

      showError("Error 1");
      showSuccess("Success 1");
      await flushPromises();

      const errorToasts = wrapper.findAll('[role="alert"]');
      const successToasts = wrapper.findAll('[role="status"]');
      expect(errorToasts.length + successToasts.length).toBe(2);
    });
  });

  describe("accessibility", () => {
    it("should have role=alert on error toasts", async () => {
      const wrapper = mount(ToastContainer);
      const { showError } = useToast();

      showError("Alert message");
      await flushPromises();

      const toast = wrapper.find('[role="alert"]');
      expect(toast.exists()).toBe(true);
    });

    it("should have role=status on success toasts", async () => {
      const wrapper = mount(ToastContainer);
      const { showSuccess } = useToast();

      showSuccess("Status message");
      await flushPromises();

      const toast = wrapper.find('[role="status"]');
      expect(toast.exists()).toBe(true);
    });

    it("should have aria-live=polite on container", () => {
      const wrapper = mount(ToastContainer);
      expect(wrapper.attributes("aria-live")).toBe("polite");
    });

    it("should have accessible dismiss button", async () => {
      const wrapper = mount(ToastContainer);
      const { showError } = useToast();

      showError("Dismissable");
      await flushPromises();

      const dismissBtn = wrapper.find('button[aria-label="Dismiss notification"]');
      expect(dismissBtn.exists()).toBe(true);
    });
  });

  describe("dismiss interaction", () => {
    it("should remove toast when dismiss button clicked", async () => {
      const wrapper = mount(ToastContainer);
      const { showError } = useToast();

      showError("To be dismissed");
      await flushPromises();

      const dismissBtn = wrapper.find('button[aria-label="Dismiss notification"]');
      await dismissBtn.trigger("click");
      await flushPromises();

      expect(wrapper.findAll('[role="alert"]')).toHaveLength(0);
    });
  });

  describe("hover to pause", () => {
    it("should call pauseTimer on mouseenter", async () => {
      const wrapper = mount(ToastContainer);
      const { showError } = useToast();

      showError("Hover me");
      await flushPromises();

      const toast = wrapper.find('[role="alert"]');
      await toast.trigger("mouseenter");

      expect(mockPauseTimer).toHaveBeenCalled();
    });

    it("should call resumeTimer on mouseleave", async () => {
      const wrapper = mount(ToastContainer);
      const { showError } = useToast();

      showError("Leave me");
      await flushPromises();

      const toast = wrapper.find('[role="alert"]');
      await toast.trigger("mouseleave");

      expect(mockResumeTimer).toHaveBeenCalled();
    });
  });

  describe("positioning", () => {
    it("should have fixed positioning class", () => {
      const wrapper = mount(ToastContainer);
      expect(wrapper.classes()).toContain("fixed");
      expect(wrapper.classes()).toContain("top-4");
      expect(wrapper.classes()).toContain("right-4");
    });
  });
});
