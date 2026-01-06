import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";
import { invalidateDashboardCache } from "@/composables/useDashboardCache";

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

export const useAuthStore = defineStore("auth", () => {
  const user = ref<User | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const mfaStep = ref<MfaStep>("none");
  const totpSetupUri = ref<string | null>(null);

  const isAuthenticated = computed(() => !!user.value);
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

      // Fetch actual role and profile from our backend database FIRST
      // (we need mfa_exempt before deciding on MFA requirement)
      let isMfaExempt = false;
      try {
        const response = await api.get("/users/me");
        if (response.data.role) {
          user.value.role = response.data.role;
        }
        if (response.data.first_name) {
          user.value.first_name = response.data.first_name;
        }
        if (response.data.last_name) {
          user.value.last_name = response.data.last_name;
        }
        isMfaExempt = response.data.mfa_exempt === true;
        user.value.mfa_exempt = isMfaExempt;
      } catch (e) {
        console.warn("Could not fetch user profile from API:", e);
      }

      // Check if user has MFA set up (skip if MFA-exempt)
      if (!isMfaExempt) {
        try {
          const mfaPreference = await fetchMFAPreference();
          const hasMfa =
            mfaPreference.preferred === "TOTP" || mfaPreference.enabled?.includes("TOTP");
          if (!hasMfa) {
            // User needs to set up MFA
            mfaStep.value = "mfa_setup_required";
          } else {
            mfaStep.value = "none";
          }
        } catch (e) {
          console.warn("Could not fetch MFA preference:", e);
          mfaStep.value = "none";
        }
      } else {
        // User is MFA-exempt, skip MFA check
        mfaStep.value = "none";
      }
    } catch (e) {
      // Session check failed - clear user silently (no toast to avoid spam on page load)
      console.error("[Auth] Session check failed:", e);
      user.value = null;
    } finally {
      loading.value = false;
    }
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

    // Always clear local state
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
    isAuthenticated,
    isAdmin,
    isEditor,
    needsMfa,
    checkAuth,
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
