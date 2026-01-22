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

    it("requires MFA setup when MFA check fails for non-exempt user (security)", async () => {
      // Issue 1: MFA check failure should NOT silently pass
      // Non-exempt users must have MFA verified - if check fails, require setup
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

      // MFA check fails (Cognito outage, network error, etc.)
      mockFetchMFAPreference.mockRejectedValue(new Error("MFA error"));

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();
      await store.checkAuth();

      // Auth should still succeed (user is logged in)
      expect(store.user).not.toBeNull();
      expect(store.user?.role).toBe("editor");
      // SECURITY: MFA check failed - require setup rather than silently passing
      expect(store.mfaStep).toBe("mfa_setup_required");
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

    it("handles logout during checkAuth without null reference errors (race condition)", async () => {
      // Issue 3: If logout() runs while Promise.all is in flight, don't crash
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "test@example.com" },
      } as never);

      // Make /users/me slow so logout can happen during it
      mockApiGet.mockImplementation(async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
        return {
          data: {
            role: "editor",
            mfa_exempt: false,
          },
        };
      });

      mockFetchMFAPreference.mockResolvedValue({
        preferred: "TOTP",
        enabled: ["TOTP"],
      } as never);

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();

      // Start checkAuth
      const checkAuthPromise = store.checkAuth();

      // Simulate logout during the async operation
      await new Promise((resolve) => setTimeout(resolve, 10));
      store.user = null; // Simulate logout clearing user

      // Should complete without throwing
      await expect(checkAuthPromise).resolves.not.toThrow();
    });

    it("times out slow API calls instead of hanging forever", async () => {
      // Issue 6: Add timeout handling for hung promises
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "test@example.com" },
      } as never);

      // Make /users/me hang for a long time (longer than timeout)
      mockApiGet.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 20000)));

      // MFA check also hangs
      mockFetchMFAPreference.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 20000))
      );

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();

      // Should complete within reasonable time (auth timeout is 5s)
      const startTime = Date.now();
      await store.checkAuth();
      const elapsed = Date.now() - startTime;

      // Should timeout around 5s, not hang for 20s
      expect(elapsed).toBeLessThan(7000);
      expect(elapsed).toBeGreaterThan(4000); // Should wait for timeout
      // User should still be set from Cognito (just without API profile data)
      expect(store.user).not.toBeNull();
      // MFA should require setup since both calls timed out (security)
      expect(store.mfaStep).toBe("mfa_setup_required");
    }, 10000); // 10s test timeout
  });

  describe("cold start UX - authInitializing", () => {
    it("exposes authInitializing state that starts as true", async () => {
      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();

      // Before any auth check, authInitializing should be true
      expect(store.authInitializing).toBe(true);
    });

    it("sets authInitializing to false after initializeAuth completes", async () => {
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "test@example.com" },
      } as never);

      mockApiGet.mockResolvedValue({
        data: { role: "admin", mfa_exempt: true },
      });

      mockFetchMFAPreference.mockResolvedValue({
        preferred: "TOTP",
        enabled: ["TOTP"],
      } as never);

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();

      expect(store.authInitializing).toBe(true);
      await store.initializeAuth();
      expect(store.authInitializing).toBe(false);
    });

    it("keeps authInitializing true until fresh auth completes", async () => {
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "test@example.com" },
      } as never);

      // Make API slow
      mockApiGet.mockImplementation(async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
        return { data: { role: "admin", mfa_exempt: true } };
      });

      mockFetchMFAPreference.mockResolvedValue({
        preferred: "TOTP",
        enabled: ["TOTP"],
      } as never);

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();

      // Start initializeAuth but don't await yet
      const initPromise = store.initializeAuth();

      // authInitializing should stay TRUE until fresh auth completes
      expect(store.authInitializing).toBe(true);

      // Wait for full auth to complete
      await initPromise;
      expect(store.authInitializing).toBe(false);
    });

    it("isAdmin is false until auth completes (security)", async () => {
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "admin@example.com" },
      } as never);

      // Slow API response
      mockApiGet.mockImplementation(async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
        return { data: { role: "admin", mfa_exempt: true } };
      });

      mockFetchMFAPreference.mockResolvedValue({
        preferred: "TOTP",
        enabled: ["TOTP"],
      } as never);

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();

      // Start init
      const initPromise = store.initializeAuth();

      // SECURITY: isAdmin should be FALSE until fresh auth completes
      expect(store.isAdmin).toBe(false);

      await initPromise;

      // Now isAdmin should be true from verified user
      expect(store.isAdmin).toBe(true);
    });

    it("sets authInitializing to false even on auth failure", async () => {
      // Auth will fail - no current user
      mockGetCurrentUser.mockRejectedValue(new Error("Not authenticated"));

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();

      await store.initializeAuth();

      expect(store.authInitializing).toBe(false);
      expect(store.user).toBeNull();
    });

    it("prevents concurrent initializeAuth calls (race condition guard)", async () => {
      mockGetCurrentUser.mockResolvedValue({
        username: "testuser",
        userId: "123",
        signInDetails: { loginId: "test@example.com" },
      } as never);

      let apiCallCount = 0;
      mockApiGet.mockImplementation(async () => {
        apiCallCount++;
        await new Promise((resolve) => setTimeout(resolve, 50));
        return { data: { role: "admin", mfa_exempt: true } };
      });

      mockFetchMFAPreference.mockResolvedValue({
        preferred: "TOTP",
        enabled: ["TOTP"],
      } as never);

      const { useAuthStore } = await import("../auth");
      const store = useAuthStore();

      // Call initializeAuth multiple times concurrently
      const promise1 = store.initializeAuth();
      const promise2 = store.initializeAuth();
      const promise3 = store.initializeAuth();

      await Promise.all([promise1, promise2, promise3]);

      // Should only have made one API call due to race condition guard
      expect(apiCallCount).toBe(1);
    });
  });
});
