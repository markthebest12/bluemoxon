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

onMounted(async () => {
  // Redirect if not admin
  if (!authStore.isAdmin) {
    router.push("/");
    return;
  }

  await Promise.all([adminStore.fetchUsers(), adminStore.fetchAPIKeys()]);
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

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text);
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
      class="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded"
    >
      {{ adminStore.error }}
    </div>

    <!-- Tabs -->
    <div class="flex border-b mb-6">
      <button
        @click="activeTab = 'users'"
        class="px-4 py-2 font-medium transition-colors"
        :class="
          activeTab === 'users'
            ? 'border-b-2 border-moxon-600 text-moxon-600'
            : 'text-gray-500 hover:text-gray-700'
        "
      >
        Users
      </button>
      <button
        @click="activeTab = 'apikeys'"
        class="px-4 py-2 font-medium transition-colors"
        :class="
          activeTab === 'apikeys'
            ? 'border-b-2 border-moxon-600 text-moxon-600'
            : 'text-gray-500 hover:text-gray-700'
        "
      >
        API Keys
      </button>
    </div>

    <!-- Users Tab -->
    <div v-if="activeTab === 'users'">
      <div v-if="adminStore.loading" class="text-center py-8 text-gray-500">Loading users...</div>

      <div v-else class="bg-white rounded-lg shadow overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Email
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Role
              </th>
              <th
                class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="user in adminStore.users" :key="user.id">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{{ user.email }}</div>
                <div class="text-xs text-gray-500">ID: {{ user.id }}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <select
                  :value="user.role"
                  @change="updateRole(user.id, ($event.target as HTMLSelectElement).value)"
                  class="text-sm border rounded px-2 py-1"
                  :class="{
                    'bg-purple-100 text-purple-800': user.role === 'admin',
                    'bg-blue-100 text-blue-800': user.role === 'editor',
                    'bg-gray-100 text-gray-800': user.role === 'viewer',
                  }"
                >
                  <option value="viewer">Viewer</option>
                  <option value="editor">Editor</option>
                  <option value="admin">Admin</option>
                </select>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <button
                  v-if="confirmDeleteUser !== user.id"
                  @click="confirmDeleteUser = user.id"
                  class="text-red-600 hover:text-red-800"
                >
                  Delete
                </button>
                <div v-else class="flex items-center gap-2">
                  <span class="text-red-600 text-xs">Confirm?</span>
                  <button
                    @click="deleteUser(user.id)"
                    class="px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                  >
                    Yes
                  </button>
                  <button
                    @click="confirmDeleteUser = null"
                    class="px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded hover:bg-gray-300"
                  >
                    No
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
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
          <button @click="createKey" class="btn-primary" :disabled="!newKeyName.trim()">
            Create Key
          </button>
        </div>
      </div>

      <div v-if="adminStore.loading" class="text-center py-8 text-gray-500">
        Loading API keys...
      </div>

      <div v-else class="bg-white rounded-lg shadow overflow-hidden">
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
                <code class="text-sm bg-gray-100 px-2 py-1 rounded">{{ key.key_prefix }}...</code>
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
                  :class="key.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                >
                  {{ key.is_active ? "Active" : "Revoked" }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <button
                  v-if="key.is_active"
                  @click="revokeKey(key.id)"
                  class="text-red-600 hover:text-red-800"
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
              @click="copyToClipboard(adminStore.newlyCreatedKey!.key)"
              class="px-3 py-1 bg-moxon-600 text-white text-sm rounded hover:bg-moxon-700"
            >
              Copy
            </button>
          </div>
        </div>

        <p class="text-sm text-gray-600 mb-4">
          Use this key in the <code class="bg-gray-100 px-1 rounded">X-API-Key</code> header for API
          requests.
        </p>

        <div class="flex justify-end">
          <button
            @click="
              showNewKeyModal = false;
              adminStore.clearNewKey();
            "
            class="btn-primary"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
