import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";

interface User {
  username: string;
  email: string;
  role: string;
}

type MfaStep = "none" | "totp_required" | "totp_setup" | "new_password_required";

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
    try {
      const { getCurrentUser } = await import("aws-amplify/auth");
      const currentUser = await getCurrentUser();

      // Basic user info from Cognito
      user.value = {
        username: currentUser.username,
        email: currentUser.signInDetails?.loginId || "",
        role: "viewer", // Default, will be updated from API
      };
      mfaStep.value = "none";

      // Fetch actual role from our backend database
      try {
        const response = await api.get("/users/me");
        if (response.data.role) {
          user.value.role = response.data.role;
        }
      } catch (e) {
        console.warn("Could not fetch user role from API:", e);
      }
    } catch {
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
      const { signIn } = await import("aws-amplify/auth");
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
    } catch (e: any) {
      error.value = e.message || "Login failed";
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
    } catch (e: any) {
      error.value = e.message || "Invalid code";
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
    } catch (e: any) {
      error.value = e.message || "Failed to set new password";
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
    } catch (e: any) {
      error.value = e.message || "Invalid code";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function logout() {
    const { signOut } = await import("aws-amplify/auth");
    await signOut();
    user.value = null;
    mfaStep.value = "none";
    totpSetupUri.value = null;
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
    logout,
  };
});
