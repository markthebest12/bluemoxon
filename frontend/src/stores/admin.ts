import { ref } from "vue";
import { defineStore } from "pinia";
import api from "@/services/api";

interface User {
  id: number;
  cognito_sub: string;
  email: string;
  role: string;
}

interface APIKey {
  id: number;
  name: string;
  key_prefix: string;
  created_by_id: number;
  created_by_email: string | null;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string | null;
}

interface NewAPIKey extends APIKey {
  key: string; // Only present when newly created
  message: string;
}

export const useAdminStore = defineStore("admin", () => {
  const users = ref<User[]>([]);
  const apiKeys = ref<APIKey[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Newly created key (shown once)
  const newlyCreatedKey = ref<NewAPIKey | null>(null);

  async function fetchUsers() {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.get("/users");
      users.value = response.data;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch users";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateUserRole(userId: number, role: string) {
    error.value = null;
    try {
      await api.put(`/users/${userId}/role`, null, { params: { role } });
      // Update local state
      const user = users.value.find((u) => u.id === userId);
      if (user) {
        user.role = role;
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to update role";
      throw e;
    }
  }

  async function deleteUser(userId: number) {
    error.value = null;
    try {
      await api.delete(`/users/${userId}`);
      // Remove from local state
      users.value = users.value.filter((u) => u.id !== userId);
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to delete user";
      throw e;
    }
  }

  async function fetchAPIKeys() {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.get("/users/api-keys");
      apiKeys.value = response.data;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to fetch API keys";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createAPIKey(name: string) {
    error.value = null;
    try {
      const response = await api.post("/users/api-keys", { name });
      newlyCreatedKey.value = response.data;
      // Add to list (without the full key)
      apiKeys.value.push({
        id: response.data.id,
        name: response.data.name,
        key_prefix: response.data.key_prefix,
        created_by_id: 0, // Will be updated on next fetch
        created_by_email: null,
        is_active: true,
        last_used_at: null,
        created_at: new Date().toISOString(),
      });
      return response.data;
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to create API key";
      throw e;
    }
  }

  async function revokeAPIKey(keyId: number) {
    error.value = null;
    try {
      await api.delete(`/users/api-keys/${keyId}`);
      // Update local state
      const key = apiKeys.value.find((k) => k.id === keyId);
      if (key) {
        key.is_active = false;
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || "Failed to revoke API key";
      throw e;
    }
  }

  function clearNewKey() {
    newlyCreatedKey.value = null;
  }

  return {
    users,
    apiKeys,
    loading,
    error,
    newlyCreatedKey,
    fetchUsers,
    updateUserRole,
    deleteUser,
    fetchAPIKeys,
    createAPIKey,
    revokeAPIKey,
    clearNewKey,
  };
});
