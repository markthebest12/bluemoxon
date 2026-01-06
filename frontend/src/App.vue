<script setup lang="ts">
import { RouterView } from "vue-router";
import NavBar from "@/components/layout/NavBar.vue";
import ToastContainer from "@/components/ToastContainer.vue";
</script>

<template>
  <div class="min-h-screen bg-[var(--color-surface-base)]">
    <NavBar />
    <main class="container mx-auto px-4 py-8">
      <RouterView />
    </main>
    <ToastContainer />
  </div>
</template>
