<script setup lang="ts">
import { computed, ref } from "vue";

interface ScoreFactor {
  name: string;
  points: number;
  reason: string;
}

interface ScoreBreakdownData {
  score: number;
  factors: ScoreFactor[];
}

interface BreakdownResponse {
  investment_grade: number;
  strategic_fit: number;
  collection_impact: number;
  overall_score: number;
  breakdown: {
    investment_grade: ScoreBreakdownData;
    strategic_fit: ScoreBreakdownData;
    collection_impact: ScoreBreakdownData;
  };
}

interface Props {
  bookId?: number;
  investmentGrade?: number | null;
  strategicFit?: number | null;
  collectionImpact?: number | null;
  overallScore?: number | null;
  compact?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  compact: false,
});

const emit = defineEmits<{
  recalculate: [];
}>();

const showBreakdown = ref(false);
const breakdownData = ref<BreakdownResponse | null>(null);
const loadingBreakdown = ref(false);

const scoreLabel = computed(() => {
  const score = props.overallScore;
  if (score === null || score === undefined) return "N/A";
  if (score >= 160) return "STRONG BUY";
  if (score >= 120) return "BUY";
  if (score >= 80) return "CONDITIONAL";
  return "PASS";
});

const scoreColor = computed(() => {
  const score = props.overallScore;
  if (score === null || score === undefined) return "bg-gray-200 text-gray-600";
  if (score >= 160) return "bg-green-500 text-white";
  if (score >= 120) return "bg-yellow-500 text-white";
  if (score >= 80) return "bg-orange-500 text-white";
  return "bg-red-500 text-white";
});

function formatScore(score?: number | null): string {
  if (score === null || score === undefined) return "-";
  return score.toString();
}

function formatPoints(points: number): string {
  if (points > 0) return `+${points}`;
  return points.toString();
}

function pointsClass(points: number): string {
  if (points > 0) return "text-green-600";
  if (points < 0) return "text-red-600";
  return "text-gray-500";
}

async function toggleBreakdown() {
  if (!props.bookId) return;

  if (showBreakdown.value) {
    showBreakdown.value = false;
    return;
  }

  if (!breakdownData.value) {
    loadingBreakdown.value = true;
    try {
      const { useBooksStore } = await import("@/stores/books");
      const store = useBooksStore();
      breakdownData.value = await store.fetchScoreBreakdown(props.bookId);
    } catch (e) {
      console.error("Failed to fetch breakdown:", e);
    } finally {
      loadingBreakdown.value = false;
    }
  }
  showBreakdown.value = true;
}

function handleRecalculate() {
  breakdownData.value = null;
  showBreakdown.value = false;
  emit("recalculate");
}
</script>

<template>
  <div v-if="compact" class="flex items-center gap-2">
    <span :class="[scoreColor, 'px-2 py-1 rounded text-xs font-bold']">
      {{ formatScore(overallScore) }}
    </span>
  </div>

  <div v-else class="border rounded-lg p-3 bg-white">
    <!-- Overall Score Header -->
    <div class="flex items-center justify-between mb-3">
      <span class="text-sm font-medium text-gray-600">SCORE</span>
      <span :class="[scoreColor, 'px-3 py-1 rounded font-bold text-sm']">
        {{ formatScore(overallScore) }} {{ scoreLabel }}
      </span>
    </div>

    <!-- Component Breakdown -->
    <div class="space-y-2 text-sm">
      <div class="flex justify-between items-center">
        <span class="text-gray-600">Investment</span>
        <div class="flex items-center gap-2">
          <div class="w-20 bg-gray-200 rounded-full h-2">
            <div
              class="bg-blue-500 h-2 rounded-full"
              :style="{ width: `${Math.min(investmentGrade || 0, 100)}%` }"
            ></div>
          </div>
          <span class="w-8 text-right font-medium">{{ formatScore(investmentGrade) }}</span>
        </div>
      </div>

      <div class="flex justify-between items-center">
        <span class="text-gray-600">Strategic</span>
        <div class="flex items-center gap-2">
          <div class="w-20 bg-gray-200 rounded-full h-2">
            <div
              class="bg-purple-500 h-2 rounded-full"
              :style="{ width: `${Math.min(strategicFit || 0, 100)}%` }"
            ></div>
          </div>
          <span class="w-8 text-right font-medium">{{ formatScore(strategicFit) }}</span>
        </div>
      </div>

      <div class="flex justify-between items-center">
        <span class="text-gray-600">Collection</span>
        <div class="flex items-center gap-2">
          <div class="w-20 bg-gray-200 rounded-full h-2">
            <div
              class="bg-teal-500 h-2 rounded-full"
              :style="{ width: `${Math.max(0, Math.min(collectionImpact || 0, 100))}%` }"
            ></div>
          </div>
          <span class="w-8 text-right font-medium">{{ formatScore(collectionImpact) }}</span>
        </div>
      </div>
    </div>

    <!-- Recalculate Link -->
    <div class="mt-3 pt-2 border-t flex items-center justify-between">
      <button
        v-if="bookId"
        @click="toggleBreakdown"
        class="text-xs text-blue-600 hover:text-blue-800 hover:underline"
        :disabled="loadingBreakdown"
      >
        <span v-if="loadingBreakdown">Loading...</span>
        <span v-else-if="showBreakdown">Hide Details</span>
        <span v-else>Show Details</span>
      </button>
      <button
        @click="handleRecalculate"
        class="text-xs text-blue-600 hover:text-blue-800 hover:underline"
      >
        Recalculate
      </button>
    </div>

    <!-- Detailed Breakdown -->
    <div v-if="showBreakdown && breakdownData" class="mt-3 pt-3 border-t space-y-4">
      <!-- Investment Grade Breakdown -->
      <div>
        <h4 class="text-xs font-semibold text-blue-600 uppercase mb-1">Investment Grade</h4>
        <div class="space-y-1">
          <div
            v-for="factor in breakdownData.breakdown.investment_grade.factors"
            :key="factor.name"
            class="flex justify-between text-xs"
          >
            <span class="text-gray-600 truncate mr-2">{{ factor.reason }}</span>
            <span :class="pointsClass(factor.points)" class="font-medium whitespace-nowrap">
              {{ formatPoints(factor.points) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Strategic Fit Breakdown -->
      <div>
        <h4 class="text-xs font-semibold text-purple-600 uppercase mb-1">Strategic Fit</h4>
        <div class="space-y-1">
          <div
            v-for="factor in breakdownData.breakdown.strategic_fit.factors"
            :key="factor.name"
            class="flex justify-between text-xs"
          >
            <span class="text-gray-600 truncate mr-2">{{ factor.reason }}</span>
            <span :class="pointsClass(factor.points)" class="font-medium whitespace-nowrap">
              {{ formatPoints(factor.points) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Collection Impact Breakdown -->
      <div>
        <h4 class="text-xs font-semibold text-teal-600 uppercase mb-1">Collection Impact</h4>
        <div class="space-y-1">
          <div
            v-for="factor in breakdownData.breakdown.collection_impact.factors"
            :key="factor.name"
            class="flex justify-between text-xs"
          >
            <span class="text-gray-600 truncate mr-2">{{ factor.reason }}</span>
            <span :class="pointsClass(factor.points)" class="font-medium whitespace-nowrap">
              {{ formatPoints(factor.points) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
