<script setup lang="ts">
import { onMounted } from "vue";
import { RouterView } from "vue-router";
import NavBar from "@/components/layout/NavBar.vue";
import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();

onMounted(() => {
  authStore.checkAuth();
});
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <NavBar />
    <main class="container mx-auto px-4 py-8">
      <RouterView />
    </main>
  </div>
</template>
