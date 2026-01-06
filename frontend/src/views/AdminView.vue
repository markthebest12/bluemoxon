<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useAdminStore } from "@/stores/admin";

const router = useRouter();
const authStore = useAuthStore();
const adminStore = useAdminStore();

const activeTab = ref<"users" | "apikeys">("users");
const newKeyName = ref("");
const showNewKeyModal = ref(false);
const confirmDeleteUser = ref<number | null>(null);

// Invite user state
const inviteEmail = ref("");
const inviteRole = ref("viewer");
const inviteMfaExempt = ref(false);
const inviteLoading = ref(false);
const inviteSuccess = ref<string | null>(null);

// Impersonation modal
const showImpersonateModal = ref(false);
const mfaLoading = ref<number | null>(null);

// Password reset modal
const showResetPasswordModal = ref(false);
const resetPasswordUserId = ref<number | null>(null);
const resetPasswordEmail = ref("");
const resetNewPassword = ref("");
const resetPasswordLoading = ref(false);
const resetPasswordSuccess = ref(false);

onMounted(async () => {
  // Redirect if not admin
  if (!authStore.isAdmin) {
    void router.push("/");
    return;
  }

  await Promise.all([adminStore.fetchUsers(), adminStore.fetchAPIKeys()]);

  // Load MFA status for each user (in background)
  for (const user of adminStore.users) {
    void loadMfaStatus(user.id);
  }
});

async function updateRole(userId: number, newRole: string) {
  try {
    await adminStore.updateUserRole(userId, newRole);
  } catch {
    // Error is set in store
  }
}

async function deleteUser(userId: number) {
  try {
    await adminStore.deleteUser(userId);
    confirmDeleteUser.value = null;
  } catch {
    // Error is set in store
  }
}

async function inviteUser() {
  if (!inviteEmail.value.trim()) return;

  inviteLoading.value = true;
  inviteSuccess.value = null;

  try {
    await adminStore.inviteUser(inviteEmail.value.trim(), inviteRole.value, inviteMfaExempt.value);
    const exemptNote = inviteMfaExempt.value ? " (MFA exempt)" : "";
    inviteSuccess.value = `Invitation sent to ${inviteEmail.value}${exemptNote}`;
    inviteEmail.value = "";
    inviteRole.value = "viewer";
    inviteMfaExempt.value = false;
  } catch {
    // Error is set in store
  } finally {
    inviteLoading.value = false;
  }
}

async function createKey() {
  if (!newKeyName.value.trim()) return;

  try {
    await adminStore.createAPIKey(newKeyName.value.trim());
    newKeyName.value = "";
    showNewKeyModal.value = true;
  } catch {
    // Error is set in store
  }
}

async function revokeKey(keyId: number) {
  if (!confirm("Are you sure you want to revoke this API key? This cannot be undone.")) {
    return;
  }

  try {
    await adminStore.revokeAPIKey(keyId);
  } catch {
    // Error is set in store
  }
}

const copySuccess = ref(false);

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).then(
    () => {
      copySuccess.value = true;
      setTimeout(() => {
        copySuccess.value = false;
      }, 2000);
    },
    (err) => {
      console.error("Copy failed:", err);
      alert("Failed to copy to clipboard");
    }
  );
}

async function toggleMfa(userId: number, currentlyEnabled: boolean | undefined) {
  mfaLoading.value = userId;
  try {
    if (currentlyEnabled) {
      await adminStore.disableUserMfa(userId);
    } else {
      await adminStore.enableUserMfa(userId);
    }
  } catch {
    // Error is set in store
  } finally {
    mfaLoading.value = null;
  }
}

async function loadMfaStatus(userId: number) {
  try {
    await adminStore.getUserMfaStatus(userId);
  } catch {
    // Silently fail - MFA status just won't show
  }
}

async function impersonateUser(userId: number) {
  try {
    await adminStore.impersonateUser(userId);
    showImpersonateModal.value = true;
  } catch {
    // Error is set in store
  }
}

