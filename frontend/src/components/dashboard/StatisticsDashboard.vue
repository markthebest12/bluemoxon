<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { api } from "@/services/api";
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
interface AcquisitionMonth {
  year: number;
  month: number;
  label: string;
  count: number;
  value: number;
  cost: number;
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

// State
const loading = ref(true);
const acquisitionData = ref<AcquisitionMonth[]>([]);
const binderData = ref<BinderData[]>([]);
const eraData = ref<EraData[]>([]);
const publisherData = ref<PublisherData[]>([]);

// Colors
const chartColors = {
  primary: "rgb(51, 65, 85)", // slate-700 (moxon color)
  primaryLight: "rgba(51, 65, 85, 0.1)",
  gold: "rgb(180, 140, 60)",
  burgundy: "rgb(128, 0, 32)",
  accent1: "rgb(59, 130, 246)", // blue
  accent2: "rgb(16, 185, 129)", // green
  accent3: "rgb(245, 158, 11)", // amber
  accent4: "rgb(139, 92, 246)", // purple
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
        label: (context: any) => {
          const dataIndex = context.dataIndex;
          const month = acquisitionData.value[dataIndex];
          return [`Items: ${month.count}`, `Value: $${month.value.toLocaleString()}`];
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
      },
    },
    y: {
      beginAtZero: true,
      grid: { color: "rgba(0,0,0,0.05)" },
      ticks: {
        font: { size: 10 },
        callback: (value: number) => `$${(value / 1000).toFixed(0)}k`,
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
        label: (context: any) => {
          const value = context.raw;
          const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
          const pct = ((value / total) * 100).toFixed(1);
          return `$${value.toLocaleString()} (${pct}%)`;
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
        label: (context: any) => `${context.raw} items`,
      },
    },
  },
  scales: {
    x: {
      beginAtZero: true,
      grid: { color: "rgba(0,0,0,0.05)" },
      ticks: { font: { size: 10 } },
    },
    y: {
      grid: { display: false },
      ticks: { font: { size: 10 } },
    },
  },
};

// Computed chart data
const acquisitionChartData = computed(() => ({
  labels: acquisitionData.value.map((d) => {
    const date = new Date(d.year, d.month - 1);
    return date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
  }),
  datasets: [
    {
      label: "Value Added",
      data: acquisitionData.value.map((d) => d.value),
      borderColor: chartColors.primary,
      backgroundColor: chartColors.primaryLight,
      fill: true,
      tension: 0.3,
      pointRadius: 3,
      pointHoverRadius: 5,
    },
  ],
}));

const binderChartData = computed(() => ({
  labels: binderData.value.map((d) => d.binder),
  datasets: [
    {
      data: binderData.value.map((d) => d.count),
      backgroundColor: [
        chartColors.burgundy,
        chartColors.gold,
        chartColors.primary,
        chartColors.accent1,
        chartColors.accent2,
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

// Fetch all data
onMounted(async () => {
  try {
    const [acqRes, binderRes, eraRes, pubRes] = await Promise.all([
      api.get("/stats/acquisitions-by-month"),
      api.get("/stats/bindings"),
      api.get("/stats/by-era"),
      api.get("/stats/by-publisher"),
    ]);

    acquisitionData.value = acqRes.data;
    binderData.value = binderRes.data;
    eraData.value = eraRes.data;
    publisherData.value = pubRes.data;
  } catch (e) {
    console.error("Failed to load statistics", e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="mt-8">
    <h2 class="text-xl font-semibold text-gray-800 mb-4">Collection Analytics</h2>

    <div v-if="loading" class="text-center py-8">
      <p class="text-gray-500">Loading charts...</p>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
      <!-- Acquisition Trends -->
      <div class="card !p-4 col-span-1 lg:col-span-2">
        <h3 class="text-sm font-medium text-gray-700 mb-3">Value Growth by Month</h3>
        <div class="h-48 md:h-64">
          <Line
            v-if="acquisitionData.length > 0"
            :data="acquisitionChartData"
            :options="lineChartOptions"
          />
          <p v-else class="text-gray-400 text-sm text-center py-8">No acquisition data available</p>
        </div>
      </div>

      <!-- Premium Bindings Distribution -->
      <div class="card !p-4">
        <h3 class="text-sm font-medium text-gray-700 mb-3">Premium Bindings</h3>
        <div class="h-48 md:h-56">
          <Doughnut
            v-if="binderData.length > 0"
            :data="binderChartData"
            :options="doughnutOptions"
          />
          <p v-else class="text-gray-400 text-sm text-center py-8">No binding data available</p>
        </div>
      </div>

      <!-- Era Distribution -->
      <div class="card !p-4">
        <h3 class="text-sm font-medium text-gray-700 mb-3">Books by Era</h3>
        <div class="h-48 md:h-56">
          <Bar v-if="eraData.length > 0" :data="eraChartData" :options="barChartOptions" />
          <p v-else class="text-gray-400 text-sm text-center py-8">No era data available</p>
        </div>
      </div>

      <!-- Top Tier 1 Publishers -->
      <div class="card !p-4 col-span-1 lg:col-span-2">
        <h3 class="text-sm font-medium text-gray-700 mb-3">Top Tier 1 Publishers</h3>
        <div class="h-40 md:h-48">
          <Bar
            v-if="publisherData.length > 0"
            :data="publisherChartData"
            :options="barChartOptions"
          />
          <p v-else class="text-gray-400 text-sm text-center py-8">No publisher data available</p>
        </div>
      </div>
    </div>
  </div>
</template>
