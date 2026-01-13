<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import type { TooltipItem, ChartEvent, ActiveElement } from "chart.js";
import type { DashboardStats, EraDefinition, AuthorData, PublisherData } from "@/types/dashboard";
import { formatAcquisitionTooltip, yAxisLabelTooltipPlugin } from "./chartHelpers";
import { navigateToBooks } from "@/utils/chart-navigation";
import { formatConditionGrade } from "@/utils/format";
import { useDashboardStore } from "@/stores/dashboard";
import BaseTooltip from "@/components/BaseTooltip.vue";

const router = useRouter();
const dashboardStore = useDashboardStore();

// Props - receive data from parent (moved up for helper access)
const props = defineProps<{
  data: DashboardStats;
}>();

// Helper to get condition label from API references (single source of truth)
function getConditionLabel(condition: string): string {
  const def = props.data.references?.conditions[condition];
  return def?.label ?? formatConditionGrade(condition);
}

// Helper to get condition description from API references (single source of truth)
function getConditionDescription(condition: string): string {
  // Use canonical condition value (e.g., "FINE", "VERY_GOOD")
  const def = props.data.references?.conditions[condition];
  return def?.description ?? "";
}

// Time range options for the selector buttons
const timeRangeOptions = [
  { days: 7, label: "1W", title: "1 Week" },
  { days: 30, label: "1M", title: "1 Month" },
  { days: 90, label: "3M", title: "3 Months" },
  { days: 180, label: "6M", title: "6 Months" },
];

