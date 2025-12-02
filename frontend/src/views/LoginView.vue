<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const email = ref("");
const password = ref("");
const totpCode = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const localError = ref("");

const error = computed(() => localError.value || authStore.error);

async function handleLogin() {
  localError.value = "";
  try {
    await authStore.login(email.value, password.value);
    // If MFA is needed, the store will set mfaStep
    // Otherwise, we're logged in
    if (authStore.isAuthenticated) {
      const redirect = (route.query.redirect as string) || "/";
      router.push(redirect);
    }
  } catch (e: any) {
    if (e.name === "UserNotConfirmedException") {
      localError.value = "Please verify your email first";
    } else if (e.name === "NotAuthorizedException") {
      localError.value = "Invalid email or password";
    } else {
      localError.value = e.message || "Login failed";
    }
  }
}

async function handleTotpSubmit() {
  localError.value = "";
  try {
    if (authStore.mfaStep === "totp_setup") {
      await authStore.verifyTotpSetup(totpCode.value);
    } else {
      await authStore.confirmTotpCode(totpCode.value);
    }

    if (authStore.isAuthenticated) {
      const redirect = (route.query.redirect as string) || "/";
      router.push(redirect);
    }
  } catch (e: any) {
    localError.value = e.message || "Invalid code";
  }
}

async function handleNewPasswordSubmit() {
  localError.value = "";

  if (newPassword.value !== confirmPassword.value) {
    localError.value = "Passwords do not match";
    return;
  }

  if (newPassword.value.length < 8) {
    localError.value = "Password must be at least 8 characters";
    return;
  }

  // Check for required character types
  if (!/[A-Z]/.test(newPassword.value)) {
    localError.value = "Password must contain at least one uppercase letter";
    return;
  }
  if (!/[a-z]/.test(newPassword.value)) {
    localError.value = "Password must contain at least one lowercase letter";
    return;
  }
  if (!/[0-9]/.test(newPassword.value)) {
    localError.value = "Password must contain at least one number";
    return;
  }

  try {
    await authStore.confirmNewPassword(newPassword.value);

    if (authStore.isAuthenticated) {
      const redirect = (route.query.redirect as string) || "/";
      router.push(redirect);
    }
  } catch (e: any) {
    localError.value = e.message || "Failed to set new password";
  }
}

function resetLogin() {
  authStore.logout();
  email.value = "";
  password.value = "";
  totpCode.value = "";
  newPassword.value = "";
  confirmPassword.value = "";
  localError.value = "";
}
</script>

