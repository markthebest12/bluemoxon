import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import TrackingCard from "../TrackingCard.vue";

// Mock the API
vi.mock("@/services/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

describe("TrackingCard", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  const defaultProps = {
    bookId: 123,
    trackingStatus: "In Transit",
    trackingCarrier: "USPS",
    trackingNumber: "9400111899223456789012",
    trackingUrl: "https://tools.usps.com/go/TrackConfirmAction?tLabels=9400111899223456789012",
    trackingLastChecked: "2026-01-02T10:30:00Z",
    estimatedDelivery: "2026-01-05",
    trackingActive: true,
  };

  describe("rendering", () => {
    it("displays tracking status prominently", () => {
      const wrapper = mount(TrackingCard, { props: defaultProps });
      expect(wrapper.text()).toContain("In Transit");
    });

    it("displays carrier name", () => {
      const wrapper = mount(TrackingCard, { props: defaultProps });
      expect(wrapper.text()).toContain("USPS");
    });

    it("displays tracking number", () => {
      const wrapper = mount(TrackingCard, { props: defaultProps });
      // Should show at least part of the tracking number
      expect(wrapper.text()).toContain("9400111899223456789012");
    });

    it("displays estimated delivery date when available", () => {
      const wrapper = mount(TrackingCard, { props: defaultProps });
      // Should show formatted delivery date (may vary by timezone, so check for Jan 4 or Jan 5)
      expect(wrapper.text()).toMatch(/Jan [45]/);
      expect(wrapper.text()).toContain("Est. Delivery");
    });

    it("displays last checked timestamp", () => {
      const wrapper = mount(TrackingCard, { props: defaultProps });
      // Should show relative time or formatted date
      expect(wrapper.text()).toMatch(/checked|updated/i);
    });

    it("shows tracking link when tracking URL is provided", () => {
      const wrapper = mount(TrackingCard, { props: defaultProps });
      const link = wrapper.find('a[href*="usps.com"]');
      expect(link.exists()).toBe(true);
      expect(link.attributes("target")).toBe("_blank");
    });
  });

  describe("no tracking state", () => {
    it("shows empty state when no tracking info", () => {
      const wrapper = mount(TrackingCard, {
        props: {
          bookId: 123,
        },
      });
      expect(wrapper.text()).toMatch(/no tracking|not available/i);
    });

    it("does not show refresh button when no tracking", () => {
      const wrapper = mount(TrackingCard, {
        props: {
          bookId: 123,
        },
      });
      const refreshButton = wrapper.find('[data-testid="refresh-button"]');
      expect(refreshButton.exists()).toBe(false);
    });
  });

  describe("refresh functionality", () => {
    it("shows refresh button when tracking is active", () => {
      const wrapper = mount(TrackingCard, { props: defaultProps });
      const refreshButton = wrapper.find('[data-testid="refresh-button"]');
      expect(refreshButton.exists()).toBe(true);
    });

    it("calls refresh API when refresh button clicked", async () => {
      const { api } = await import("@/services/api");
      (api.post as any).mockResolvedValue({ data: { ...defaultProps } });

      const wrapper = mount(TrackingCard, { props: defaultProps });
      const refreshButton = wrapper.find('[data-testid="refresh-button"]');
      await refreshButton.trigger("click");

      expect(api.post).toHaveBeenCalledWith("/books/123/tracking/refresh");
    });

    it("shows loading state while refreshing", async () => {
      const { api } = await import("@/services/api");
      // Create a promise that won't resolve immediately
      let resolvePromise: (value: any) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      (api.post as any).mockReturnValue(pendingPromise);

      const wrapper = mount(TrackingCard, { props: defaultProps });
      const refreshButton = wrapper.find('[data-testid="refresh-button"]');
      await refreshButton.trigger("click");

      // Should show loading indicator
      expect(wrapper.find('[data-testid="refresh-button"]').attributes("disabled")).toBeDefined();

      // Cleanup
      resolvePromise!({ data: {} });
    });

    it("emits refreshed event with updated data on success", async () => {
      const { api } = await import("@/services/api");
      const updatedData = { ...defaultProps, trackingStatus: "Delivered" };
      (api.post as any).mockResolvedValue({ data: updatedData });

      const wrapper = mount(TrackingCard, { props: defaultProps });
      const refreshButton = wrapper.find('[data-testid="refresh-button"]');
      await refreshButton.trigger("click");

      // Wait for promise to resolve
      await vi.waitFor(() => {
        expect(wrapper.emitted("refreshed")).toBeTruthy();
      });
    });

    it("shows error message on refresh failure", async () => {
      const { api } = await import("@/services/api");
      (api.post as any).mockRejectedValue(new Error("Network error"));

      const wrapper = mount(TrackingCard, { props: defaultProps });
      const refreshButton = wrapper.find('[data-testid="refresh-button"]');
      await refreshButton.trigger("click");

      await vi.waitFor(() => {
        expect(wrapper.text()).toMatch(/error|failed/i);
      });
    });
  });

  describe("status styling", () => {
    it("shows success styling for delivered status", () => {
      const wrapper = mount(TrackingCard, {
        props: {
          ...defaultProps,
          trackingStatus: "Delivered",
          trackingActive: false,
        },
      });
      // Check for success-related styling class
      const statusElement = wrapper.find('[data-testid="tracking-status"]');
      expect(statusElement.classes().join(" ")).toMatch(/green|success/i);
    });

    it("shows warning styling for delayed status", () => {
      const wrapper = mount(TrackingCard, {
        props: {
          ...defaultProps,
          trackingStatus: "Delayed",
        },
      });
      const statusElement = wrapper.find('[data-testid="tracking-status"]');
      expect(statusElement.classes().join(" ")).toMatch(/yellow|orange|warning/i);
    });

    it("shows normal styling for in transit status", () => {
      const wrapper = mount(TrackingCard, { props: defaultProps });
      const statusElement = wrapper.find('[data-testid="tracking-status"]');
      expect(statusElement.classes().join(" ")).toMatch(/blue|primary|hunter/i);
    });
  });

  describe("delivered state", () => {
    it("shows delivered badge when trackingActive is false and status is Delivered", () => {
      const wrapper = mount(TrackingCard, {
        props: {
          ...defaultProps,
          trackingStatus: "Delivered",
          trackingActive: false,
          trackingDeliveredAt: "2026-01-03T14:30:00Z",
        },
      });
      expect(wrapper.text()).toMatch(/delivered/i);
    });

    it("hides refresh button when package is delivered", () => {
      const wrapper = mount(TrackingCard, {
        props: {
          ...defaultProps,
          trackingStatus: "Delivered",
          trackingActive: false,
        },
      });
      const refreshButton = wrapper.find('[data-testid="refresh-button"]');
      expect(refreshButton.exists()).toBe(false);
    });
  });
});
