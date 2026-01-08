<script setup lang="ts">
import { computed } from "vue";
import type { TooltipItem } from "chart.js";
import type { DashboardStats } from "@/types/dashboard";
import { formatAcquisitionTooltip } from "./chartHelpers";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line, Doughnut, Bar } from "vue-chartjs";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Props - receive data from parent
const props = defineProps<{
  data: DashboardStats;
}>();

// Colors - Victorian Design System
const chartColors = {
  // Hunter greens
  primary: "rgb(26, 58, 47)", // victorian-hunter-800 #1a3a2f
  primaryLight: "rgba(26, 58, 47, 0.1)",
  hunter700: "rgb(37, 74, 61)", // victorian-hunter-700 #254a3d
  // Gold tones
  gold: "rgb(201, 162, 39)", // victorian-gold #c9a227
  goldMuted: "rgb(184, 149, 110)", // victorian-gold-muted #b8956e
  // Burgundy
  burgundy: "rgb(114, 47, 55)", // victorian-burgundy #722f37
  burgundyLight: "rgb(139, 58, 66)", // victorian-burgundy-light #8b3a42
  // Paper
  paperAntique: "rgb(232, 225, 213)", // victorian-paper-antique #e8e1d5
  // Ink
  inkMuted: "rgb(92, 92, 88)", // victorian-ink-muted #5c5c58
};

// Chart options - mobile friendly
// Note: lineChartOptions needs to be a computed to access props.data
const lineChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      callbacks: {
        label: (context: TooltipItem<"line">) => {
          const day = props.data.acquisitions_daily[context.dataIndex];
          return formatAcquisitionTooltip(day);
        },
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: {
        maxRotation: 45,
        minRotation: 45,
        font: { size: 10 },
        autoSkip: true,
        maxTicksLimit: 8,
      },
    },
    y: {
      beginAtZero: true,
      grid: { color: "rgba(0,0,0,0.05)" },
      ticks: {
        font: { size: 10 },
        callback: (value: string | number) => `$${(Number(value) / 1000).toFixed(0)}k`,
      },
    },
  },
}));

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: "bottom" as const,
      labels: {
        boxWidth: 12,
        padding: 8,
        font: { size: 11 },
      },
    },
    tooltip: {
      callbacks: {
        label: (context: TooltipItem<"doughnut">) => {
          const value = context.raw as number;
          const total = context.dataset.data.reduce((a: number, b) => a + (b as number), 0);
          const pct = ((value / total) * 100).toFixed(1);
          return `${value} ${value === 1 ? "book" : "books"} (${pct}%)`;
        },
      },
    },
  },
};

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: "y" as const,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (context: TooltipItem<"bar">) => {
          const value = context.raw as number;
          return `${value} ${value === 1 ? "book" : "books"}`;
        },
      },
    },
  },
  scales: {
    x: {
      beginAtZero: true,
      grid: { color: "rgba(0,0,0,0.05)" },
      ticks: {
        font: { size: 10 },
        stepSize: 1,
        callback: (value: string | number) => (Number.isInteger(Number(value)) ? value : ""),
      },
    },
    y: {
      grid: { display: false },
      ticks: { font: { size: 10 } },
    },
  },
};

// Computed chart data - cumulative value growth (daily, last 30 days)
const acquisitionChartData = computed(() => ({
  labels: props.data.acquisitions_daily.map((d) => d.label),
  datasets: [
    {
      label: "Cumulative Value",
      data: props.data.acquisitions_daily.map((d) => d.cumulative_value),
      borderColor: chartColors.primary,
      backgroundColor: chartColors.primaryLight,
      fill: true,
      tension: 0.3,
      pointRadius: 2,
      pointHoverRadius: 5,
    },
  ],
}));

const binderChartData = computed(() => ({
  labels: props.data.bindings.map((d) => d.binder),
  datasets: [
    {
      data: props.data.bindings.map((d) => d.count),
      backgroundColor: [
        chartColors.burgundy,
        chartColors.gold,
        chartColors.primary,
        chartColors.hunter700,
        chartColors.goldMuted,
      ],
      borderWidth: 0,
    },
  ],
}));

const eraChartData = computed(() => ({
  labels: props.data.by_era.map((d) => d.era.split(" ")[0]),
  datasets: [
    {
      data: props.data.by_era.map((d) => d.count),
      backgroundColor: chartColors.primary,
      borderRadius: 4,
    },
  ],
}));

