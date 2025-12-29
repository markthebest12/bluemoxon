<script setup lang="ts">
import { RouterView } from "vue-router";
import NavBar from "@/components/layout/NavBar.vue";
</script>

<template>
  <div class="min-h-screen bg-[var(--color-surface-base)]">
    <NavBar />
    <main class="container mx-auto px-4 py-8">
      <RouterView />
    </main>
  </div>
</template>
