<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/services/api";

interface Stats {
  primary: {
    count: number;
    volumes: number;
    value_low: number;
    value_mid: number;
    value_high: number;
  };
  extended: { count: number };
  flagged: { count: number };
  total_items: number;
  authenticated_bindings: number;
}

const stats = ref<Stats | null>(null);
const loading = ref(true);

onMounted(async () => {
  try {
    const response = await api.get("/stats/overview");
    stats.value = response.data;
  } catch (e) {
    console.error("Failed to load stats", e);
  } finally {
    loading.value = false;
  }
});

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
  }).format(value);
}
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold text-gray-800 mb-8">Collection Dashboard</h1>

    <div v-if="loading" class="text-center py-12">
      <p class="text-gray-500">Loading statistics...</p>
    </div>

    <div v-else-if="stats" class="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6">
      <!-- Total Items -->
      <div class="card !p-3 md:!p-6">
        <h3 class="text-xs md:text-sm font-medium text-gray-500 uppercase">Total Items</h3>
        <p class="text-2xl md:text-3xl font-bold text-moxon-600 mt-1 md:mt-2">
          {{ stats.primary.count }}
        </p>
        <p class="text-xs md:text-sm text-gray-500 mt-1 hidden md:block">Primary collection</p>
      </div>

      <!-- Total Volumes -->
      <div class="card !p-3 md:!p-6">
        <h3 class="text-xs md:text-sm font-medium text-gray-500 uppercase">Volumes</h3>
        <p class="text-2xl md:text-3xl font-bold text-moxon-600 mt-1 md:mt-2">
          {{ stats.primary.volumes }}
        </p>
        <p class="text-xs md:text-sm text-gray-500 mt-1 hidden md:block">Including multi-volume sets</p>
      </div>

      <!-- Collection Value -->
      <div class="card !p-3 md:!p-6">
        <h3 class="text-xs md:text-sm font-medium text-gray-500 uppercase">Value</h3>
        <p class="text-xl md:text-3xl font-bold text-victorian-gold mt-1 md:mt-2">
          {{ formatCurrency(stats.primary.value_mid) }}
        </p>
        <p class="text-xs md:text-sm text-gray-500 mt-1 hidden md:block">
          {{ formatCurrency(stats.primary.value_low) }} -
          {{ formatCurrency(stats.primary.value_high) }}
        </p>
      </div>

      <!-- Authenticated Bindings -->
      <div class="card !p-3 md:!p-6">
        <h3 class="text-xs md:text-sm font-medium text-gray-500 uppercase">Premium</h3>
        <p class="text-2xl md:text-3xl font-bold text-victorian-burgundy mt-1 md:mt-2">
          {{ stats.authenticated_bindings }}
        </p>
        <p class="text-xs md:text-sm text-gray-500 mt-1 hidden md:block">Authenticated bindings</p>
      </div>
    </div>

    <!-- Quick Links -->
    <div class="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
      <RouterLink to="/books" class="card hover:shadow-lg transition-shadow">
        <h3 class="text-lg font-semibold text-gray-800">Browse Collection</h3>
        <p class="text-gray-500 mt-2">View and filter your complete book inventory</p>
      </RouterLink>

      <RouterLink to="/search" class="card hover:shadow-lg transition-shadow">
        <h3 class="text-lg font-semibold text-gray-800">Search</h3>
        <p class="text-gray-500 mt-2">Search across books and analysis documents</p>
      </RouterLink>

      <RouterLink
        to="/books?inventory_type=PRIMARY&binding_authenticated=true"
        class="card hover:shadow-lg transition-shadow"
      >
        <h3 class="text-lg font-semibold text-gray-800">Premium Bindings</h3>
        <p class="text-gray-500 mt-2">View authenticated Zaehnsdorf, Riviere, and more</p>
      </RouterLink>
    </div>
  </div>
</template>
