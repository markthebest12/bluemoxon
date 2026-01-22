import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

// Use vi.hoisted to ensure the state is available at mock time
const mockState = vi.hoisted(() => ({
  authInitializing: true,
  authError: false,
  authRetrying: false,
}));

const mockInitializeAuth = vi.hoisted(() => vi.fn().mockResolvedValue(undefined));

vi.mock("@/stores/auth", () => {
  return {
    useAuthStore: () => ({
      // Use a ref that wraps our mutable state
      get authInitializing() {
        return mockState.authInitializing;
      },
      get authError() {
        return mockState.authError;
      },
      get authRetrying() {
        return mockState.authRetrying;
      },
      initializeAuth: mockInitializeAuth,
    }),
  };
});

// Mock NavBar to prevent loading ThemeToggle and useTheme
vi.mock("@/components/layout/NavBar.vue", () => ({
  default: {
    name: "NavBar",
    template: '<nav data-testid="navbar">NavBar</nav>',
  },
}));

// Mock ToastContainer
vi.mock("@/components/ToastContainer.vue", () => ({
  default: {
    name: "ToastContainer",
    template: '<div data-testid="toast-container"></div>',
  },
}));

import App from "../App.vue";

describe("App.vue - cold start loading", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    // Reset to initializing state before each test
    mockState.authInitializing = true;
    mockState.authError = false;
    mockState.authRetrying = false;
    mockInitializeAuth.mockClear();
  });

  const mountApp = () =>
    mount(App, {
      global: {
        stubs: {
          RouterView: {
            name: "RouterView",
            template: '<div data-testid="router-view">Router Content</div>',
          },
        },
      },
    });

  it("shows loading overlay when authInitializing is true", async () => {
    mockState.authInitializing = true;

    const wrapper = mountApp();
    await flushPromises();

    const loadingOverlay = wrapper.find('[data-testid="auth-loading"]');
    expect(loadingOverlay.exists()).toBe(true);
  });

  it("hides loading overlay when authInitializing is false", async () => {
    mockState.authInitializing = false;

    const wrapper = mountApp();
    await flushPromises();

    const loadingOverlay = wrapper.find('[data-testid="auth-loading"]');
    expect(loadingOverlay.exists()).toBe(false);
  });

  it("shows NavBar when authInitializing is false", async () => {
    mockState.authInitializing = false;

    const wrapper = mountApp();
    await flushPromises();

    const navbar = wrapper.find('[data-testid="navbar"]');
    expect(navbar.exists()).toBe(true);
  });

  it("shows RouterView when authInitializing is false", async () => {
    mockState.authInitializing = false;

    const wrapper = mountApp();
    await flushPromises();

    const routerView = wrapper.find('[data-testid="router-view"]');
    expect(routerView.exists()).toBe(true);
  });

  it("loading overlay contains BlueMoxon branding", async () => {
    mockState.authInitializing = true;

    const wrapper = mountApp();
    await flushPromises();

    const loadingOverlay = wrapper.find('[data-testid="auth-loading"]');
    expect(loadingOverlay.text()).toContain("BlueMoxon");
  });

  it("shows error screen when authError is true", async () => {
    mockState.authError = true;
    mockState.authInitializing = false;

    const wrapper = mountApp();
    await flushPromises();

    const errorScreen = wrapper.find('[data-testid="auth-error"]');
    expect(errorScreen.exists()).toBe(true);
    expect(errorScreen.text()).toContain("Unable to connect");
  });

  it("error screen has retry button that calls initializeAuth", async () => {
    mockState.authError = true;
    mockState.authInitializing = false;

    const wrapper = mountApp();
    await flushPromises();

    const retryButton = wrapper.find('[data-testid="auth-retry-button"]');
    expect(retryButton.exists()).toBe(true);
    expect(retryButton.text()).toBe("Retry");

    await retryButton.trigger("click");
    expect(mockInitializeAuth).toHaveBeenCalled();
  });

  it("error screen has higher priority than loading overlay", async () => {
    mockState.authError = true;
    mockState.authInitializing = true;

    const wrapper = mountApp();
    await flushPromises();

    const errorScreen = wrapper.find('[data-testid="auth-error"]');
    const loadingOverlay = wrapper.find('[data-testid="auth-loading"]');

    expect(errorScreen.exists()).toBe(true);
    expect(loadingOverlay.exists()).toBe(false);
  });

  it("shows loading overlay when authInitializing is true and authError is false", async () => {
    mockState.authError = false;
    mockState.authInitializing = true;

    const wrapper = mountApp();
    await flushPromises();

    const errorScreen = wrapper.find('[data-testid="auth-error"]');
    const loadingOverlay = wrapper.find('[data-testid="auth-loading"]');

    expect(errorScreen.exists()).toBe(false);
    expect(loadingOverlay.exists()).toBe(true);
  });

  it("shows 'taking longer' message when authRetrying is true", async () => {
    mockState.authInitializing = true;
    mockState.authError = false;
    mockState.authRetrying = true;

    const wrapper = mountApp();
    await flushPromises();

    const retryingMessage = wrapper.find('[data-testid="auth-retrying"]');
    expect(retryingMessage.exists()).toBe(true);
    expect(retryingMessage.text()).toContain("Taking longer than usual");
  });

  it("hides 'taking longer' message when authRetrying is false", async () => {
    mockState.authInitializing = true;
    mockState.authError = false;
    mockState.authRetrying = false;

    const wrapper = mountApp();
    await flushPromises();

    const retryingMessage = wrapper.find('[data-testid="auth-retrying"]');
    expect(retryingMessage.exists()).toBe(false);
  });
});
