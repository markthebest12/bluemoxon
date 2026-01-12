<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import type { TooltipItem, ChartEvent, ActiveElement } from "chart.js";
import type { DashboardStats } from "@/types/dashboard";
import { formatAcquisitionTooltip } from "./chartHelpers";
import { navigateToBooks } from "@/utils/chart-navigation";
import { formatConditionGrade } from "@/utils/format";
import { useDashboardStore } from "@/stores/dashboard";

const router = useRouter();
const dashboardStore = useDashboardStore();

// Time range options for the selector buttons
const timeRangeOptions = [
  { days: 7, label: "1W" },
  { days: 30, label: "1M" },
  { days: 90, label: "3M" },
  { days: 180, label: "6M" },
];

// Dynamic chart title based on selected days
const valueGrowthTitle = computed(() => {
  const days = dashboardStore.selectedDays;
  if (days === 7) return "Est. Value Growth (Last 1 Week)";
  if (days === 30) return "Est. Value Growth (Last 1 Month)";
  if (days === 90) return "Est. Value Growth (Last 3 Months)";
  if (days === 180) return "Est. Value Growth (Last 6 Months)";
  return `Est. Value Growth (Last ${days} Days)`;
});
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
  onClick: (event: ChartEvent, elements: ActiveElement[]) => {
    if (elements.length > 0) {
      const index = elements[0].index;
      const day = props.data.acquisitions_daily[index];
      if (day?.date) {
        navigateToBooks(router, { date_acquired: day.date }, event.native);
      }
    }
  },
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

// Factory function for doughnut chart options to reduce duplication
function createDoughnutChartOptions(onClick: (index: number, nativeEvent?: Event | null) => void) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    onClick: (event: ChartEvent, elements: ActiveElement[]) => {
      if (elements.length > 0) {
        onClick(elements[0].index, event.native);
      }
    },
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
}

// Chart-specific options with click handlers
const conditionChartOptions = computed(() =>
  createDoughnutChartOptions((index: number, nativeEvent?: Event | null) => {
    const condition = props.data.by_condition[index]?.condition;
    if (condition) {
      // navigateToBooks handles "Ungraded" -> condition_grade__isnull=true
      navigateToBooks(router, { condition_grade: condition }, nativeEvent);
    }
  })
);

const categoryChartOptions = computed(() =>
  createDoughnutChartOptions((index: number, nativeEvent?: Event | null) => {
    const category = props.data.by_category[index]?.category;
    if (category) {
      // navigateToBooks handles "Uncategorized" -> category__isnull=true
      navigateToBooks(router, { category }, nativeEvent);
    }
  })
);

const bindingsChartOptions = computed(() =>
  createDoughnutChartOptions((index: number, nativeEvent?: Event | null) => {
    const binder = props.data.bindings[index];
    if (binder?.binder_id) {
      navigateToBooks(
        router,
        { binder_id: binder.binder_id, binding_authenticated: "true" },
        nativeEvent
      );
    }
  })
);

const eraChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: "y" as const,
  onClick: (event: ChartEvent, elements: ActiveElement[]) => {
    if (elements.length > 0) {
      const index = elements[0].index;
      const era = props.data.by_era[index]?.era;
      if (era) {
        navigateToBooks(router, { era }, event.native);
      }
    }
  },
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
}));

const publisherChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: "y" as const,
  onClick: (event: ChartEvent, elements: ActiveElement[]) => {
    if (elements.length > 0) {
      const index = elements[0].index;
      // Match chart data: filter to TIER_1 and slice to top 5
      const tier1 = props.data.by_publisher.filter((p) => p.tier === "TIER_1").slice(0, 5);
      const publisher = tier1[index];
      if (publisher?.publisher_id) {
        navigateToBooks(router, { publisher_id: publisher.publisher_id }, event.native);
      }
    }
  },
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
}));

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

// Explicit color mapping for condition grades (not index-based)
// Uses high-contrast colors: best conditions = cool/green, worst = warm/red
const conditionColors: Record<string, string> = {
  // Best conditions - greens/teals
  FINE: chartColors.primary, // Deep hunter green
  Fine: chartColors.primary,
  NEAR_FINE: chartColors.hunter700, // Lighter green
  Near_Fine: chartColors.hunter700,
  // Good conditions - golds/yellows
  VERY_GOOD: chartColors.gold, // Bright gold
  Very_Good: chartColors.gold,
  "VG+": chartColors.gold,
  VG: "rgb(218, 165, 32)", // Goldenrod - distinct from gold
  "VG-": chartColors.goldMuted,
  // Mid conditions - distinct warm tones
  "GOOD+": "rgb(205, 133, 63)", // Peru/tan
  "Good+": "rgb(205, 133, 63)",
  GOOD: chartColors.burgundy, // Deep burgundy
  Good: chartColors.burgundyLight, // Lighter burgundy (for case mismatch)
  // Poor conditions - reds/grays
  FAIR: "rgb(178, 102, 102)", // Muted red
  Fair: "rgb(178, 102, 102)",
  POOR: "rgb(139, 69, 69)", // Dark red-brown
  Poor: "rgb(139, 69, 69)",
  // Ungraded - neutral gray
  Ungraded: "rgb(160, 160, 160)",
};