<template>
  <div class="min-h-[60vh] flex items-center justify-center">
    <div class="card w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-moxon-800">BlueMoxon</h1>
        <p class="text-gray-500 mt-2">
          {{
            authStore.mfaStep === "totp_setup"
              ? "Set up authenticator"
              : authStore.mfaStep === "totp_required"
                ? "Enter verification code"
                : authStore.mfaStep === "new_password_required"
                  ? "Create a new password"
                  : "Sign in to your account"
          }}
        </p>
      </div>

      <!-- Error display -->
      <div v-if="error" class="bg-red-50 text-red-700 p-4 rounded-lg text-sm mb-6">
        {{ error }}
      </div>

      <!-- Login form -->
      <form v-if="authStore.mfaStep === 'none'" @submit.prevent="handleLogin" class="space-y-6">
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700 mb-1"> Email </label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            class="input"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            class="input"
            placeholder="••••••••"
          />
        </div>

        <button type="submit" class="btn-primary w-full" :disabled="authStore.loading">
          {{ authStore.loading ? "Signing in..." : "Sign In" }}
        </button>
      </form>

      <!-- New Password Required -->
      <div v-else-if="authStore.mfaStep === 'new_password_required'" class="space-y-6">
        <div class="bg-blue-50 text-blue-800 p-4 rounded-lg text-sm">
          <p class="font-medium mb-2">Welcome to BlueMoxon!</p>
          <p>Please create a new password to secure your account.</p>
        </div>

        <form @submit.prevent="handleNewPasswordSubmit" class="space-y-4">
          <div>
            <label for="newPassword" class="block text-sm font-medium text-gray-700 mb-1">
              New Password
            </label>
            <input
              id="newPassword"
              v-model="newPassword"
              type="password"
              required
              minlength="8"
              class="input"
              placeholder="Enter new password"
            />
          </div>

          <div>
            <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-1">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              required
              minlength="8"
              class="input"
              placeholder="Confirm new password"
            />
          </div>

          <div class="text-xs text-gray-500 space-y-1">
            <p class="font-medium">Password requirements:</p>
            <ul class="list-disc list-inside">
              <li>At least 8 characters</li>
              <li>Uppercase and lowercase letters</li>
              <li>At least one number</li>
            </ul>
          </div>

          <button
            type="submit"
            class="btn-primary w-full"
            :disabled="authStore.loading || newPassword.length < 8 || confirmPassword.length < 8"
          >
            {{ authStore.loading ? "Setting password..." : "Set Password" }}
          </button>
        </form>

        <button @click="resetLogin" class="w-full text-sm text-gray-500 hover:text-gray-700">
          Use a different account
        </button>
      </div>

      <!-- TOTP Setup (first time) -->
      <div v-else-if="authStore.mfaStep === 'totp_setup'" class="space-y-6">
        <div class="bg-blue-50 text-blue-800 p-4 rounded-lg text-sm">
          <p class="font-medium mb-2">Set up two-factor authentication</p>
          <p>
            Scan this QR code with your authenticator app (Google Authenticator, Authy, 1Password,
            etc.)
          </p>
        </div>

        <!-- QR Code -->
        <div class="flex justify-center">
          <img
            :src="`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(authStore.totpSetupUri || '')}`"
            alt="TOTP QR Code"
            class="border rounded-lg"
            width="200"
            height="200"
          />
        </div>

        <!-- Manual entry option -->
        <details class="text-sm text-gray-600">
          <summary class="cursor-pointer hover:text-gray-800">Can't scan? Enter manually</summary>
          <code class="block mt-2 p-2 bg-gray-100 rounded text-xs break-all">
            {{ authStore.totpSetupUri }}
          </code>
        </details>

        <form @submit.prevent="handleTotpSubmit" class="space-y-4">
          <div>
            <label for="totp" class="block text-sm font-medium text-gray-700 mb-1">
              Enter 6-digit code from your app
            </label>
            <input
              id="totp"
              v-model="totpCode"
              type="text"
              inputmode="numeric"
              pattern="[0-9]{6}"
              maxlength="6"
              required
              class="input text-center text-2xl tracking-widest"
              placeholder="000000"
              autocomplete="one-time-code"
            />
          </div>

          <button
            type="submit"
            class="btn-primary w-full"
            :disabled="authStore.loading || totpCode.length !== 6"
          >
            {{ authStore.loading ? "Verifying..." : "Verify & Complete Setup" }}
          </button>
        </form>

        <button @click="resetLogin" class="w-full text-sm text-gray-500 hover:text-gray-700">
          Cancel and start over
        </button>
      </div>

      <!-- TOTP Required (returning user) -->
      <div v-else-if="authStore.mfaStep === 'totp_required'" class="space-y-6">
        <div class="bg-gray-50 text-gray-700 p-4 rounded-lg text-sm">
          Enter the 6-digit code from your authenticator app
        </div>

        <form @submit.prevent="handleTotpSubmit" class="space-y-4">
          <div>
            <label for="totp" class="block text-sm font-medium text-gray-700 mb-1">
              Verification Code
            </label>
            <input
              id="totp"
              v-model="totpCode"
              type="text"
              inputmode="numeric"
              pattern="[0-9]{6}"
              maxlength="6"
              required
              class="input text-center text-2xl tracking-widest"
              placeholder="000000"
              autocomplete="one-time-code"
            />
          </div>

          <button
            type="submit"
            class="btn-primary w-full"
            :disabled="authStore.loading || totpCode.length !== 6"
          >
            {{ authStore.loading ? "Verifying..." : "Verify" }}
          </button>
        </form>

        <button @click="resetLogin" class="w-full text-sm text-gray-500 hover:text-gray-700">
          Use a different account
        </button>
      </div>

      <p v-if="authStore.mfaStep === 'none'" class="text-center text-sm text-gray-500 mt-6">
        Contact administrator for access
      </p>
    </div>
  </div>
</template>
