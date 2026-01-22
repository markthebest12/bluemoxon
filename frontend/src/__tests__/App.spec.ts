import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

// Use vi.hoisted to ensure the state is available at mock time
const mockState = vi.hoisted(() => ({
  authInitializing: true,
}));

vi.mock("@/stores/auth", () => {
  return {
    useAuthStore: () => ({
      // Use a ref that wraps our mutable state
      get authInitializing() {
        return mockState.authInitializing;
      },
      initializeAuth: vi.fn().mockResolvedValue(undefined),
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
});
