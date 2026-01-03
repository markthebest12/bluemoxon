import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import NotificationPreferences from "../NotificationPreferences.vue";
import { api } from "@/services/api";

// Mock the API
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

describe("NotificationPreferences", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("renders notification preferences panel", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });

    const wrapper = mount(NotificationPreferences);
    await flushPromises();

    expect(wrapper.text()).toContain("Notification Preferences");
    expect(wrapper.text()).toContain("Email Notifications");
    expect(wrapper.text()).toContain("SMS Notifications");
  });

  it("loads and displays current preferences", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notify_tracking_email: true,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });

    const wrapper = mount(NotificationPreferences);
    await flushPromises();

    // Email toggle should be checked
    const emailToggle = wrapper.find('[data-testid="email-toggle"]');
    expect((emailToggle.element as HTMLInputElement).checked).toBe(true);

    // SMS toggle should be unchecked
    const smsToggle = wrapper.find('[data-testid="sms-toggle"]');
    expect((smsToggle.element as HTMLInputElement).checked).toBe(false);
  });

  it("shows phone number field only when SMS is enabled", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });

    const wrapper = mount(NotificationPreferences);
    await flushPromises();

    // Phone field should be hidden initially
    expect(wrapper.find('[data-testid="phone-input"]').exists()).toBe(false);

    // Enable SMS
    await wrapper.find('[data-testid="sms-toggle"]').setValue(true);

    // Phone field should now be visible
    expect(wrapper.find('[data-testid="phone-input"]').exists()).toBe(true);
  });

  it("displays existing phone number when SMS is enabled", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: true,
        phone_number: "+1234567890",
      },
    });

    const wrapper = mount(NotificationPreferences);
    await flushPromises();

    const phoneInput = wrapper.find('[data-testid="phone-input"]');
    expect(phoneInput.exists()).toBe(true);
    expect((phoneInput.element as HTMLInputElement).value).toBe("+1234567890");
  });

  it("saves preferences when save button is clicked", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });
    vi.mocked(api.patch).mockResolvedValueOnce({
      data: {
        notify_tracking_email: true,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });

    const wrapper = mount(NotificationPreferences);
    await flushPromises();

    // Enable email notifications
    await wrapper.find('[data-testid="email-toggle"]').setValue(true);

    // Click save
    await wrapper.find('[data-testid="save-button"]').trigger("click");

    expect(api.patch).toHaveBeenCalledWith("/users/me/preferences", {
      notify_tracking_email: true,
      notify_tracking_sms: false,
      phone_number: null,
    });
  });

  it("saves phone number when SMS is enabled", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });
    vi.mocked(api.patch).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: true,
        phone_number: "+1234567890",
      },
    });

    const wrapper = mount(NotificationPreferences);
    await flushPromises();

    // Enable SMS
    await wrapper.find('[data-testid="sms-toggle"]').setValue(true);

    // Enter phone number
    await wrapper.find('[data-testid="phone-input"]').setValue("+1234567890");

    // Click save
    await wrapper.find('[data-testid="save-button"]').trigger("click");

    expect(api.patch).toHaveBeenCalledWith("/users/me/preferences", {
      notify_tracking_email: false,
      notify_tracking_sms: true,
      phone_number: "+1234567890",
    });
  });

  it("shows success message after saving", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });
    vi.mocked(api.patch).mockResolvedValueOnce({
      data: {
        notify_tracking_email: true,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });

    const wrapper = mount(NotificationPreferences);
    await flushPromises();

    // Click save
    await wrapper.find('[data-testid="save-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Preferences saved");
  });

  it("shows error message on save failure", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });
    vi.mocked(api.patch).mockRejectedValueOnce(new Error("Network error"));

    const wrapper = mount(NotificationPreferences);
    await flushPromises();

    // Click save
    await wrapper.find('[data-testid="save-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Failed to save");
  });

  it("shows loading state on save button while saving", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });

    // Create a promise that won't resolve immediately
    let resolvePromise: (value: unknown) => void;
    const pendingPromise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    vi.mocked(api.patch).mockReturnValueOnce(pendingPromise as ReturnType<typeof api.patch>);

    const wrapper = mount(NotificationPreferences);
    await flushPromises();

    // Click save
    wrapper.find('[data-testid="save-button"]').trigger("click");
    await flushPromises();

    // Button should show loading state
    const saveButton = wrapper.find('[data-testid="save-button"]');
    expect(saveButton.text()).toContain("Saving");
    expect(saveButton.attributes("disabled")).toBeDefined();

    // Resolve the promise
    resolvePromise!({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });
    await flushPromises();

    // Button should return to normal state
    expect(saveButton.text()).toContain("Save");
  });

  it("disables save button while loading initial preferences", async () => {
    // Create a promise that won't resolve immediately
    let resolvePromise: (value: unknown) => void;
    const pendingPromise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    vi.mocked(api.get).mockReturnValueOnce(pendingPromise as ReturnType<typeof api.get>);

    const wrapper = mount(NotificationPreferences);

    // Button should be disabled during loading
    const saveButton = wrapper.find('[data-testid="save-button"]');
    expect(saveButton.attributes("disabled")).toBeDefined();

    // Resolve the promise
    resolvePromise!({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });
    await flushPromises();

    // Button should be enabled now
    expect(saveButton.attributes("disabled")).toBeUndefined();
  });

  it("clears phone number when SMS is disabled", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: true,
        phone_number: "+1234567890",
      },
    });
    vi.mocked(api.patch).mockResolvedValueOnce({
      data: {
        notify_tracking_email: false,
        notify_tracking_sms: false,
        phone_number: null,
      },
    });

    const wrapper = mount(NotificationPreferences);
    await flushPromises();

    // Disable SMS
    await wrapper.find('[data-testid="sms-toggle"]').setValue(false);

    // Click save
    await wrapper.find('[data-testid="save-button"]').trigger("click");

    // Phone should be sent as null when SMS is disabled
    expect(api.patch).toHaveBeenCalledWith("/users/me/preferences", {
      notify_tracking_email: false,
      notify_tracking_sms: false,
      phone_number: null,
    });
  });
});
