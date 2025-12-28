<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();

// Profile editing
const firstName = ref("");
const lastName = ref("");
const profileLoading = ref(false);
const profileError = ref("");
const profileSuccess = ref("");

// Password change
const currentPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const loading = ref(false);
const error = ref("");
const success = ref("");

onMounted(() => {
  firstName.value = authStore.user?.first_name || "";
  lastName.value = authStore.user?.last_name || "";
});

async function handleUpdateProfile() {
  profileError.value = "";
  profileSuccess.value = "";
  profileLoading.value = true;

  try {
    await authStore.updateProfile(firstName.value, lastName.value);
    profileSuccess.value = "Profile updated successfully";
  } catch (e: any) {
    profileError.value = e.message || "Failed to update profile";
  } finally {
    profileLoading.value = false;
  }
}

async function handleChangePassword() {
  error.value = "";
  success.value = "";

  if (newPassword.value !== confirmPassword.value) {
    error.value = "New passwords do not match";
    return;
  }

  if (newPassword.value.length < 8) {
    error.value = "Password must be at least 8 characters";
    return;
  }

  loading.value = true;
  try {
    const { updatePassword } = await import("aws-amplify/auth");
    await updatePassword({
      oldPassword: currentPassword.value,
      newPassword: newPassword.value,
    });
    success.value = "Password changed successfully";
    currentPassword.value = "";
    newPassword.value = "";
    confirmPassword.value = "";
  } catch (e: any) {
    if (e.name === "NotAuthorizedException") {
      error.value = "Current password is incorrect";
    } else if (e.name === "InvalidPasswordException") {
      error.value = "Password does not meet requirements (8+ chars, upper, lower, number)";
    } else {
      error.value = e.message || "Failed to change password";
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-moxon-800 mb-8">Profile Settings</h1>

    <!-- Profile Information -->
    <div class="card mb-8">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Profile Information</h2>

      <div v-if="profileError" class="bg-red-50 text-red-700 p-4 rounded-lg text-sm mb-4">
        {{ profileError }}
      </div>

      <div v-if="profileSuccess" class="bg-green-50 text-green-700 p-4 rounded-lg text-sm mb-4">
        {{ profileSuccess }}
      </div>

      <form @submit.prevent="handleUpdateProfile" class="flex flex-col gap-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="firstName" class="block text-sm font-medium text-gray-700 mb-1">
              First Name
            </label>
            <input
              id="firstName"
              v-model="firstName"
              type="text"
              class="input"
              placeholder="Enter your first name"
            />
          </div>
          <div>
            <label for="lastName" class="block text-sm font-medium text-gray-700 mb-1">
              Last Name
            </label>
            <input
              id="lastName"
              v-model="lastName"
              type="text"
              class="input"
              placeholder="Enter your last name"
            />
          </div>
        </div>

        <dl class="flex flex-col gap-3 pt-4 border-t">
          <div>
            <dt class="text-sm text-gray-500">Email</dt>
            <dd class="text-gray-800">{{ authStore.user?.email }}</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500">Role</dt>
            <dd class="text-gray-800 capitalize">
              {{ authStore.user?.role || "viewer" }}
            </dd>
          </div>
        </dl>

        <button type="submit" class="btn-primary" :disabled="profileLoading">
          {{ profileLoading ? "Saving..." : "Save Profile" }}
        </button>
      </form>
    </div>

    <!-- Change Password -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Change Password</h2>

      <div v-if="error" class="bg-red-50 text-red-700 p-4 rounded-lg text-sm mb-4">
        {{ error }}
      </div>

      <div v-if="success" class="bg-green-50 text-green-700 p-4 rounded-lg text-sm mb-4">
        {{ success }}
      </div>

      <form @submit.prevent="handleChangePassword" class="flex flex-col gap-4">
        <div>
          <label for="currentPassword" class="block text-sm font-medium text-gray-700 mb-1">
            Current Password
          </label>
          <input
            id="currentPassword"
            v-model="currentPassword"
            type="password"
            required
            class="input"
            autocomplete="current-password"
          />
        </div>

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
            autocomplete="new-password"
          />
          <p class="text-xs text-gray-500 mt-1">
            At least 8 characters with uppercase, lowercase, and number
          </p>
        </div>

        <div>
          <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-1">
            Confirm New Password
          </label>
          <input
            id="confirmPassword"
            v-model="confirmPassword"
            type="password"
            required
            class="input"
            autocomplete="new-password"
          />
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? "Changing..." : "Change Password" }}
        </button>
      </form>
    </div>

    <!-- Security Info -->
    <div class="card mt-8">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Security</h2>
      <div class="flex items-center text-sm">
        <svg class="w-5 h-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path
            fill-rule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clip-rule="evenodd"
          />
        </svg>
        <span class="text-gray-700">Two-factor authentication enabled (TOTP)</span>
      </div>
    </div>
  </div>
</template>
