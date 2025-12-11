<script setup lang="ts">
import { computed } from "vue";

interface Props {
  investmentGrade?: number | null;
  strategicFit?: number | null;
  collectionImpact?: number | null;
  overallScore?: number | null;
  compact?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  compact: false,
});

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
  </div>
</template>
