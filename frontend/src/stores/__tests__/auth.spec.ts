import { describe, it, expect, beforeEach, vi, type Mock } from "vitest";
import { setActivePinia, createPinia } from "pinia";

// Store references to mocked functions
let mockGetCurrentUser: Mock;
let mockFetchMFAPreference: Mock;
let mockApiGet: Mock;

// Mock the API module
vi.mock("@/services/api", () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

// Mock aws-amplify/auth
vi.mock("aws-amplify/auth", () => ({
  getCurrentUser: vi.fn(),
  fetchMFAPreference: vi.fn(),
  signIn: vi.fn(),
  signOut: vi.fn(),
  confirmSignIn: vi.fn(),
  setUpTOTP: vi.fn(),
  verifyTOTPSetup: vi.fn(),
  updateMFAPreference: vi.fn(),
}));

// Mock dashboard cache invalidation
vi.mock("@/stores/dashboard", () => ({
  invalidateDashboardCache: vi.fn(),
}));

describe("Auth Store", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    vi.resetModules();

    // Clear the API key env var to test production auth flow
    vi.stubEnv("VITE_API_KEY", "");

    setActivePinia(createPinia());

    // Get fresh references to mocks after module reset
    const apiModule = await import("@/services/api");
    const amplifyModule = await import("aws-amplify/auth");

    mockApiGet = vi.mocked(apiModule.api.get);
    mockGetCurrentUser = vi.mocked(amplifyModule.getCurrentUser);
    mockFetchMFAPreference = vi.mocked(amplifyModule.fetchMFAPreference);
  });

  describe("checkAuth - parallel API calls", () => {
    it("calls /users/me and fetchMFAPreference in parallel (not sequentially)", async () => {
      // Track call order to prove parallelism
      const callOrder: string[] = [];

      // Mock getCurrentUser to return immediately
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "test@example.com" },
      } as never);

      // Mock /users/me - track when called, resolve after delay
      mockApiGet.mockImplementation(async (url) => {
        if (url === "/users/me") {
          callOrder.push("users/me:start");
          // Simulate network delay
          await new Promise((resolve) => setTimeout(resolve, 10));
          callOrder.push("users/me:end");
          return {
            data: {
              role: "editor",
              first_name: "Test",
              last_name: "User",
              mfa_exempt: false,
            },
          };
        }
        return { data: {} };
      });

      // Mock fetchMFAPreference - track when called
      mockFetchMFAPreference.mockImplementation(async () => {
        callOrder.push("mfa:start");
        await new Promise((resolve) => setTimeout(resolve, 10));
        callOrder.push("mfa:end");
        return { preferred: "TOTP", enabled: ["TOTP"] } as never;
      });

      // Dynamic import to get fresh module with cleared env
      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();
      await store.checkAuth();

      // If parallel: both :start calls happen before any :end
      // If sequential: users/me:end happens before mfa:start
      const usersEndIndex = callOrder.indexOf("users/me:end");
      const mfaStartIndex = callOrder.indexOf("mfa:start");

      expect(mfaStartIndex).toBeLessThan(usersEndIndex);
    });

    it("handles /users/me error without blocking MFA check", async () => {
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "test@example.com" },
      } as never);

      // /users/me fails
      mockApiGet.mockRejectedValue(new Error("API error"));

      // MFA check should still run
      mockFetchMFAPreference.mockResolvedValue({
        preferred: "TOTP",
        enabled: ["TOTP"],
      } as never);

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();
      await store.checkAuth();

      // Both should have been called
      expect(mockApiGet).toHaveBeenCalledWith("/users/me");
      expect(mockFetchMFAPreference).toHaveBeenCalled();
    });

    it("handles fetchMFAPreference error without breaking auth", async () => {
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "test@example.com" },
      } as never);

      mockApiGet.mockResolvedValue({
        data: {
          role: "editor",
          mfa_exempt: false,
        },
      });

      // MFA check fails
      mockFetchMFAPreference.mockRejectedValue(new Error("MFA error"));

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();
      await store.checkAuth();

      // Auth should still succeed
      expect(store.user).not.toBeNull();
      expect(store.user?.role).toBe("editor");
      // MFA step should be none (graceful degradation)
      expect(store.mfaStep).toBe("none");
    });

    it("skips MFA preference result when user is mfa_exempt", async () => {
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "test@example.com" },
      } as never);

      mockApiGet.mockResolvedValue({
        data: {
          role: "admin",
          mfa_exempt: true,
        },
      });

      // MFA preference says no TOTP (would normally trigger setup)
      mockFetchMFAPreference.mockResolvedValue({
        preferred: undefined,
        enabled: [],
      } as never);

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();
      await store.checkAuth();

      // Despite no TOTP, exempt user shouldn't need MFA setup
      expect(store.mfaStep).toBe("none");
      expect(store.user?.mfa_exempt).toBe(true);
    });

    it("requires MFA setup when non-exempt user has no TOTP", async () => {
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "test@example.com" },
      } as never);

      mockApiGet.mockResolvedValue({
        data: {
          role: "editor",
          mfa_exempt: false,
        },
      });

      mockFetchMFAPreference.mockResolvedValue({
        preferred: undefined,
        enabled: [],
      } as never);

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();
      await store.checkAuth();

      expect(store.mfaStep).toBe("mfa_setup_required");
    });
  });
});
