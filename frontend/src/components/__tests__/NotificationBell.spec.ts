import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import NotificationBell from "../NotificationBell.vue";
import { api } from "@/services/api";

// Mock the API
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Mock vue-router
vi.mock("vue-router", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  RouterLink: {
    name: "RouterLink",
    template: '<a><slot /></a>',
    props: ['to'],
  },
}));

describe("NotificationBell", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("renders bell icon", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { notifications: [], unread_count: 0 },
    });

    const wrapper = mount(NotificationBell);
    await flushPromises();

    // Should have a button with bell icon
    expect(wrapper.find("button").exists()).toBe(true);
    expect(wrapper.find("svg").exists()).toBe(true);
  });

  it("shows unread count badge when there are unread notifications", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notifications: [
          { id: 1, title: "Test", message: "Test message", read: false },
        ],
        unread_count: 3,
      },
    });

    const wrapper = mount(NotificationBell);
    await flushPromises();

    // Should show badge with count
    const badge = wrapper.find('[data-testid="notification-badge"]');
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe("3");
  });

  it("hides badge when there are no unread notifications", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { notifications: [], unread_count: 0 },
    });

    const wrapper = mount(NotificationBell);
    await flushPromises();

    const badge = wrapper.find('[data-testid="notification-badge"]');
    expect(badge.exists()).toBe(false);
  });

  it("opens dropdown when bell is clicked", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notifications: [
          { id: 1, title: "Test", message: "Test message", read: false },
        ],
        unread_count: 1,
      },
    });

    const wrapper = mount(NotificationBell);
    await flushPromises();

    // Dropdown should be hidden initially
    expect(wrapper.find('[data-testid="notification-dropdown"]').exists()).toBe(false);

    // Click bell button
    await wrapper.find("button").trigger("click");

    // Dropdown should be visible
    expect(wrapper.find('[data-testid="notification-dropdown"]').exists()).toBe(true);
  });

  it("displays notifications in dropdown", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notifications: [
          { id: 1, title: "Package Shipped", message: "Your book is on the way", read: false },
          { id: 2, title: "Delivered", message: "Package delivered", read: true },
        ],
        unread_count: 1,
      },
    });

    const wrapper = mount(NotificationBell);
    await flushPromises();

    // Open dropdown
    await wrapper.find("button").trigger("click");

    const dropdown = wrapper.find('[data-testid="notification-dropdown"]');
    expect(dropdown.text()).toContain("Package Shipped");
    expect(dropdown.text()).toContain("Delivered");
  });

  it("marks notification as read when clicked", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notifications: [
          { id: 1, title: "Test", message: "Test message", read: false },
        ],
        unread_count: 1,
      },
    });
    vi.mocked(api.post).mockResolvedValueOnce({
      data: { id: 1, read: true },
    });

    const wrapper = mount(NotificationBell);
    await flushPromises();

    // Open dropdown
    await wrapper.find("button").trigger("click");

    // Click on notification
    const notificationItem = wrapper.find('[data-testid="notification-item-1"]');
    await notificationItem.trigger("click");

    // Should call POST to mark as read
    expect(api.post).toHaveBeenCalledWith("/users/me/notifications/1/read");
  });

  it("shows empty state when no notifications", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { notifications: [], unread_count: 0 },
    });

    const wrapper = mount(NotificationBell);
    await flushPromises();

    // Open dropdown
    await wrapper.find("button").trigger("click");

    const dropdown = wrapper.find('[data-testid="notification-dropdown"]');
    expect(dropdown.text()).toContain("No notifications");
  });

  it("has View All link to notifications page", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notifications: [
          { id: 1, title: "Test", message: "Test message", read: false },
        ],
        unread_count: 1,
      },
    });

    const wrapper = mount(NotificationBell);
    await flushPromises();

    // Open dropdown
    await wrapper.find("button").trigger("click");

    // Should have View All link
    const viewAllLink = wrapper.find('[data-testid="view-all-link"]');
    expect(viewAllLink.exists()).toBe(true);
    expect(viewAllLink.text()).toContain("View All");
  });

  it("closes dropdown when clicking outside", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notifications: [
          { id: 1, title: "Test", message: "Test message", read: false },
        ],
        unread_count: 1,
      },
    });

    const wrapper = mount(NotificationBell);
    await flushPromises();

    // Open dropdown
    await wrapper.find("button").trigger("click");
    expect(wrapper.find('[data-testid="notification-dropdown"]').exists()).toBe(true);

    // Click overlay to close
    await wrapper.find('[data-testid="notification-overlay"]').trigger("click");
    expect(wrapper.find('[data-testid="notification-dropdown"]').exists()).toBe(false);
  });

  it("styles unread notifications differently", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        notifications: [
          { id: 1, title: "Unread", message: "Unread message", read: false },
          { id: 2, title: "Read", message: "Read message", read: true },
        ],
        unread_count: 1,
      },
    });

    const wrapper = mount(NotificationBell);
    await flushPromises();

    // Open dropdown
    await wrapper.find("button").trigger("click");

    const unreadItem = wrapper.find('[data-testid="notification-item-1"]');
    const readItem = wrapper.find('[data-testid="notification-item-2"]');

    // Unread should have different styling (e.g., background color)
    expect(unreadItem.classes()).toContain("bg-blue-50");
    expect(readItem.classes()).not.toContain("bg-blue-50");
  });
});
