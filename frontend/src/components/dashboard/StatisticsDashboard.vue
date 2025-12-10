<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { api } from "@/services/api";
import type { TooltipItem } from "chart.js";
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

// Types
interface AcquisitionDay {
  date: string;
  label: string;
  count: number;
  value: number;
  cost: number;
  cumulative_count: number;
  cumulative_value: number;
  cumulative_cost: number;
}

interface BinderData {
  binder: string;
  full_name: string;
  count: number;
  value: number;
}

interface EraData {
  era: string;
  count: number;
  value: number;
}

interface PublisherData {
  publisher: string;
  tier: string;
  count: number;
  value: number;
  volumes: number;
}

interface AuthorData {
  author: string;
  count: number;
  value: number;
  volumes: number;
  sample_titles: string[];
  has_more: boolean;
}

// State
const loading = ref(true);
const acquisitionData = ref<AcquisitionDay[]>([]);
const binderData = ref<BinderData[]>([]);
const eraData = ref<EraData[]>([]);
const publisherData = ref<PublisherData[]>([]);
const authorData = ref<AuthorData[]>([]);

// Get today's date in browser timezone (YYYY-MM-DD format)
function getTodayLocal(): string {
  const now = new Date();
  return now.toLocaleDateString("en-CA"); // en-CA gives YYYY-MM-DD format
}

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
const lineChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      callbacks: {
        label: (context: TooltipItem<"line">) => {
          const dataIndex = context.dataIndex;
          const day = acquisitionData.value[dataIndex];
          if (!day) return "";
          return [
            `Total: $${day.cumulative_value.toLocaleString()}`,
            `Added today: ${day.count} items ($${day.value.toLocaleString()})`,
          ];
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
};

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
const acquisitionChartData = computed(() => {
  // Data already has cumulative values from backend
  return {
    labels: acquisitionData.value.map((d) => d.label),
    datasets: [
      {
        label: "Cumulative Value",
        data: acquisitionData.value.map((d) => d.cumulative_value),
        borderColor: chartColors.primary,
        backgroundColor: chartColors.primaryLight,
        fill: true,
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 5,
      },
    ],
  };
});

const binderChartData = computed(() => ({
  labels: binderData.value.map((d) => d.binder),
  datasets: [
    {
      data: binderData.value.map((d) => d.count),
      backgroundColor: [
        chartColors.burgundy, // Zaehnsdorf
        chartColors.gold, // Rivière
        chartColors.primary, // Sangorski
        chartColors.hunter700, // Bayntun
        chartColors.goldMuted, // Others
      ],
      borderWidth: 0,
    },
  ],
}));

const eraChartData = computed(() => ({
  labels: eraData.value.map((d) => d.era.split(" ")[0]), // Just "Victorian", "Romantic", etc.
  datasets: [
    {
      data: eraData.value.map((d) => d.count),
      backgroundColor: chartColors.primary,
      borderRadius: 4,
    },
  ],
}));

const publisherChartData = computed(() => {
  const tier1 = publisherData.value.filter((p) => p.tier === "TIER_1");
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
  return publisherData.value.some((p) => p.tier === "TIER_1");
});

const authorChartData = computed(() => ({
  labels: authorData.value.slice(0, 8).map((d) => d.author),
  datasets: [
    {
      data: authorData.value.slice(0, 8).map((d) => d.count),
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
          const author = authorData.value[authorIndex];

          if (author && author.sample_titles && author.sample_titles.length > 0) {
            const lines = [`${value} ${value === 1 ? "book" : "books"}:`];
            author.sample_titles.forEach((title: string) => {
              // Truncate long titles
              const truncated = title.length > 35 ? title.substring(0, 32) + "..." : title;
              lines.push(`  • ${truncated}`);
            });
            if (author.has_more) {
              lines.push(`  ...and ${value - author.sample_titles.length} more`);
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

// Fetch all data
onMounted(async () => {
  try {
    // Get today's date in browser timezone for the daily chart
    const today = getTodayLocal();

    const [acqRes, binderRes, eraRes, pubRes, authorRes] = await Promise.all([
      api.get(`/stats/acquisitions-daily?reference_date=${today}&days=30`),
      api.get("/stats/bindings"),
      api.get("/stats/by-era"),
      api.get("/stats/by-publisher"),
      api.get("/stats/by-author"),
    ]);

    acquisitionData.value = acqRes.data;
    binderData.value = binderRes.data;
    eraData.value = eraRes.data;
    publisherData.value = pubRes.data;
    authorData.value = authorRes.data;
  } catch (e) {
    console.error("Failed to load statistics", e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="mt-8">
    <div class="section-header">
      <h2>Collection Analytics</h2>
    </div>

    <div v-if="loading" class="text-center py-8">
      <p class="text-victorian-ink-muted">Loading charts...</p>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
      <!-- Premium Bindings Distribution -->
      <div class="card-static !p-4">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Premium Bindings
        </h3>
        <div class="h-48 md:h-56">
          <Doughnut
            v-if="binderData.length > 0"
            :data="binderChartData"
            :options="doughnutOptions"
          />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No binding data available
          </p>
        </div>
      </div>

      <!-- Era Distribution -->
      <div class="card-static !p-4">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Books by Era
        </h3>
        <div class="h-48 md:h-56">
          <Bar v-if="eraData.length > 0" :data="eraChartData" :options="barChartOptions" />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No era data available
          </p>
        </div>
      </div>

      <!-- Top Authors -->
      <div class="card-static !p-4">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Top Authors
        </h3>
        <div class="h-48 md:h-56">
          <Bar v-if="authorData.length > 0" :data="authorChartData" :options="authorChartOptions" />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No author data available
          </p>
        </div>
      </div>

      <!-- Top Tier 1 Publishers -->
      <div class="card-static !p-4">
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
      <div class="card-static !p-4 col-span-1 lg:col-span-2">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Est. Value Growth (Last 30 Days)
        </h3>
        <div class="h-48 md:h-64">
          <Line
            v-if="acquisitionData.length > 0"
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
