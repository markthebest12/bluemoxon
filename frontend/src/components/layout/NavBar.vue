<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
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
            <RouterLink
              to="/profile"
              class="text-sm text-moxon-200 hover:text-white transition-colors"
            >
              {{ authStore.user?.email }}
            </RouterLink>
            <button
              @click="authStore.logout()"
              class="text-sm hover:text-moxon-200 transition-colors"
            >
              Sign Out
            </button>
          </template>
          <template v-else>
            <RouterLink
              to="/login"
              class="text-sm hover:text-moxon-200 transition-colors"
            >
              Sign In
            </RouterLink>
          </template>
        </div>
      </div>
    </div>
  </nav>
</template>