// Dynamic chart title based on selected days
const valueGrowthTitle = computed(() => {
  const option = timeRangeOptions.find((o) => o.days === dashboardStore.selectedDays);
  const rangeText = option?.title ?? `${dashboardStore.selectedDays} Days`;
  return `Est. Value Growth (Last ${rangeText})`;
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
  Filler,
  yAxisLabelTooltipPlugin
);

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
function createDoughnutChartOptions(
  onClick: (index: number, nativeEvent?: Event | null) => void,
  options?: { hideLegend?: boolean }
) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    onClick: (event: ChartEvent, elements: ActiveElement[]) => {
      if (elements.length > 0) {
        onClick(elements[0].index, event.native);
      }
    },
    plugins: {
      legend: options?.hideLegend
        ? { display: false }
        : {
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
// Hide legend for condition chart - we render custom legend with tooltips
const conditionChartOptions = computed(() =>
  createDoughnutChartOptions(
    (index: number, nativeEvent?: Event | null) => {
      const condition = props.data.by_condition[index]?.condition;
      if (condition) {
        // navigateToBooks handles "Ungraded" -> condition_grade__isnull=true
        navigateToBooks(router, { condition_grade: condition }, nativeEvent);
      }
    },
    { hideLegend: true }
  )
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

// Hide legend for bindings chart - we render custom legend with tooltips
const bindingsChartOptions = computed(() =>
  createDoughnutChartOptions(
    (index: number, nativeEvent?: Event | null) => {
      const binder = props.data.bindings[index];
      if (binder?.binder_id) {
        navigateToBooks(
          router,
          { binder_id: binder.binder_id, binding_authenticated: "true" },
          nativeEvent
        );
      }
    },
    { hideLegend: true }
  )
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
        title: (items: TooltipItem<"bar">[]) => {
          if (items.length > 0) {
            const era = props.data.by_era[items[0].dataIndex]?.era;
            const def = props.data.references?.eras[era] as EraDefinition | undefined;
            return def ? `${def.label} (${def.years})` : era;
          }
          return "";
        },
        label: (context: TooltipItem<"bar">) => {
          const value = context.raw as number;
          const era = props.data.by_era[context.dataIndex]?.era;
          const def = props.data.references?.eras[era] as EraDefinition | undefined;
          const lines = [`${value} ${value === 1 ? "book" : "books"}`];
          if (def?.description) {
            lines.push(def.description);
          }
          return lines;
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

// Maximum number of tier 1 publishers to show in chart
const MAX_TIER1_PUBLISHERS = 5;

// Helper to get filtered tier1 publishers (used in both chart data and options)
const tier1Publishers = computed(() =>
  props.data.by_publisher.filter((p) => p.tier === "TIER_1").slice(0, MAX_TIER1_PUBLISHERS)
);

// Computed label tooltips for publisher chart (must match chart data order)
const publisherLabelTooltips = computed(() =>
  tier1Publishers.value.map((publisher) => formatPublisherLabelTooltip(publisher))
);

const publisherChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: "y" as const,
  // Label tooltips for Y-axis hover (via yAxisLabelTooltipPlugin)
  labelTooltips: publisherLabelTooltips.value,
  onClick: (event: ChartEvent, elements: ActiveElement[]) => {
    if (elements.length > 0) {
      const index = elements[0].index;
      const publisher = tier1Publishers.value[index];
      if (publisher?.publisher_id) {
        navigateToBooks(router, { publisher_id: publisher.publisher_id }, event.native);
      }
    }
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        // Bar tooltip: Simple count. Hover on publisher name for full details.
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

const publisherChartData = computed(() => ({
  labels: tier1Publishers.value.map((d) => d.publisher),
  datasets: [
    {
      data: tier1Publishers.value.map((d) => d.count),
      backgroundColor: chartColors.gold,
      borderRadius: 4,
    },
  ],
}));

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
    labels: conditions.map((d) => getConditionLabel(d.condition)),
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

// Helper to format author lifespan
function formatAuthorLifespan(author: {
  birth_year?: number | null;
  death_year?: number | null;
}): string {
  if (author.birth_year && author.death_year) {
    return `${author.birth_year}–${author.death_year}`;
  } else if (author.birth_year) {
    return `b. ${author.birth_year}`;
  } else if (author.death_year) {
    return `d. ${author.death_year}`;
  }
  return "Dates unknown";
}

// Helper to format binder operation years
function formatBinderYears(binder: {
  founded_year?: number | null;
  closed_year?: number | null;
}): string | null {
  if (binder.founded_year && binder.closed_year) {
    return `${binder.founded_year}–${binder.closed_year}`;
  } else if (binder.founded_year) {
    return `Est. ${binder.founded_year}`;
  }
  return null;
}

// Helper to format binder tooltip content with dates and sample titles
function formatBinderTooltip(binder: {
  full_name?: string | null;
  binder: string;
  count: number;
  founded_year?: number | null;
  closed_year?: number | null;
  sample_titles?: string[];
  has_more?: boolean;
}): string {
  const lines: string[] = [];

  // Full name
  if (binder.full_name) {
    lines.push(binder.full_name);
  }

  // Operation years
  const years = formatBinderYears(binder);
  if (years) {
    lines.push(years);
  }

  // Book count
  lines.push(`${binder.count} ${binder.count === 1 ? "book" : "books"}`);

  // Sample titles
  if (binder.sample_titles && binder.sample_titles.length > 0) {
    binder.sample_titles.forEach((title: string) => {
      const truncated = title.length > 35 ? title.substring(0, 32) + "..." : title;
      lines.push(`  • ${truncated}`);
    });
    if (binder.has_more) {
      const moreCount = binder.count - binder.sample_titles.length;
      lines.push(`  ...and ${moreCount} more`);
    }
  }

  return lines.join("\n");
}

// Helper to format author tooltip for Y-axis label hover
function formatAuthorLabelTooltip(author: AuthorData): string {
  const lines: string[] = [];

  // Era and lifespan
  const lifespan = formatAuthorLifespan(author);
  if (author.era || lifespan) {
    const parts = [];
    if (author.era) parts.push(author.era);
    if (lifespan) parts.push(lifespan);
    lines.push(parts.join(" • "));
  }

  // Book/title count
  lines.push(
    `${author.count} ${author.count === 1 ? "book" : "books"} across ${author.titles} ${author.titles === 1 ? "title" : "titles"}`
  );

  // Sample titles
  if (author.sample_titles && author.sample_titles.length > 0) {
    author.sample_titles.forEach((title: string) => {
      const truncated = title.length > 35 ? title.substring(0, 32) + "..." : title;
      lines.push(`  • ${truncated}`);
    });
    if (author.has_more) {
      const moreCount = author.titles - author.sample_titles.length;
      lines.push(`  ...and ${moreCount} more`);
    }
  }

  return lines.join("\n");
}

// Helper to format publisher tooltip for Y-axis label hover
function formatPublisherLabelTooltip(publisher: PublisherData): string {
  const lines: string[] = [];

  // Founded year
  if (publisher.founded_year) {
    lines.push(`Founded: ${publisher.founded_year}`);
  }

  // Book count
  lines.push(`${publisher.count} ${publisher.count === 1 ? "book" : "books"}`);

  // Description (truncate if long)
  if (publisher.description) {
    const desc = publisher.description;
    if (desc.length > 80) {
      lines.push(desc.substring(0, 77) + "...");
    } else {
      lines.push(desc);
    }
  }

  return lines.join("\n");
}

// Computed label tooltips for author chart (must match chart data order)
const authorLabelTooltips = computed(() =>
  filteredAuthorData.value.slice(0, 8).map((author) => formatAuthorLabelTooltip(author))
);

// Custom options for author chart with enhanced tooltips showing era and book titles
const authorChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: "y" as const,
  // Label tooltips for Y-axis hover (via yAxisLabelTooltipPlugin)
  labelTooltips: authorLabelTooltips.value,
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
        // Bar tooltip: Simple count/value. Hover on author name for full details.
        label: (context: TooltipItem<"bar">) => {
          const value = context.raw as number;
          const author = filteredAuthorData.value[context.dataIndex];
          const titles = author?.titles ?? 0;
          return `${value} ${value === 1 ? "book" : "books"} across ${titles} ${titles === 1 ? "title" : "titles"}`;
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
        <div class="h-36 md:h-44">
          <Doughnut
            v-if="props.data.bindings.length > 0"
            :data="binderChartData"
            :options="bindingsChartOptions"
          />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No binding data available
          </p>
        </div>
        <!-- Custom legend with tooltips for binder full names -->
        <div
          v-if="props.data.bindings.length > 0"
          class="chart-legend flex flex-wrap justify-center gap-x-3 gap-y-1 mt-2"
        >
          <BaseTooltip
            v-for="(binder, index) in props.data.bindings"
            :key="binder.binder_id"
            :content="formatBinderTooltip(binder)"
            position="top"
          >
            <button
              class="legend-btn flex items-center gap-1 text-xs cursor-pointer hover:opacity-80"
              :aria-label="`Filter books by ${binder.full_name || binder.binder} binding`"
              @click="
                navigateToBooks(router, {
                  binder_id: binder.binder_id,
                  binding_authenticated: 'true',
                })
              "
            >
              <span
                class="w-3 h-3 rounded-sm inline-block"
                :style="{ backgroundColor: binderChartData.datasets[0].backgroundColor[index] }"
              ></span>
              <span class="text-gray-600">{{ binder.binder }}</span>
            </button>
          </BaseTooltip>
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
        <div class="h-36 md:h-44">
          <Doughnut
            v-if="props.data?.by_condition?.length > 0"
            :data="conditionChartData"
            :options="conditionChartOptions"
          />
          <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
            No condition data available
          </p>
        </div>
        <!-- Custom legend with tooltips -->
        <div
          v-if="props.data?.by_condition?.length > 0"
          class="chart-legend flex flex-wrap justify-center gap-x-3 gap-y-1 mt-2"
        >
          <BaseTooltip
            v-for="(item, index) in props.data.by_condition"
            :key="item.condition"
            :content="getConditionDescription(item.condition) || item.condition"
            position="top"
          >
            <button
              class="legend-btn flex items-center gap-1 text-xs cursor-pointer hover:opacity-80"
              :aria-label="`Filter books by ${getConditionLabel(item.condition)} condition`"
              @click="navigateToBooks(router, { condition_grade: item.condition })"
            >
              <span
                class="w-3 h-3 rounded-sm inline-block"
                :style="{ backgroundColor: conditionChartData.datasets[0].backgroundColor[index] }"
              ></span>
              <span class="text-gray-600">{{ getConditionLabel(item.condition) }}</span>
            </button>
          </BaseTooltip>
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
              :disabled="dashboardStore.loading"
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
  padding: 0.5rem 0.75rem;
  min-height: 2.75rem; /* 44px - iOS recommended touch target */
  min-width: 2.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 9999px;
  border: 1px solid var(--color-accent-primary);
  background-color: transparent;
  color: var(--color-accent-primary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.time-range-btn:hover {
  background-color: color-mix(in srgb, var(--color-accent-primary) 15%, transparent);
}

.time-range-btn.active {
  background-color: var(--color-accent-primary);
  color: var(--color-surface-primary);
}

.time-range-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Chart legend container - handle overflow with scroll */
.chart-legend {
  max-height: 4rem; /* ~3 rows of legend items */
  overflow-y: auto;
}

/* Legend button accessibility - focus styles for keyboard navigation */
.legend-btn {
  border-radius: 0.125rem;
}

.legend-btn:focus {
  outline: 2px solid var(--color-accent-primary);
  outline-offset: 2px;
}

.legend-btn:focus:not(:focus-visible) {
  outline: none;
}

.legend-btn:focus-visible {
  outline: 2px solid var(--color-accent-primary);
  outline-offset: 2px;
}
</style>
