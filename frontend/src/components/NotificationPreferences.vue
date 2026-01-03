<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { api } from "@/services/api";

interface UserPreferences {
  notify_tracking_email: boolean;
  notify_tracking_sms: boolean;
  phone_number: string | null;
}

const notifyEmail = ref(false);
const notifySms = ref(false);
const phoneNumber = ref<string | null>(null);

const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);
const success = ref<string | null>(null);

async function fetchPreferences() {
  loading.value = true;
  error.value = null;
  try {
    const response = await api.get<UserPreferences>("/users/me/preferences");
    notifyEmail.value = response.data.notify_tracking_email;
    notifySms.value = response.data.notify_tracking_sms;
    phoneNumber.value = response.data.phone_number;
  } catch (e: any) {
    console.error("Failed to fetch preferences:", e);
    error.value = "Failed to load preferences";
  } finally {
    loading.value = false;
  }
}

async function savePreferences() {
  saving.value = true;
  error.value = null;
  success.value = null;

  try {
    const payload: UserPreferences = {
      notify_tracking_email: notifyEmail.value,
      notify_tracking_sms: notifySms.value,
      // Clear phone number if SMS is disabled
      phone_number: notifySms.value ? phoneNumber.value : null,
    };

    await api.patch<UserPreferences>("/users/me/preferences", payload);
    success.value = "Preferences saved successfully";

    // Clear success message after 3 seconds
    setTimeout(() => {
      success.value = null;
    }, 3000);
  } catch (e: any) {
    console.error("Failed to save preferences:", e);
    error.value = "Failed to save preferences";
  } finally {
    saving.value = false;
  }
}

// Clear phone number input when SMS is disabled
watch(notifySms, (newValue) => {
  if (!newValue) {
    phoneNumber.value = null;
  }
});

onMounted(() => {
  void fetchPreferences();
});
</script>

<template>
  <div class="card">
    <h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-4">
      Notification Preferences
    </h2>

    <p class="text-sm text-[var(--color-text-secondary)] mb-6">
      Choose how you want to receive updates about your book shipments.
    </p>

    <!-- Error Message -->
    <div
      v-if="error"
      class="bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] text-[var(--color-status-error-text)] p-3 rounded-lg text-sm mb-4"
    >
      {{ error }}
    </div>

    <!-- Success Message -->
    <div
      v-if="success"
      class="bg-[var(--color-status-success-bg)] border border-[var(--color-status-success-border)] text-[var(--color-status-success-text)] p-3 rounded-lg text-sm mb-4"
    >
      {{ success }}
    </div>

    <div class="flex flex-col gap-6">
      <!-- Email Notifications Toggle -->
      <div class="flex items-center justify-between">
        <div>
          <label for="email-toggle" class="text-sm font-medium text-[var(--color-text-primary)]">
            Email Notifications
          </label>
          <p class="text-xs text-[var(--color-text-secondary)] mt-0.5">
            Receive tracking updates via email
          </p>
        </div>
        <label class="relative inline-flex items-center cursor-pointer">
          <input
            id="email-toggle"
            v-model="notifyEmail"
            type="checkbox"
            data-testid="email-toggle"
            class="sr-only peer"
          />
          <div
            class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-victorian-hunter-300 dark:peer-focus:ring-victorian-hunter-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-victorian-hunter-600"
          />
        </label>
      </div>

      <!-- SMS Notifications Toggle -->
      <div class="flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <div>
            <label for="sms-toggle" class="text-sm font-medium text-[var(--color-text-primary)]">
              SMS Notifications
            </label>
            <p class="text-xs text-[var(--color-text-secondary)] mt-0.5">
              Receive tracking updates via text message
            </p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input
              id="sms-toggle"
              v-model="notifySms"
              type="checkbox"
              data-testid="sms-toggle"
              class="sr-only peer"
            />
            <div
              class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-victorian-hunter-300 dark:peer-focus:ring-victorian-hunter-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-victorian-hunter-600"
            />
          </label>
        </div>

        <!-- Phone Number Input (shown only when SMS is enabled) -->
        <div v-if="notifySms" class="ml-0 pl-0">
          <label
            for="phone-input"
            class="block text-sm font-medium text-[var(--color-text-primary)] mb-1"
          >
            Phone Number
          </label>
          <input
            id="phone-input"
            v-model="phoneNumber"
            type="tel"
            data-testid="phone-input"
            placeholder="+1 (555) 123-4567"
            class="input w-full max-w-xs"
          />
          <p class="text-xs text-[var(--color-text-secondary)] mt-1">
            Include country code (e.g., +1 for US)
          </p>
        </div>
      </div>
    </div>

    <!-- Save Button -->
    <div class="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
      <button
        data-testid="save-button"
        @click="savePreferences"
        :disabled="loading || saving"
        class="btn-primary"
      >
        {{ saving ? "Saving..." : "Save Preferences" }}
      </button>
    </div>
  </div>
</template>