const publisherChartData = computed(() => {
  const tier1 = props.data.by_publisher.filter((p) => p.tier === "TIER_1");
  return {
    labels: tier1.slice(0, 5).map((d) => d.publisher),
    datasets: [
      {
        data: tier1.slice(0, 5).map((d) => d.count),
        backgroundColor: chartColors.gold,
        borderRadius: 4,
      },
    ],
  };
});

// Check if there are any tier 1 publishers
const hasTier1Publishers = computed(() => {
  return props.data.by_publisher.some((p) => p.tier === "TIER_1");
});

// Filter out "Various" from author data (not a real author)
const variousEntry = computed(() => props.data.by_author.find((d) => d.author === "Various"));
const filteredAuthorData = computed(() =>
  props.data.by_author.filter((d) => d.author !== "Various")
);

const authorChartData = computed(() => ({
  labels: filteredAuthorData.value.slice(0, 8).map((d) => d.author),
  datasets: [
    {
      data: filteredAuthorData.value.slice(0, 8).map((d) => d.count),
      backgroundColor: chartColors.burgundy,
      borderRadius: 4,
    },
  ],
}));

// Custom options for author chart with enhanced tooltips showing book titles
const authorChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: "y" as const,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (context: TooltipItem<"bar">) => {
          const value = context.raw as number;
          const authorIndex = context.dataIndex;
          const author = filteredAuthorData.value[authorIndex];

          if (author && author.sample_titles && author.sample_titles.length > 0) {
            const lines = [
              `${value} ${value === 1 ? "book" : "books"} across ${author.titles} ${author.titles === 1 ? "title" : "titles"}:`,
            ];
            author.sample_titles.forEach((title: string) => {
              // Truncate long titles
              const truncated = title.length > 35 ? title.substring(0, 32) + "..." : title;
              lines.push(`  • ${truncated}`);
            });
            if (author.has_more) {
              const moreCount = author.titles - author.sample_titles.length;
              lines.push(`  ...and ${moreCount} more ${moreCount === 1 ? "title" : "titles"}`);
            }
            return lines;
          }
          return `${value} ${value === 1 ? "book" : "books"}`;
        },
      },
    },
  },
  scales: {
    x: {
      beginAtZero: true,
      grid: { color: "rgba(0,0,0,0.05)" },
      ticks: {
        font: { size: 10 },
        stepSize: 1,
        callback: (value: string | number) => (Number.isInteger(Number(value)) ? value : ""),
      },
    },
    y: {
      grid: { display: false },
      ticks: { font: { size: 10 } },
    },
  },
}));
</script>

<template>
  <div class="mt-8">
    <div class="section-header">
      <h2>Collection Analytics</h2>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
      <!-- Premium Bindings Distribution -->
      <div class="card-static p-4!">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Premium Bindings
        </h3>
        <div class="h-48 md:h-56">
          <Doughnut
            v-if="props.data.bindings.length > 0"
            :data="binderChartData"
            :options="doughnutOptions"
          />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No binding data available
          </p>
        </div>
      </div>

      <!-- Era Distribution -->
      <div class="card-static p-4!">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Books by Era
        </h3>
        <div class="h-48 md:h-56">
          <Bar
            v-if="props.data.by_era.length > 0"
            :data="eraChartData"
            :options="barChartOptions"
          />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No era data available
          </p>
        </div>
      </div>

      <!-- Top Authors -->
      <div class="card-static p-4!">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Top Authors
        </h3>
        <div class="h-48 md:h-56">
          <Bar
            v-if="filteredAuthorData.length > 0"
            :data="authorChartData"
            :options="authorChartOptions"
          />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No author data available
          </p>
        </div>
        <p v-if="variousEntry" class="text-xs text-victorian-ink-muted mt-2">
          * Excludes {{ variousEntry.count }} books by various/multiple authors
        </p>
      </div>

      <!-- Top Tier 1 Publishers -->
      <div class="card-static p-4!">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Top Tier 1 Publishers
        </h3>
        <div class="h-48 md:h-56">
          <Bar v-if="hasTier1Publishers" :data="publisherChartData" :options="barChartOptions" />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No Tier 1 publisher data available
          </p>
        </div>
      </div>

      <!-- Cumulative Value Growth - full width at bottom -->
      <div class="card-static p-4! col-span-1 lg:col-span-2">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Est. Value Growth (Last 30 Days)
        </h3>
        <div class="h-48 md:h-64">
          <Line
            v-if="props.data.acquisitions_daily.length > 0"
            :data="acquisitionChartData"
            :options="lineChartOptions"
          />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No acquisition data available
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
