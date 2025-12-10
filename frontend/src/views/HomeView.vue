<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/services/api";
import StatisticsDashboard from "@/components/dashboard/StatisticsDashboard.vue";

interface WeekDelta {
  count: number;
  volumes: number;
  value_mid: number;
  authenticated_bindings: number;
}

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
  in_transit: number;
  week_delta: WeekDelta;
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

function formatDelta(value: number, isCurrency = false): string {
  if (value === 0) return "—";
  const prefix = value > 0 ? "+" : "";
  if (isCurrency) {
    return prefix + formatCurrency(value);
  }
  return prefix + value.toString();
}

function getTrendClass(value: number): string {
  if (value > 0) return "text-victorian-hunter-600";
  if (value < 0) return "text-victorian-burgundy";
  return "text-victorian-ink-muted";
}

function getTrendArrow(value: number): string {
  if (value > 0) return "↑";
  if (value < 0) return "↓";
  return "→";
}
</script>

<template>
  <div>
    <div class="section-header">
      <h1>Collection Dashboard</h1>
    </div>

    <div v-if="loading" class="text-center py-12">
      <p class="text-victorian-ink-muted">Loading statistics...</p>
    </div>

    <div v-else-if="stats" class="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6">
      <!-- Total Collections -->
      <div class="card-static !p-3 md:!p-6 relative overflow-hidden">
        <div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-victorian-hunter-800/5 to-transparent"></div>
        <h3 class="text-xs md:text-sm font-medium text-victorian-ink-muted uppercase tracking-wider">On Hand</h3>
        <div class="flex items-baseline gap-2 mt-1 md:mt-2">
          <p class="text-2xl md:text-3xl font-display text-victorian-hunter-800">
            {{ stats.primary.count }}
          </p>
          <span
            v-if="stats.week_delta"
            :class="['text-xs md:text-sm font-medium', getTrendClass(stats.week_delta.count)]"
          >
            {{ getTrendArrow(stats.week_delta.count) }}
            {{ formatDelta(stats.week_delta.count) }}
          </span>
        </div>
        <p class="text-xs md:text-sm text-victorian-ink-muted mt-1 hidden md:block">
          Primary collection
          <span v-if="stats.in_transit" class="text-victorian-ink-muted/60"
            >({{ stats.in_transit }} in transit)</span
          >
        </p>
      </div>

      <!-- Total Volumes -->
      <div class="card-static !p-3 md:!p-6 relative overflow-hidden">
        <div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-victorian-hunter-800/5 to-transparent"></div>
        <h3 class="text-xs md:text-sm font-medium text-victorian-ink-muted uppercase tracking-wider">Volumes</h3>
        <div class="flex items-baseline gap-2 mt-1 md:mt-2">
          <p class="text-2xl md:text-3xl font-display text-victorian-hunter-800">
            {{ stats.primary.volumes }}
          </p>
          <span
            v-if="stats.week_delta"
            :class="['text-xs md:text-sm font-medium', getTrendClass(stats.week_delta.volumes)]"
          >
            {{ getTrendArrow(stats.week_delta.volumes) }}
            {{ formatDelta(stats.week_delta.volumes) }}
          </span>
        </div>
        <p class="text-xs md:text-sm text-victorian-ink-muted mt-1 hidden md:block">
          Including multi-volume sets
        </p>
      </div>

      <!-- Collection Value -->
      <div class="card-static !p-3 md:!p-6 relative overflow-hidden">
        <div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-victorian-gold/10 to-transparent"></div>
        <h3 class="text-xs md:text-sm font-medium text-victorian-ink-muted uppercase tracking-wider">Est. Value</h3>
        <div class="flex items-baseline gap-2 mt-1 md:mt-2">
          <p class="text-xl md:text-3xl font-display text-victorian-gold-dark">
            {{ formatCurrency(stats.primary.value_mid) }}
          </p>
          <span
            v-if="stats.week_delta"
            :class="['text-xs md:text-sm font-medium', getTrendClass(stats.week_delta.value_mid)]"
          >
            {{ getTrendArrow(stats.week_delta.value_mid) }}
          </span>
        </div>
        <p class="text-xs md:text-sm text-victorian-ink-muted mt-1 hidden md:block">
          <span v-if="stats.week_delta && stats.week_delta.value_mid !== 0">
            <span :class="getTrendClass(stats.week_delta.value_mid)">
              {{ formatDelta(stats.week_delta.value_mid, true) }}
            </span>
            this week
          </span>
          <span v-else>
            {{ formatCurrency(stats.primary.value_low) }} -
            {{ formatCurrency(stats.primary.value_high) }}
          </span>
        </p>
      </div>

      <!-- Authenticated Bindings -->
      <div class="card-static !p-3 md:!p-6 relative overflow-hidden">
        <div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-victorian-burgundy/10 to-transparent"></div>
        <h3 class="text-xs md:text-sm font-medium text-victorian-ink-muted uppercase tracking-wider">Premium</h3>
        <div class="flex items-baseline gap-2 mt-1 md:mt-2">
          <p class="text-2xl md:text-3xl font-display text-victorian-burgundy">
            {{ stats.authenticated_bindings }}
          </p>
          <span
            v-if="stats.week_delta"
            :class="[
              'text-xs md:text-sm font-medium',
              getTrendClass(stats.week_delta.authenticated_bindings),
            ]"
          >
            {{ getTrendArrow(stats.week_delta.authenticated_bindings) }}
            {{ formatDelta(stats.week_delta.authenticated_bindings) }}
          </span>
        </div>
        <p class="text-xs md:text-sm text-victorian-ink-muted mt-1 hidden md:block">Authenticated bindings</p>
      </div>
    </div>

    <!-- Quick Links -->
    <div class="mt-8 md:mt-12 grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
      <RouterLink to="/books" class="card group">
        <h3 class="text-lg font-display text-victorian-ink-black group-hover:text-victorian-hunter-700">Browse Collection</h3>
        <p class="text-victorian-ink-muted mt-2">Search and filter your complete book inventory</p>
      </RouterLink>

      <RouterLink
        to="/books?inventory_type=PRIMARY&binding_authenticated=true"
        class="card group"
      >
        <h3 class="text-lg font-display text-victorian-ink-black group-hover:text-victorian-hunter-700">Premium Bindings</h3>
        <p class="text-victorian-ink-muted mt-2">View authenticated Zaehnsdorf, Riviere, and more</p>
      </RouterLink>
    </div>

    <!-- Statistics Dashboard -->
    <StatisticsDashboard />
  </div>
</template>