// Fallback color for unknown conditions - bright orange to stand out
const getConditionColor = (condition: string): string =>
  conditionColors[condition] ?? "rgb(255, 140, 0)";

const conditionChartData = computed(() => {
  const conditions = props.data?.by_condition ?? [];
  return {
    labels: conditions.map((d) => formatConditionGrade(d.condition)),
    datasets: [
      {
        data: conditions.map((d) => d.count),
        backgroundColor: conditions.map((d) => getConditionColor(d.condition)),
        borderWidth: 0,
      },
    ],
  };
});

// Category colors - use rotating palette with fallback
const categoryPalette = [
  chartColors.burgundy,
  chartColors.gold,
  chartColors.primary,
  chartColors.hunter700,
  chartColors.goldMuted,
  chartColors.burgundyLight,
  chartColors.inkMuted,
  chartColors.paperAntique,
];

const categoryChartData = computed(() => {
  const categories = props.data?.by_category ?? [];
  return {
    labels: categories.map((d) => d.category),
    datasets: [
      {
        data: categories.map((d) => d.count),
        backgroundColor: categories.map((_, i) => categoryPalette[i % categoryPalette.length]),
        borderWidth: 0,
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
  onClick: (event: ChartEvent, elements: ActiveElement[]) => {
    if (elements.length > 0) {
      const index = elements[0].index;
      const author = filteredAuthorData.value[index];
      if (author?.author_id) {
        navigateToBooks(router, { author_id: author.author_id }, event.native);
      }
    }
  },
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
            :options="bindingsChartOptions"
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
            :options="eraChartOptions"
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
          <Bar
            v-if="hasTier1Publishers"
            :data="publisherChartData"
            :options="publisherChartOptions"
          />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No Tier 1 publisher data available
          </p>
        </div>
      </div>

      <!-- Condition Grade Distribution -->
      <div class="card-static p-4!">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Books by Condition
        </h3>
        <div class="h-48 md:h-56">
          <Doughnut
            v-if="props.data?.by_condition?.length > 0"
            :data="conditionChartData"
            :options="conditionChartOptions"
          />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No condition data available
          </p>
        </div>
      </div>

      <!-- Category Distribution -->
      <div class="card-static p-4!">
        <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
          Books by Category
        </h3>
        <div class="h-48 md:h-56">
          <Doughnut
            v-if="props.data?.by_category?.length > 0"
            :data="categoryChartData"
            :options="categoryChartOptions"
          />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No category data available
          </p>
        </div>
      </div>

      <!-- Cumulative Value Growth - full width at bottom -->
      <div class="card-static p-4! col-span-1 lg:col-span-2">
        <div class="flex items-center justify-between mb-3">
          <h3
            data-testid="value-growth-title"
            class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider"
          >
            {{ valueGrowthTitle }}
          </h3>
          <div class="flex gap-1">
            <button
              v-for="option in timeRangeOptions"
              :key="option.days"
              data-testid="time-range-btn"
              class="time-range-btn"
              :class="{ active: dashboardStore.selectedDays === option.days }"
              @click="dashboardStore.setDays(option.days)"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
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

<style scoped>
/* Make charts show clickable cursor */
:deep(canvas) {
  cursor: pointer;
}

/* Add hover effect to chart containers for visual affordance */
.card-static {
  transition: box-shadow 0.2s ease;
}

.card-static:hover {
  box-shadow: 0 0 0 2px rgba(26, 58, 47, 0.2);
}

/* Time range selector buttons */
.time-range-btn {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 9999px;
  border: 1px solid rgb(26, 58, 47);
  background-color: transparent;
  color: rgb(26, 58, 47);
  cursor: pointer;
  transition: all 0.15s ease;
}

.time-range-btn:hover {
  background-color: rgba(26, 58, 47, 0.1);
}

.time-range-btn.active {
  background-color: rgb(26, 58, 47);
  color: white;
}
</style>