function openResetPasswordModal(userId: number, email: string) {
  resetPasswordUserId.value = userId;
  resetPasswordEmail.value = email;
  resetNewPassword.value = "";
  resetPasswordSuccess.value = false;
  showResetPasswordModal.value = true;
}

function closeResetPasswordModal() {
  showResetPasswordModal.value = false;
  resetPasswordUserId.value = null;
  resetPasswordEmail.value = "";
  resetNewPassword.value = "";
  resetPasswordSuccess.value = false;
}

async function handleResetPassword() {
  if (!resetPasswordUserId.value || !resetNewPassword.value) return;

  resetPasswordLoading.value = true;
  try {
    await adminStore.resetUserPassword(resetPasswordUserId.value, resetNewPassword.value);
    resetPasswordSuccess.value = true;
    resetNewPassword.value = "";
  } catch {
    // Error is set in store
  } finally {
    resetPasswordLoading.value = false;
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Never";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
</script>

<template>
  <div class="max-w-6xl mx-auto">
    <h1 class="text-2xl sm:text-3xl font-bold text-gray-800 mb-6">Admin Settings</h1>

    <!-- Error display -->
    <div
      v-if="adminStore.error"
      class="mb-4 p-4 bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] text-[var(--color-status-error-text)] rounded-sm"
    >
      {{ adminStore.error }}
    </div>

    <!-- Tabs -->
    <div class="flex border-b mb-6">
      <button
        class="px-4 py-2 font-medium transition-colors"
        :class="
          activeTab === 'users'
            ? 'border-b-2 border-moxon-600 text-moxon-600'
            : 'text-gray-500 hover:text-gray-700'
        "
        @click="activeTab = 'users'"
      >
        Users
      </button>
      <button
        class="px-4 py-2 font-medium transition-colors"
        :class="
          activeTab === 'apikeys'
            ? 'border-b-2 border-moxon-600 text-moxon-600'
            : 'text-gray-500 hover:text-gray-700'
        "
        @click="activeTab = 'apikeys'"
      >
        API Keys
      </button>
    </div>

    <!-- Users Tab -->
    <div v-if="activeTab === 'users'">
      <!-- Invite user form -->
      <div class="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 class="text-lg font-medium text-gray-800 mb-3">Invite New User</h3>
        <div
          v-if="inviteSuccess"
          class="mb-3 p-3 bg-[var(--color-status-success-bg)] border border-[var(--color-status-success-border)] text-[var(--color-status-success-text)] rounded-sm text-sm"
        >
          {{ inviteSuccess }}
        </div>
        <div class="flex gap-2 flex-wrap">
          <input
            v-model="inviteEmail"
            type="email"
            placeholder="Email address"
            class="flex-1 min-w-[200px] input"
            @keyup.enter="inviteUser"
          />
          <select v-model="inviteRole" class="input w-auto">
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
            <option value="admin">Admin</option>
          </select>
          <button
            class="btn-primary"
            :disabled="!inviteEmail.trim() || inviteLoading"
            @click="inviteUser"
          >
            {{ inviteLoading ? "Sending..." : "Send Invite" }}
          </button>
        </div>
        <label class="flex items-center gap-2 mt-2 text-sm text-gray-600 cursor-pointer">
          <input
            v-model="inviteMfaExempt"
            type="checkbox"
            class="rounded-sm border-gray-300 text-moxon-600 focus:ring-moxon-500"
          />
          <span>MFA Exempt (user won't be required to set up two-factor authentication)</span>
        </label>
        <p class="text-xs text-gray-500 mt-2">
          User will receive an email with a temporary password to set up their account.
        </p>
      </div>

      <div v-if="adminStore.loading" class="text-center py-8 text-gray-500">Loading users...</div>

      <div v-else class="flex flex-col gap-3">
        <div
          v-for="user in adminStore.users"
          :key="user.id"
          class="bg-white rounded-lg shadow-sm p-4"
        >
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div class="min-w-0">
              <div class="text-sm font-medium text-gray-900 break-all sm:truncate">
                {{ user.first_name || user.email }}
              </div>
              <div class="text-xs text-gray-500 break-all sm:truncate">
                {{ user.first_name ? user.email : "" }} ID: {{ user.id }}
                <span v-if="user.mfa_enabled !== undefined" class="ml-2">
                  <span v-if="user.mfa_enabled" class="text-[var(--color-status-success-accent)]"
                    >MFA Active</span
                  >
                  <span
                    v-else-if="user.mfa_configured"
                    class="text-[var(--color-status-warning-accent)]"
                    >MFA Off</span
                  >
                  <span v-else class="text-[var(--color-text-muted)]">MFA Pending</span>
                </span>
              </div>
            </div>
            <div class="flex items-center gap-2 flex-wrap">
              <select
                :value="user.role"
                class="text-sm border rounded-sm px-2 py-1"
                :class="{
                  'bg-purple-100 text-purple-800': user.role === 'admin',
                  'badge-transit': user.role === 'editor',
                  'bg-gray-100 text-gray-800': user.role === 'viewer',
                }"
                @change="updateRole(user.id, ($event.target as HTMLSelectElement).value)"
              >
                <option value="viewer">Viewer</option>
                <option value="editor">Editor</option>
                <option value="admin">Admin</option>
              </select>
              <!-- MFA Toggle - enable/disable MFA for user -->
              <button
                :disabled="mfaLoading === user.id || (!user.mfa_enabled && !user.mfa_configured)"
                class="text-xs px-2 py-1 rounded-sm border"
                :class="
                  user.mfa_enabled
                    ? 'border-[var(--color-status-warning-border)] text-[var(--color-status-warning-text)] hover:bg-[var(--color-status-warning-bg)]'
                    : user.mfa_configured
                      ? 'border-[var(--color-status-success-border)] text-[var(--color-status-success-text)] hover:bg-[var(--color-status-success-bg)]'
                      : 'border-[var(--color-border-default)] text-[var(--color-text-muted)] cursor-not-allowed'
                "
                :title="
                  user.mfa_enabled
                    ? 'Disable MFA for this user'
                    : user.mfa_configured
                      ? 'Re-enable MFA for this user'
                      : 'User has not completed MFA setup yet'
                "
                @click="toggleMfa(user.id, user.mfa_enabled)"
              >
                {{
                  mfaLoading === user.id
                    ? "..."
                    : user.mfa_enabled
                      ? "Make Exempt"
                      : user.mfa_configured
                        ? "Enable MFA"
                        : "Pending Setup"
                }}
              </button>
              <!-- Reset Password (not for self) -->
              <button
                v-if="authStore.user?.email !== user.email"
                class="text-xs px-2 py-1 rounded-sm border border-amber-300 text-amber-700 hover:bg-amber-50"
                @click="openResetPasswordModal(user.id, user.email)"
              >
                Reset PW
              </button>
              <!-- Impersonate (not for self) -->
              <button
                v-if="authStore.user?.email !== user.email"
                class="text-xs px-2 py-1 rounded-sm border border-victorian-hunter-300 text-victorian-hunter-700 hover:bg-victorian-paper-aged"
                @click="impersonateUser(user.id)"
              >
                Login As
              </button>
              <!-- Delete -->
              <div v-if="confirmDeleteUser !== user.id">
                <button
                  class="text-[var(--color-status-error-accent)] hover:text-[var(--color-status-error-text)] text-sm"
                  @click="confirmDeleteUser = user.id"
                >
                  Delete
                </button>
              </div>
              <div v-else class="flex items-center gap-2">
                <button
                  class="px-2 py-1 bg-[var(--color-status-error-solid)] text-[var(--color-status-error-solid-text)] text-xs rounded-sm hover:opacity-90"
                  @click="deleteUser(user.id)"
                >
                  Yes
                </button>
                <button
                  class="px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded-sm hover:bg-gray-300"
                  @click="confirmDeleteUser = null"
                >
                  No
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- API Keys Tab -->
    <div v-if="activeTab === 'apikeys'">
      <!-- Create new key form -->
      <div class="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 class="text-lg font-medium text-gray-800 mb-3">Create New API Key</h3>
        <div class="flex gap-2">
          <input
            v-model="newKeyName"
            type="text"
            placeholder="Key name (e.g., 'CLI Tool', 'Import Script')"
            class="flex-1 input"
            @keyup.enter="createKey"
          />
          <button class="btn-primary" :disabled="!newKeyName.trim()" @click="createKey">
            Create Key
          </button>
        </div>
      </div>

      <div v-if="adminStore.loading" class="text-center py-8 text-gray-500">
        Loading API keys...
      </div>

      <div v-else class="bg-white rounded-lg shadow-sm overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Name
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Key Prefix
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Created
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Last Used
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Status
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr
              v-for="key in adminStore.apiKeys"
              :key="key.id"
              :class="{ 'opacity-50': !key.is_active }"
            >
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{{ key.name }}</div>
                <div class="text-xs text-gray-500">by {{ key.created_by_email || "Unknown" }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <code class="text-sm bg-gray-100 px-2 py-1 rounded-sm"
                  >{{ key.key_prefix }}...</code
                >
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDate(key.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDate(key.last_used_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  class="px-2 py-1 text-xs rounded-full"
                  :class="
                    key.is_active
                      ? 'bg-[var(--color-status-success-bg)] text-[var(--color-status-success-text)]'
                      : 'bg-[var(--color-status-error-bg)] text-[var(--color-status-error-text)]'
                  "
                >
                  {{ key.is_active ? "Active" : "Revoked" }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <button
                  v-if="key.is_active"
                  class="text-[var(--color-status-error-accent)] hover:text-[var(--color-status-error-text)]"
                  @click="revokeKey(key.id)"
                >
                  Revoke
                </button>
                <span v-else class="text-gray-400">-</span>
              </td>
            </tr>
            <tr v-if="adminStore.apiKeys.length === 0">
              <td colspan="6" class="px-6 py-8 text-center text-gray-500">
                No API keys created yet
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- New Key Modal -->
    <div
      v-if="showNewKeyModal && adminStore.newlyCreatedKey"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="
        showNewKeyModal = false;
        adminStore.clearNewKey();
      "
    >
      <div class="bg-white rounded-lg p-6 max-w-lg w-full mx-4 shadow-xl">
        <h3 class="text-lg font-bold text-gray-800 mb-2">API Key Created</h3>
        <p class="text-sm text-amber-600 mb-4">Save this key now - it won't be shown again!</p>

        <div class="bg-gray-100 p-4 rounded-lg mb-4">
          <label class="block text-xs text-gray-500 mb-1">API Key</label>
          <div class="flex items-center gap-2">
            <code class="flex-1 text-sm break-all">{{ adminStore.newlyCreatedKey.key }}</code>
            <button
              class="px-3 py-1 bg-moxon-600 text-white text-sm rounded-sm hover:bg-moxon-700"
              @click="copyToClipboard(adminStore.newlyCreatedKey!.key)"
            >
              {{ copySuccess ? "Copied!" : "Copy" }}
            </button>
          </div>
        </div>

        <p class="text-sm text-gray-600 mb-4">
          Use this key in the <code class="bg-gray-100 px-1 rounded-sm">X-API-Key</code> header for
          API requests.
        </p>

        <div class="flex justify-end">
          <button
            class="btn-primary"
            @click="
              showNewKeyModal = false;
              adminStore.clearNewKey();
            "
          >
            Done
          </button>
        </div>
      </div>
    </div>

    <!-- Impersonation Modal -->
    <div
      v-if="showImpersonateModal && adminStore.impersonationCredentials"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="
        showImpersonateModal = false;
        adminStore.clearImpersonation();
      "
    >
      <div class="bg-white rounded-lg p-6 max-w-lg w-full mx-4 shadow-xl">
        <h3 class="text-lg font-bold text-gray-800 mb-2">Login As User</h3>
        <p class="text-sm text-amber-600 mb-4">
          Temporary credentials generated. The user's password has been changed.
        </p>

        <div class="flex flex-col gap-3 mb-4">
          <div class="bg-gray-100 p-3 rounded-lg">
            <label class="block text-xs text-gray-500 mb-1">Email</label>
            <div class="flex items-center gap-2">
              <code class="flex-1 text-sm">{{ adminStore.impersonationCredentials.email }}</code>
              <button
                class="px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded-sm hover:bg-gray-300"
                @click="copyToClipboard(adminStore.impersonationCredentials!.email)"
              >
                {{ copySuccess ? "Copied!" : "Copy" }}
              </button>
            </div>
          </div>
          <div class="bg-gray-100 p-3 rounded-lg">
            <label class="block text-xs text-gray-500 mb-1">Temporary Password</label>
            <div class="flex items-center gap-2">
              <code class="flex-1 text-sm break-all">{{
                adminStore.impersonationCredentials.temp_password
              }}</code>
              <button
                class="px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded-sm hover:bg-gray-300"
                @click="copyToClipboard(adminStore.impersonationCredentials!.temp_password)"
              >
                {{ copySuccess ? "Copied!" : "Copy" }}
              </button>
            </div>
          </div>
        </div>

        <p class="text-sm text-gray-600 mb-4">
          Sign out and use these credentials to log in as this user. Remember to notify the user to
          reset their password afterward.
        </p>

        <div class="flex justify-end gap-2">
          <button
            class="px-4 py-2 bg-gray-200 text-gray-700 rounded-sm hover:bg-gray-300"
            @click="
              showImpersonateModal = false;
              adminStore.clearImpersonation();
            "
          >
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Reset Password Modal -->
    <div
      v-if="showResetPasswordModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeResetPasswordModal"
    >
      <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
        <h3 class="text-lg font-bold text-gray-800 mb-2">Reset Password</h3>
        <p class="text-sm text-gray-600 mb-4">
          Set a new password for <span class="font-medium">{{ resetPasswordEmail }}</span>
        </p>

        <div
          v-if="adminStore.error"
          class="mb-4 p-3 bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] text-[var(--color-status-error-text)] rounded-sm text-sm"
        >
          {{ adminStore.error }}
        </div>

        <div
          v-if="resetPasswordSuccess"
          class="mb-4 p-3 bg-[var(--color-status-success-bg)] border border-[var(--color-status-success-border)] text-[var(--color-status-success-text)] rounded-sm text-sm"
        >
          Password reset successfully! The user can now log in with the new password.
        </div>

        <form
          v-if="!resetPasswordSuccess"
          class="flex flex-col gap-4"
          @submit.prevent="handleResetPassword"
        >
          <div>
            <label for="resetNewPassword" class="block text-sm font-medium text-gray-700 mb-1">
              New Password
            </label>
            <input
              id="resetNewPassword"
              v-model="resetNewPassword"
              type="password"
              required
              minlength="8"
              class="input"
              placeholder="Enter new password"
              autocomplete="new-password"
            />
            <p class="text-xs text-gray-500 mt-1">
              At least 8 characters with uppercase, lowercase, and number
            </p>
          </div>

          <div class="flex justify-end gap-2">
            <button
              type="button"
              class="px-4 py-2 bg-gray-200 text-gray-700 rounded-sm hover:bg-gray-300"
              @click="closeResetPasswordModal"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="resetPasswordLoading || resetNewPassword.length < 8"
            >
              {{ resetPasswordLoading ? "Resetting..." : "Reset Password" }}
            </button>
          </div>
        </form>

        <div v-else class="flex justify-end">
          <button class="btn-primary" @click="closeResetPasswordModal">Done</button>
        </div>
      </div>
    </div>
  </div>
</template>
