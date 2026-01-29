import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";
import { invalidateDashboardCache } from "@/stores/dashboard";

const DEV_API_KEY = import.meta.env.VITE_API_KEY || "";

interface User {
  username: string;
  email: string;
  role: string;
  first_name?: string;
  last_name?: string;
  mfa_exempt?: boolean;
}

type MfaStep =
  | "none"
  | "totp_required"
  | "totp_setup"
  | "new_password_required"
  | "mfa_setup_required";

type MfaResult<T> =
  | { status: "success"; value: T }
  | { status: "timeout" }
  | { status: "failed"; error: Error };

export const useAuthStore = defineStore("auth", () => {
  const user = ref<User | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const mfaStep = ref<MfaStep>("none");
  const totpSetupUri = ref<string | null>(null);
  const authInitializing = ref(true);
  const authError = ref(false);
  const authRetrying = ref(false); // True after first retry fails, shows "taking longer" message
  let pendingInitPromise: Promise<void> | null = null; // Race condition guard using Promise reference

  interface UserProfileResponse {
    data: {
      role?: string;
      first_name?: string;
      last_name?: string;
      mfa_exempt?: boolean;
    };
  }

  /**
   * Fetch user profile with exponential backoff retry for cold start resilience.
   * Retries up to 3 times with delays of 2s, 4s between attempts.
   * Each attempt has a 10s timeout to handle hung promises.
   * Sets authRetrying=true after first failure for progressive UI feedback.
   */
  async function fetchUserProfileWithRetry(): Promise<UserProfileResponse | null> {
    const MAX_RETRIES = 3;
    const BASE_DELAY_MS = 2000;
    const ATTEMPT_TIMEOUT_MS = 10000;

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        const response = await Promise.race([
          api.get("/users/me"),
          new Promise<never>((_, reject) => {
            setTimeout(() => reject(new Error("Request timeout")), ATTEMPT_TIMEOUT_MS);
          }),
        ]);
        authRetrying.value = false; // Clear retrying state on success
        return response;
      } catch (e) {
        console.warn(`[Auth] /users/me attempt ${attempt}/${MAX_RETRIES} failed:`, e);
        if (attempt < MAX_RETRIES) {
          authRetrying.value = true; // Show "taking longer" message after first failure
          const delay = BASE_DELAY_MS * Math.pow(2, attempt - 1);
          console.log(`[Auth] Retrying in ${delay}ms...`);
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }
    return null;
  }

  const isAuthenticated = computed(() => !!user.value);
  // SECURITY: Only use verified user role, never cached role for authorization
  const isAdmin = computed(() => user.value?.role === "admin");
  const isEditor = computed(() => ["admin", "editor"].includes(user.value?.role || ""));
  const needsMfa = computed(() => mfaStep.value !== "none");

  async function checkAuth() {
    loading.value = true;

    // Dev mode: bypass Cognito entirely when API key is configured
    if (DEV_API_KEY) {
      console.log("[Auth] Dev mode: using API key auth");
      try {
        const response = await api.get("/users/me");
        user.value = {
          username: response.data.email || "dev-user",
          email: response.data.email || "dev@localhost",
          role: response.data.role || "admin",
          first_name: response.data.first_name,
          last_name: response.data.last_name,
          mfa_exempt: true,
        };
        mfaStep.value = "none";
      } catch (e) {
        console.warn("[Auth] Dev mode: API key auth failed:", e);
        // Still set a default dev user so the app works
        user.value = {
          username: "dev-user",
          email: "dev@localhost",
          role: "admin",
          mfa_exempt: true,
        };
        mfaStep.value = "none";
      }
      loading.value = false;
      return;
    }

    try {
      const { getCurrentUser, fetchMFAPreference } = await import("aws-amplify/auth");
      const currentUser = await getCurrentUser();

      // Basic user info from Cognito
      user.value = {
        username: currentUser.username,
        email: currentUser.signInDetails?.loginId || "",
        role: "viewer", // Default, will be updated from API
      };

      // Timeout wrapper to prevent hung promises (Issue 6)
      // Returns a typed MfaResult to distinguish success, timeout, and failure
      const MFA_TIMEOUT_MS = 5000;
      const withMfaTimeout = <T>(promise: Promise<T>): Promise<MfaResult<T>> => {
        let timeoutId: ReturnType<typeof setTimeout>;
        return Promise.race([
          promise
            .then((value) => {
              clearTimeout(timeoutId);
              return { status: "success" as const, value };
            })
            .catch((e: unknown) => {
              clearTimeout(timeoutId);
              console.warn("[Auth] Could not fetch MFA preference:", e);
              const error = e instanceof Error ? e : new Error(String(e));
              return { status: "failed" as const, error };
            }),
          new Promise<MfaResult<T>>((resolve) => {
            timeoutId = setTimeout(() => {
              // Log at debug level - timeouts are expected during Cognito cold starts
              // and don't indicate a problem if user already authenticated via MFA
              console.debug(
                `[Auth] fetchMFAPreference timed out after ${MFA_TIMEOUT_MS}ms (non-blocking)`
              );
              resolve({ status: "timeout" as const });
            }, MFA_TIMEOUT_MS);
          }),
        ]);
      };

      // Fetch user profile (with retry for cold start) and MFA preference in parallel
      // Both calls are independent - we'll use mfa_exempt from profile to decide
      // whether to apply the MFA preference result
      const [userResult, mfaResult] = await Promise.all([
        fetchUserProfileWithRetry(),
        withMfaTimeout(fetchMFAPreference()),
      ]);

      // Issue 3: Check if logout happened during async operation
      if (!user.value) {
        console.warn("[Auth] User logged out during checkAuth, aborting");
        return;
      }

      // Apply user profile data
      let isMfaExempt = false;
      if (userResult?.data) {
        user.value.role = userResult.data.role || user.value.role;
        user.value.first_name = userResult.data.first_name;
        user.value.last_name = userResult.data.last_name;
        isMfaExempt = userResult.data.mfa_exempt === true;
        user.value.mfa_exempt = isMfaExempt;
        authError.value = false; // Clear error on successful fetch
      } else {
        // All retries exhausted - set authError to show error UI
        authError.value = true;
      }

      // Apply MFA preference using typed result
      if (isMfaExempt) {
        // User is explicitly MFA-exempt - no MFA required
        mfaStep.value = "none";
      } else if (mfaResult.status === "failed") {
        // Issue 1: MFA check failed for non-exempt user - require setup for security
        // Don't silently pass when we can't verify MFA status
        console.warn("[Auth] MFA check failed for non-exempt user, requiring MFA setup");
        mfaStep.value = "mfa_setup_required";
      } else if (mfaResult.status === "success" && mfaResult.value) {
        // MFA check succeeded - check if TOTP is configured
        const hasMfa =
          mfaResult.value.preferred === "TOTP" || mfaResult.value.enabled?.includes("TOTP");
        mfaStep.value = hasMfa ? "none" : "mfa_setup_required";
      } else if (mfaResult.status === "timeout") {
        // Issue #1414: MFA check timed out but didn't fail - don't force MFA setup
        // If user already passed Cognito authentication, they already verified MFA
        // SECURITY DEPENDENCY: This assumes Cognito User Pool is configured to require MFA
        // for all non-exempt users. If Cognito MFA enforcement is disabled, users without
        // MFA could bypass this check. Verify Cognito config if changing MFA requirements.
        // Timeouts are expected during Cognito cold starts and shouldn't penalize users
        console.debug("[Auth] MFA preference check timed out, assuming MFA is configured");
        mfaStep.value = "none";
      } else {
        // MFA preference returned null (success but no data) - require setup
        mfaStep.value = "mfa_setup_required";
      }
    } catch (e) {
      // Session check failed - clear user silently (no toast to avoid spam on page load)
      console.error("[Auth] Session check failed:", e);
      user.value = null;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Initialize auth - shows loading overlay until fresh auth completes.
   * Uses Promise reference pattern to handle concurrent calls safely.
   */
  async function initializeAuth(): Promise<void> {
    // Race condition guard using Promise reference - return existing promise if in progress
    if (pendingInitPromise) {
      return pendingInitPromise;
    }

    authRetrying.value = false; // Reset retrying state at start

    const doInit = async () => {
      try {
        await checkAuth();
      } finally {
        authInitializing.value = false;
        pendingInitPromise = null;
      }
    };

    pendingInitPromise = doInit();
    return pendingInitPromise;
  }

  async function login(username: string, password: string) {
    loading.value = true;
    error.value = null;
    mfaStep.value = "none";
    totpSetupUri.value = null;

    try {
      const { signIn, signOut } = await import("aws-amplify/auth");

      // Clear any existing session to avoid "already signed in" errors
      try {
        await signOut();
      } catch {
        // Ignore errors - no session to clear
      }
      const result = await signIn({ username, password });

      if (result.nextStep.signInStep === "CONFIRM_SIGN_IN_WITH_TOTP_CODE") {
        mfaStep.value = "totp_required";
        return; // Don't complete login yet, wait for TOTP
      }

      if (result.nextStep.signInStep === "CONTINUE_SIGN_IN_WITH_TOTP_SETUP") {
        // User needs to set up TOTP - details are in the result
        const totpSetupDetails = result.nextStep.totpSetupDetails;
        if (totpSetupDetails) {
          totpSetupUri.value = totpSetupDetails.getSetupUri("BlueMoxon", username).toString();
        }
        mfaStep.value = "totp_setup";
        return; // Wait for user to set up and verify TOTP
      }

      if (result.nextStep.signInStep === "CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED") {
        // User has temporary password and needs to set a new one
        mfaStep.value = "new_password_required";
        return; // Wait for user to set new password
      }

      if (result.isSignedIn) {
        await checkAuth();
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Login failed";
      error.value = message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function confirmTotpCode(code: string) {
    loading.value = true;
    error.value = null;

    try {
      const { confirmSignIn } = await import("aws-amplify/auth");
      const result = await confirmSignIn({ challengeResponse: code });

      if (result.isSignedIn) {
        mfaStep.value = "none";
        totpSetupUri.value = null;
        await checkAuth();
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Invalid code";
      error.value = message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function confirmNewPassword(newPassword: string) {
    loading.value = true;
    error.value = null;

    try {
      const { confirmSignIn } = await import("aws-amplify/auth");
      const result = await confirmSignIn({ challengeResponse: newPassword });

      if (result.nextStep.signInStep === "CONTINUE_SIGN_IN_WITH_TOTP_SETUP") {
        // After setting password, user needs to set up TOTP
        const totpSetupDetails = result.nextStep.totpSetupDetails;
        if (totpSetupDetails) {
          totpSetupUri.value = totpSetupDetails.getSetupUri("BlueMoxon").toString();
        }
        mfaStep.value = "totp_setup";
        return;
      }

      if (result.isSignedIn) {
        mfaStep.value = "none";
        await checkAuth();
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to set new password";
      error.value = message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function verifyTotpSetup(code: string) {
    loading.value = true;
    error.value = null;

    try {
      // During sign-in TOTP setup, just use confirmSignIn with the code
      const { confirmSignIn } = await import("aws-amplify/auth");
      const result = await confirmSignIn({ challengeResponse: code });

      if (result.isSignedIn) {
        mfaStep.value = "none";
        totpSetupUri.value = null;
        await checkAuth();
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Invalid code";
      error.value = message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function initiateMfaSetup() {
    loading.value = true;
    error.value = null;

    try {
      const { setUpTOTP } = await import("aws-amplify/auth");
      console.log("[Auth] Initiating TOTP setup...");
      const totpSetupDetails = await setUpTOTP();
      const username = user.value?.email || user.value?.username || "BlueMoxon";
      totpSetupUri.value = totpSetupDetails.getSetupUri("BlueMoxon", username).toString();
      console.log("[Auth] TOTP setup URI generated successfully");
      mfaStep.value = "totp_setup";
    } catch (e: unknown) {
      console.error("[Auth] Failed to initiate MFA setup:", e);
      // Provide more specific error messages
      const err = e as { name?: string; message?: string };
      if (err.name === "InvalidParameterException") {
        error.value = "MFA setup failed - please contact administrator";
      } else if (err.message?.includes("not signed in")) {
        error.value = "Session expired. Please sign in again.";
        // Reset auth state
        user.value = null;
        mfaStep.value = "none";
      } else {
        error.value = err.message || "Failed to initiate MFA setup";
      }
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function completeMfaSetup(code: string) {
    loading.value = true;
    error.value = null;

    try {
      const { verifyTOTPSetup, updateMFAPreference } = await import("aws-amplify/auth");
      await verifyTOTPSetup({ code });
      // Set TOTP as preferred MFA method
      await updateMFAPreference({ totp: "PREFERRED" });
      mfaStep.value = "none";
      totpSetupUri.value = null;
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Invalid code";
      error.value = message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function logout() {
    try {
      const { signOut } = await import("aws-amplify/auth");
      await signOut({ global: true });
    } catch (e) {
      console.warn("Error during sign out:", e);
    }

    // Clear dashboard cache
    invalidateDashboardCache();

    // Clear local state
    user.value = null;
    mfaStep.value = "none";
    totpSetupUri.value = null;
    error.value = null;
  }

  async function updateProfile(firstName: string, lastName: string) {
    if (!user.value) return;

    const response = await api.put("/users/me", {
      first_name: firstName,
      last_name: lastName,
    });

    user.value.first_name = response.data.first_name;
    user.value.last_name = response.data.last_name;
  }

  return {
    user,
    loading,
    error,
    mfaStep,
    totpSetupUri,
    authInitializing,
    authError,
    authRetrying,
    isAuthenticated,
    isAdmin,
    isEditor,
    needsMfa,
    checkAuth,
    initializeAuth,
    login,
    confirmTotpCode,
    confirmNewPassword,
    verifyTotpSetup,
    initiateMfaSetup,
    completeMfaSetup,
    logout,
    updateProfile,
  };
});
