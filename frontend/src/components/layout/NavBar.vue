<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();
const showDropdown = ref(false);

async function handleSignOut() {
  showDropdown.value = false;
  await authStore.logout();
  router.push("/login");
}

function closeDropdown() {
  showDropdown.value = false;
}
</script>

<template>
  <nav class="bg-moxon-800 text-white shadow-lg">
    <div class="container mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <RouterLink to="/" class="flex items-center space-x-2">
          <span class="text-2xl font-bold">BlueMoxon</span>
        </RouterLink>

        <!-- Navigation Links -->
        <div class="hidden md:flex items-center space-x-6">
          <RouterLink
            to="/"
            class="hover:text-moxon-200 transition-colors"
            active-class="text-moxon-200"
          >
            Dashboard
          </RouterLink>
          <RouterLink
            to="/books"
            class="hover:text-moxon-200 transition-colors"
            active-class="text-moxon-200"
          >
            Collection
          </RouterLink>
          <RouterLink
            to="/search"
            class="hover:text-moxon-200 transition-colors"
            active-class="text-moxon-200"
          >
            Search
          </RouterLink>
        </div>

        <!-- User Menu -->
        <div class="flex items-center space-x-4">
          <template v-if="authStore.isAuthenticated">
            <div class="relative">
              <button
                @click="showDropdown = !showDropdown"
                class="text-sm text-moxon-200 hover:text-white transition-colors flex items-center gap-1"
              >
                {{ authStore.user?.email }}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
              <!-- Dropdown Menu -->
              <div
                v-if="showDropdown"
                class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50"
                @click="closeDropdown"
              >
                <RouterLink
                  v-if="authStore.isAdmin"
                  to="/admin"
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Admin Settings
                </RouterLink>
                <button
                  @click="handleSignOut"
                  class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Sign Out
                </button>
              </div>
            </div>
            <!-- Click outside to close -->
            <div v-if="showDropdown" class="fixed inset-0 z-40" @click="closeDropdown"></div>
          </template>
          <template v-else>
            <RouterLink to="/login" class="text-sm hover:text-moxon-200 transition-colors">
              Sign In
            </RouterLink>
          </template>
        </div>
      </div>
    </div>
  </nav>
</template>
