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
  <!-- Error screen when auth initialization fails -->
  <div
    v-if="authStore.authError"
    data-testid="auth-error"
    class="min-h-screen bg-[#0f2318] flex flex-col items-center justify-center"
  >
    <img src="/bluemoxon-classic-logo.png" alt="BlueMoxon" class="h-20 w-auto mb-6" />
    <div class="text-white text-lg mb-4">Unable to connect</div>
    <div class="text-slate-400 text-sm mb-6">Please check your connection and try again.</div>
    <button
      data-testid="auth-retry-button"
      class="px-4 py-2 bg-[var(--color-brand)] text-white rounded hover:opacity-90 transition-opacity"
      @click="authStore.initializeAuth()"
    >
      Retry
    </button>
  </div>

  <!-- Loading overlay during cold start auth initialization -->
  <div
    v-else-if="authStore.authInitializing"
    data-testid="auth-loading"
    class="min-h-screen bg-[#0f2318] flex flex-col items-center justify-center"
  >
    <img src="/bluemoxon-classic-logo.png" alt="BlueMoxon" class="h-20 w-auto mb-6 animate-pulse" />
    <div class="text-slate-300 text-sm">Loading BlueMoxon...</div>
    <div
      v-if="authStore.authRetrying"
      data-testid="auth-retrying"
      class="text-slate-400 text-xs mt-2"
    >
      Taking longer than usual...
    </div>
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
