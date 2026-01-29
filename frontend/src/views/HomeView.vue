<script setup lang="ts">
import { defineAsyncComponent, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useDashboardStore } from "@/stores/dashboard";
import CollectionSpotlight from "@/components/dashboard/CollectionSpotlight.vue";
import SocialCirclesCard from "@/components/dashboard/SocialCirclesCard.vue";
import BaseTooltip from "@/components/BaseTooltip.vue";
import { DASHBOARD_STAT_CARDS } from "@/constants";

// Lazy load StatisticsDashboard to defer Chart.js bundle (~46KB) until needed
const StatisticsDashboard = defineAsyncComponent({
  loader: () => import("@/components/dashboard/StatisticsDashboard.vue"),
  errorComponent: {
    template: `<div class="card-static p-6 text-center">
      <p class="text-victorian-burgundy">Failed to load statistics. Please refresh the page.</p>
    </div>`,
  },
  loadingComponent: {
    template: `<div class="card-static p-6 text-center">
      <p class="text-victorian-ink-muted">Loading statistics...</p>
    </div>`,
  },
});

const router = useRouter();

const dashboardStore = useDashboardStore();

onMounted(() => {
  void dashboardStore.loadDashboard();
});

onUnmounted(() => {
  dashboardStore.cleanup();
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

function navigateToStat(filterParam: string, event?: MouseEvent): void {
  // Parse filterParam and build URL with proper encoding
  const params = new URLSearchParams(filterParam);
  params.set("inventory_type", "PRIMARY");
  const url = `/books?${params.toString()}`;
  if (event?.metaKey || event?.ctrlKey) {
    window.open(url, "_blank");
  } else {
    void router.push(url);
  }
}
</script>

<template>
  <div>
    <div class="section-header">
      <h1>Collection Dashboard</h1>
    </div>
    <div v-if="dashboardStore.isStale" class="text-xs text-victorian-ink-muted mb-2">
      Updating...
    </div>

    <div v-if="dashboardStore.loading" class="text-center py-12">
      <p class="text-victorian-ink-muted">Loading statistics...</p>
    </div>

    <div
      v-else-if="dashboardStore.error && !dashboardStore.data"
      class="card-static p-6 text-center"
    >
      <p class="text-victorian-burgundy">{{ dashboardStore.error }}</p>
      <button class="btn btn-primary mt-4" @click="dashboardStore.loadDashboard()">Retry</button>
    </div>

    <div v-else-if="dashboardStore.data" class="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6">
      <!-- Total Collections -->
      <div
        class="card-static p-3! md:p-6! relative overflow-hidden cursor-pointer hover:ring-2 hover:ring-victorian-hunter-600/30 transition-all"
        @click="navigateToStat(DASHBOARD_STAT_CARDS.ON_HAND.filterParam, $event)"
      >
        <div
          class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-victorian-hunter-800/5 to-transparent"
        ></div>
        <BaseTooltip :content="DASHBOARD_STAT_CARDS.ON_HAND.description" position="bottom">
          <h3
            class="text-xs md:text-sm font-medium text-victorian-ink-muted uppercase tracking-wider cursor-help"
          >
            On Hand
          </h3>
        </BaseTooltip>
        <div class="flex items-baseline gap-2 mt-1 md:mt-2">
          <p class="text-2xl md:text-3xl font-display text-victorian-hunter-800">
            {{ dashboardStore.data.overview.primary.count }}
          </p>
          <span
            v-if="dashboardStore.data.overview.week_delta"
            :class="[
              'text-xs md:text-sm font-medium',
              getTrendClass(dashboardStore.data.overview.week_delta.count),
            ]"
          >
            {{ getTrendArrow(dashboardStore.data.overview.week_delta.count) }}
            {{ formatDelta(dashboardStore.data.overview.week_delta.count) }}
          </span>
        </div>
        <p class="text-xs md:text-sm text-victorian-ink-muted mt-1 hidden md:block">
          Primary collection
          <span v-if="dashboardStore.data.overview.in_transit" class="text-victorian-ink-muted/60"
            >({{ dashboardStore.data.overview.in_transit }} in transit)</span
          >
        </p>
      </div>

      <!-- Total Volumes -->
      <div
        class="card-static p-3! md:p-6! relative overflow-hidden cursor-pointer hover:ring-2 hover:ring-victorian-hunter-600/30 transition-all"
        @click="navigateToStat(DASHBOARD_STAT_CARDS.VOLUMES.filterParam, $event)"
      >
        <div
          class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-victorian-hunter-800/5 to-transparent"
        ></div>
        <BaseTooltip :content="DASHBOARD_STAT_CARDS.VOLUMES.description" position="bottom">
          <h3
            class="text-xs md:text-sm font-medium text-victorian-ink-muted uppercase tracking-wider cursor-help"
          >
            Volumes
          </h3>
        </BaseTooltip>
        <div class="flex items-baseline gap-2 mt-1 md:mt-2">
          <p class="text-2xl md:text-3xl font-display text-victorian-hunter-800">
            {{ dashboardStore.data.overview.primary.volumes }}
          </p>
          <span
            v-if="dashboardStore.data.overview.week_delta"
            :class="[
              'text-xs md:text-sm font-medium',
              getTrendClass(dashboardStore.data.overview.week_delta.volumes),
            ]"
          >
            {{ getTrendArrow(dashboardStore.data.overview.week_delta.volumes) }}
            {{ formatDelta(dashboardStore.data.overview.week_delta.volumes) }}
          </span>
        </div>
        <p class="text-xs md:text-sm text-victorian-ink-muted mt-1 hidden md:block">
          Including multi-volume sets
        </p>
      </div>

      <!-- Collection Value -->
      <div
        class="card-static p-3! md:p-6! relative overflow-hidden cursor-pointer hover:ring-2 hover:ring-victorian-gold/30 transition-all"
        @click="navigateToStat(DASHBOARD_STAT_CARDS.EST_VALUE.filterParam, $event)"
      >
        <div
          class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-victorian-gold/10 to-transparent"
        ></div>
        <BaseTooltip :content="DASHBOARD_STAT_CARDS.EST_VALUE.description" position="bottom">
          <h3
            class="text-xs md:text-sm font-medium text-victorian-ink-muted uppercase tracking-wider cursor-help"
          >
            Est. Value
          </h3>
        </BaseTooltip>
        <div class="flex items-baseline gap-2 mt-1 md:mt-2">
          <p class="text-xl md:text-3xl font-display text-victorian-gold-dark">
            {{ formatCurrency(dashboardStore.data.overview.primary.value_mid) }}
          </p>
          <span
            v-if="dashboardStore.data.overview.week_delta"
            :class="[
              'text-xs md:text-sm font-medium',
              getTrendClass(dashboardStore.data.overview.week_delta.value_mid),
            ]"
          >
            {{ getTrendArrow(dashboardStore.data.overview.week_delta.value_mid) }}
          </span>
        </div>
        <p class="text-xs md:text-sm text-victorian-ink-muted mt-1 hidden md:block">
          <span
            v-if="
              dashboardStore.data.overview.week_delta &&
              dashboardStore.data.overview.week_delta.value_mid !== 0
            "
          >
            <span :class="getTrendClass(dashboardStore.data.overview.week_delta.value_mid)">
              {{ formatDelta(dashboardStore.data.overview.week_delta.value_mid, true) }}
            </span>
            this week
          </span>
          <span v-else>
            {{ formatCurrency(dashboardStore.data.overview.primary.value_low) }} -
            {{ formatCurrency(dashboardStore.data.overview.primary.value_high) }}
          </span>
        </p>
      </div>

      <!-- Authenticated Bindings -->
      <div
        class="card-static p-3! md:p-6! relative overflow-hidden cursor-pointer hover:ring-2 hover:ring-victorian-burgundy/30 transition-all"
        @click="navigateToStat(DASHBOARD_STAT_CARDS.PREMIUM.filterParam, $event)"
      >
        <div
          class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-victorian-burgundy/10 to-transparent"
        ></div>
        <BaseTooltip :content="DASHBOARD_STAT_CARDS.PREMIUM.description" position="bottom">
          <h3
            class="text-xs md:text-sm font-medium text-victorian-ink-muted uppercase tracking-wider cursor-help"
          >
            Premium
          </h3>
        </BaseTooltip>
        <div class="flex items-baseline gap-2 mt-1 md:mt-2">
          <p class="text-2xl md:text-3xl font-display text-victorian-burgundy">
            {{ dashboardStore.data.overview.authenticated_bindings }}
          </p>
          <span
            v-if="dashboardStore.data.overview.week_delta"
            :class="[
              'text-xs md:text-sm font-medium',
              getTrendClass(dashboardStore.data.overview.week_delta.authenticated_bindings),
            ]"
          >
            {{ getTrendArrow(dashboardStore.data.overview.week_delta.authenticated_bindings) }}
            {{ formatDelta(dashboardStore.data.overview.week_delta.authenticated_bindings) }}
          </span>
        </div>
        <p class="text-xs md:text-sm text-victorian-ink-muted mt-1 hidden md:block">
          Authenticated bindings
        </p>
      </div>
    </div>

    <!-- Collection Spotlight - showcases top value books -->
    <CollectionSpotlight />

    <!-- Social Circles Preview Card -->
    <SocialCirclesCard />

    <!-- Statistics Dashboard - pass data as prop -->
    <StatisticsDashboard v-if="dashboardStore.data" :data="dashboardStore.data" />
  </div>
</template>
