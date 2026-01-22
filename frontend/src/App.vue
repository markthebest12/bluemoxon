<script setup lang="ts">
import { onMounted } from "vue";
import { RouterView } from "vue-router";
import NavBar from "@/components/layout/NavBar.vue";
import ToastContainer from "@/components/ToastContainer.vue";
import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();

onMounted(() => {
  // Initialize auth with optimistic role caching
  void authStore.initializeAuth();
});
</script>

<template>
  <!-- Loading overlay during cold start auth initialization -->
  <div
    v-if="authStore.authInitializing"
    data-testid="auth-loading"
    class="min-h-screen bg-[var(--color-surface-base)] flex flex-col items-center justify-center"
  >
    <img src="/bluemoxon-classic-logo.png" alt="BlueMoxon" class="h-20 w-auto mb-6 animate-pulse" />
    <div class="text-[var(--color-text-secondary)] text-sm">Loading BlueMoxon...</div>
  </div>

  <!-- Main app content -->
  <div v-else class="min-h-screen bg-[var(--color-surface-base)]">
    <NavBar />
    <main class="container mx-auto px-4 py-8">
      <RouterView />
    </main>
    <ToastContainer />
  </div>
</template>
