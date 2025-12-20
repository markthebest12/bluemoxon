<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import {
  useEvalRunbookStore,
  type EvalRunbook,
  type PriceUpdatePayload,
} from "@/stores/evalRunbook";

const props = defineProps<{
  bookId: number;
  bookTitle: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const store = useEvalRunbookStore();
const loading = ref(true);
const runbook = ref<EvalRunbook | null>(null);

// Accordion state
const openSections = ref<Set<string>>(new Set(["identification"]));

// Price edit state
const showPriceEdit = ref(false);
const priceForm = ref<PriceUpdatePayload>({
  new_price: 0,
  discount_code: "",
  notes: "",
});
const priceUpdatePreview = ref<{ scoreDelta: number; newScore: number } | null>(null);
const updatingPrice = ref(false);

// Full analysis state
const refreshing = ref(false);
const refreshError = ref<string | null>(null);
const refreshSuccess = ref(false);

onMounted(async () => {
  document.body.style.overflow = "hidden";
  try {
    runbook.value = await store.fetchRunbook(props.bookId);
    if (runbook.value) {
      priceForm.value.new_price = runbook.value.current_asking_price || 0;
    }
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  document.body.style.overflow = "";
  store.clearRunbook();
});

const scoreColor = computed(() => {
  if (!runbook.value) return "bg-gray-200";
  const score = runbook.value.total_score;
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-yellow-500";
  return "bg-red-500";
});

const tierBadgeConfig = computed(() => {
  if (!runbook.value?.recommendation_tier) {
    // Fallback to legacy recommendation
    return runbook.value?.recommendation === "ACQUIRE"
      ? { bg: "bg-green-100", text: "text-green-800", label: "ACQUIRE", icon: "" }
      : { bg: "bg-yellow-100", text: "text-yellow-800", label: "PASS", icon: "" };
  }

  const configs: Record<string, { bg: string; text: string; icon: string }> = {
    STRONG_BUY: { bg: "bg-green-500", text: "text-white", icon: "✓✓" },
    BUY: { bg: "bg-green-100", text: "text-green-800", icon: "✓" },
    CONDITIONAL: { bg: "bg-amber-100", text: "text-amber-800", icon: "⚠" },
    PASS: { bg: "bg-gray-100", text: "text-gray-800", icon: "✗" },
  };

  const config = configs[runbook.value.recommendation_tier] || configs.PASS;
  return { ...config, label: runbook.value.recommendation_tier };
});

const hasNapoleonOverride = computed(() => {
  return (
    runbook.value?.napoleon_recommendation &&
    runbook.value.napoleon_recommendation !== runbook.value.recommendation_tier
  );
});

const fmvRange = computed(() => {
  if (!runbook.value?.fmv_low || !runbook.value?.fmv_high) return null;
  const low = Number(runbook.value.fmv_low);
  const high = Number(runbook.value.fmv_high);
  return `$${low.toFixed(0)}-$${high.toFixed(0)}`;
});

const priceDelta = computed(() => {
  if (!runbook.value?.current_asking_price || !runbook.value?.recommended_price) return null;
  return runbook.value.recommended_price - runbook.value.current_asking_price;
});

// Check if full AI analysis is needed (quick import creates runbook without analysis)
const needsFullAnalysis = computed(() => {
  if (!runbook.value) return false;
  // If no analysis narrative and no FMV data, full analysis hasn't been run
  return (
    !runbook.value.analysis_narrative &&
    !runbook.value.ebay_comparables?.length &&
    !runbook.value.abebooks_comparables?.length
  );
});

function toggleSection(section: string) {
  if (openSections.value.has(section)) {
    openSections.value.delete(section);
  } else {
    openSections.value.add(section);
  }
}

function isSectionOpen(section: string): boolean {
  return openSections.value.has(section);
}

function openPriceEdit() {
  if (runbook.value) {
    priceForm.value = {
      new_price: runbook.value.current_asking_price || 0,
      discount_code: runbook.value.discount_code || "",
      notes: "",
    };
  }
  showPriceEdit.value = true;
}

function closePriceEdit() {
  showPriceEdit.value = false;
  priceUpdatePreview.value = null;
}

// Calculate preview when price changes
watch(
  () => priceForm.value.new_price,
  (newPrice) => {
    if (!runbook.value || !newPrice) {
      priceUpdatePreview.value = null;
      return;
    }
    // Simple estimate - real calculation happens on server
    const fmvMid =
      runbook.value.fmv_low && runbook.value.fmv_high
        ? (Number(runbook.value.fmv_low) + Number(runbook.value.fmv_high)) / 2
        : null;

    if (fmvMid) {
      const currentPricePoints = runbook.value.score_breakdown["Price vs FMV"]?.points || 0;
      const discountPct = ((fmvMid - newPrice) / fmvMid) * 100;

      let newPricePoints = 0;
      if (discountPct >= 30) newPricePoints = 20;
      else if (discountPct >= 15) newPricePoints = 10;
      else if (discountPct >= 0) newPricePoints = 5;

      const scoreDelta = newPricePoints - currentPricePoints;
      priceUpdatePreview.value = {
        scoreDelta,
        newScore: runbook.value.total_score + scoreDelta,
      };
    }
  }
);

async function submitPriceUpdate() {
  updatingPrice.value = true;
  try {
    const result = await store.updatePrice(props.bookId, priceForm.value);
    runbook.value = result.runbook;
    closePriceEdit();
  } catch (e) {
    console.error("Failed to update price:", e);
  } finally {
    updatingPrice.value = false;
  }
}

async function runFullAnalysis() {
  refreshing.value = true;
  refreshError.value = null;
  refreshSuccess.value = false;
  try {
    const result = await store.refreshRunbook(props.bookId);
    runbook.value = result.runbook;
    refreshSuccess.value = true;
    // Auto-hide success message after 3 seconds
    setTimeout(() => {
      refreshSuccess.value = false;
    }, 3000);
  } catch (e: any) {
    refreshError.value = e.response?.data?.detail || e.message || "Failed to run full analysis";
  } finally {
    refreshing.value = false;
  }
}

function handleClose() {
  emit("close");
}

function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="handleClose"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200 shrink-0">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">Eval Runbook</h2>
            <p class="text-sm text-gray-600 truncate">{{ bookTitle }}</p>
          </div>
          <button @click="handleClose" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-4">
          <!-- Loading -->
          <div v-if="loading" class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>

          <!-- Not Found -->
          <div v-else-if="!runbook" class="text-center py-12">
            <p class="text-gray-500">No eval runbook generated for this book.</p>
          </div>

          <!-- Runbook Content -->
          <div v-else class="space-y-4">
            <!-- Run Full Analysis Banner (shows when quick import was used) -->
            <div
              v-if="needsFullAnalysis && !refreshing"
              class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4"
            >
              <div class="flex items-start gap-3">
                <svg
                  class="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div class="flex-1">
                  <p class="text-sm text-amber-800 font-medium">Quick evaluation only</p>
                  <p class="text-sm text-amber-700 mt-1">
                    This runbook was created without AI image analysis or market price lookup. Run
                    full analysis for detailed condition assessment and FMV comparables.
                  </p>
                  <button
                    @click="runFullAnalysis"
                    class="mt-3 px-4 py-2 bg-amber-600 text-white text-sm font-medium rounded hover:bg-amber-700 flex items-center gap-2"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                      />
                    </svg>
                    Run Full Analysis
                  </button>
                </div>
              </div>
            </div>

            <!-- Refreshing state -->
            <div v-if="refreshing" class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div class="flex items-center gap-3">
                <div
                  class="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent"
                ></div>
                <div>
                  <p class="text-sm text-blue-800 font-medium">Running full analysis...</p>
                  <p class="text-sm text-blue-600">
                    Analyzing images and looking up market prices. This may take 30-60 seconds.
                  </p>
                </div>
              </div>
            </div>

            <!-- Refresh error -->
            <div
              v-if="refreshError"
              class="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 flex items-center gap-2"
            >
              <svg
                class="w-5 h-5 text-red-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span class="text-sm text-red-700">{{ refreshError }}</span>
            </div>

            <!-- Refresh success -->
            <div
              v-if="refreshSuccess"
              class="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 flex items-center gap-2"
            >
              <svg
                class="w-5 h-5 text-green-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span class="text-sm text-green-700">Full analysis completed successfully!</span>
            </div>

            <!-- Score Summary -->
            <div class="bg-gray-50 rounded-lg p-4">
              <!-- Tiered Recommendation Badge -->
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                  <span
                    :class="[tierBadgeConfig.bg, tierBadgeConfig.text]"
                    class="px-3 py-1.5 rounded-full text-sm font-bold flex items-center gap-1"
                  >
                    <span v-if="tierBadgeConfig.icon">{{ tierBadgeConfig.icon }}</span>
                    {{ tierBadgeConfig.label }}
                  </span>
                  <!-- Napoleon Override Indicator -->
                  <span
                    v-if="hasNapoleonOverride"
                    class="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded"
                  >
                    Napoleon: {{ runbook.napoleon_recommendation }}
                  </span>
                </div>
                <span class="text-sm text-gray-500">
                  v{{ runbook.scoring_version || "legacy" }}
                </span>
              </div>

              <!-- Score Bars -->
              <div class="space-y-3">
                <!-- Quality Score -->
                <div v-if="runbook.quality_score !== undefined">
                  <div class="flex justify-between text-sm mb-1">
                    <span class="text-gray-600">Quality</span>
                    <span class="font-medium">{{ runbook.quality_score }}/100</span>
                  </div>
                  <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-blue-500"
                      :style="{ width: `${runbook.quality_score}%` }"
                    ></div>
                  </div>
                  <div v-if="runbook.quality_floor_applied" class="text-xs text-red-500 mt-1">
                    ⚠ Below quality threshold
                  </div>
                </div>

                <!-- Strategic Fit Score -->
                <div v-if="runbook.strategic_fit_score !== undefined">
                  <div class="flex justify-between text-sm mb-1">
                    <span class="text-gray-600">Strategic Fit</span>
                    <span class="font-medium">{{ runbook.strategic_fit_score }}/100</span>
                  </div>
                  <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      class="h-full"
                      :class="runbook.strategic_fit_score < 30 ? 'bg-red-400' : 'bg-green-500'"
                      :style="{ width: `${runbook.strategic_fit_score}%` }"
                    ></div>
                  </div>
                  <div v-if="runbook.strategic_floor_applied" class="text-xs text-red-500 mt-1">
                    ⚠ Below strategic fit threshold
                  </div>
                </div>

                <!-- Combined Score (legacy fallback) -->
                <div v-else-if="runbook.combined_score !== undefined">
                  <div class="flex justify-between text-sm mb-1">
                    <span class="text-gray-600">Combined Score</span>
                    <span class="font-medium">{{ runbook.combined_score }}/100</span>
                  </div>
                  <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      class="h-full"
                      :class="scoreColor"
                      :style="{ width: `${runbook.combined_score}%` }"
                    ></div>
                  </div>
                </div>

                <!-- Legacy total_score fallback -->
                <div v-else>
                  <div class="flex justify-between text-sm mb-1">
                    <span class="text-gray-600">Total Score</span>
                    <span class="font-medium">{{ runbook.total_score }}/100</span>
                  </div>
                  <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      class="h-full"
                      :class="scoreColor"
                      :style="{ width: `${runbook.total_score}%` }"
                    ></div>
                  </div>
                </div>

                <!-- Price Position -->
                <div v-if="runbook.price_position" class="flex items-center gap-2 text-sm">
                  <span class="text-gray-600">Price Position:</span>
                  <span
                    :class="{
                      'text-green-600 font-medium': runbook.price_position === 'EXCELLENT',
                      'text-green-500': runbook.price_position === 'GOOD',
                      'text-amber-500': runbook.price_position === 'FAIR',
                      'text-red-500': runbook.price_position === 'POOR',
                    }"
                  >
                    {{ runbook.price_position }}
                  </span>
                </div>
              </div>

              <!-- Reasoning -->
              <div
                v-if="runbook.recommendation_reasoning"
                class="mt-4 p-3 bg-white rounded border text-sm text-gray-700"
              >
                {{ runbook.recommendation_reasoning }}
              </div>

              <!-- Suggested Offer (for CONDITIONAL) -->
              <div
                v-if="runbook.recommendation_tier === 'CONDITIONAL' && runbook.suggested_offer"
                class="mt-4 p-3 bg-amber-50 rounded border border-amber-200"
              >
                <div class="text-sm font-medium text-amber-800">Suggested Offer</div>
                <div class="text-lg font-bold text-amber-900">
                  {{ formatCurrency(runbook.suggested_offer) }}
                </div>
              </div>

              <!-- Pricing Row -->
              <div class="mt-4 grid grid-cols-4 gap-2 text-sm">
                <div>
                  <div class="text-gray-500">Asking</div>
                  <div class="font-medium flex items-center gap-1">
                    {{ formatCurrency(runbook.current_asking_price) }}
                    <button
                      @click="openPriceEdit"
                      class="text-blue-600 hover:text-blue-700"
                      title="Edit price"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
                <div>
                  <div class="text-gray-500">Est. FMV</div>
                  <div class="font-medium">{{ fmvRange || "-" }}</div>
                </div>
                <div>
                  <div class="text-gray-500">Recommend</div>
                  <div class="font-medium">{{ formatCurrency(runbook.recommended_price) }}</div>
                </div>
                <div>
                  <div class="text-gray-500">Delta</div>
                  <div
                    class="font-medium"
                    :class="priceDelta && priceDelta < 0 ? 'text-red-600' : 'text-green-600'"
                  >
                    {{ priceDelta ? formatCurrency(priceDelta) : "-" }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Accordion Sections -->
            <!-- Item Identification -->
            <div class="border border-gray-200 rounded-lg">
              <button
                @click="toggleSection('identification')"
                class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
              >
                <span class="font-medium">Item Identification</span>
                <svg
                  class="w-5 h-5 transition-transform"
                  :class="{ 'rotate-180': isSectionOpen('identification') }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
              <div v-if="isSectionOpen('identification')" class="p-3 pt-0 border-t border-gray-200">
                <dl class="grid grid-cols-2 gap-2 text-sm">
                  <template v-for="(value, key) in runbook.item_identification" :key="key">
                    <dt class="text-gray-500">{{ key }}</dt>
                    <dd class="font-medium">{{ value }}</dd>
                  </template>
                </dl>
              </div>
            </div>

            <!-- Condition Assessment -->
            <div class="border border-gray-200 rounded-lg">
              <button
                @click="toggleSection('condition')"
                class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
              >
                <span class="font-medium">Condition Assessment</span>
                <span class="text-sm text-gray-500 mr-2">{{ runbook.condition_grade || "-" }}</span>
              </button>
              <div
                v-if="isSectionOpen('condition')"
                class="p-3 pt-0 border-t border-gray-200 text-sm"
              >
                <div v-if="runbook.condition_positives?.length" class="mb-2">
                  <div class="font-medium text-green-700 mb-1">Positives</div>
                  <ul class="list-disc list-inside text-gray-600">
                    <li v-for="(item, i) in runbook.condition_positives" :key="i">{{ item }}</li>
                  </ul>
                </div>
                <div v-if="runbook.condition_negatives?.length">
                  <div class="font-medium text-red-700 mb-1">Negatives</div>
                  <ul class="list-disc list-inside text-gray-600">
                    <li v-for="(item, i) in runbook.condition_negatives" :key="i">{{ item }}</li>
                  </ul>
                </div>
              </div>
            </div>

            <!-- Strategic Scoring -->
            <div class="border border-gray-200 rounded-lg">
              <button
                @click="toggleSection('scoring')"
                class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
              >
                <span class="font-medium">Strategic Scoring</span>
                <span class="text-sm text-gray-500 mr-2">{{ runbook.total_score }} pts</span>
              </button>
              <div v-if="isSectionOpen('scoring')" class="p-3 pt-0 border-t border-gray-200">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="text-left text-gray-500">
                      <th class="pb-2">Criterion</th>
                      <th class="pb-2 text-center">Points</th>
                      <th class="pb-2">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(item, key) in runbook.score_breakdown"
                      :key="key"
                      class="border-t border-gray-100"
                    >
                      <td class="py-2">{{ key }}</td>
                      <td
                        class="py-2 text-center"
                        :class="item.points > 0 ? 'text-green-600 font-medium' : 'text-gray-400'"
                      >
                        {{ item.points > 0 ? `+${item.points}` : item.points }}
                      </td>
                      <td class="py-2 text-gray-600">{{ item.notes }}</td>
                    </tr>
                    <tr class="border-t-2 border-gray-300 font-medium">
                      <td class="py-2">TOTAL</td>
                      <td class="py-2 text-center">{{ runbook.total_score }}</td>
                      <td class="py-2 text-gray-600">
                        {{ runbook.total_score >= 80 ? "Meets threshold" : "Below 80pt threshold" }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- FMV Pricing -->
            <div class="border border-gray-200 rounded-lg">
              <button
                @click="toggleSection('fmv')"
                class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
              >
                <span class="font-medium">FMV Pricing</span>
                <span class="text-sm text-gray-500 mr-2">{{ fmvRange || "-" }}</span>
              </button>
              <div
                v-if="isSectionOpen('fmv')"
                class="p-3 pt-0 border-t border-gray-200 text-sm space-y-3"
              >
                <!-- eBay Sold -->
                <div v-if="runbook.ebay_comparables?.length">
                  <div class="font-medium mb-1">eBay Sold (last 90 days)</div>
                  <div class="space-y-1">
                    <div
                      v-for="(comp, i) in runbook.ebay_comparables"
                      :key="i"
                      class="flex justify-between text-gray-600"
                    >
                      <span class="truncate mr-2"
                        >{{ comp.title }} - {{ comp.condition || "N/A" }}</span
                      >
                      <span class="whitespace-nowrap">
                        {{ formatCurrency(comp.price) }}
                        <span v-if="comp.days_ago" class="text-gray-400 text-xs"
                          >{{ comp.days_ago }}d</span
                        >
                      </span>
                    </div>
                  </div>
                </div>

                <!-- AbeBooks -->
                <div v-if="runbook.abebooks_comparables?.length">
                  <div class="font-medium mb-1">AbeBooks (current)</div>
                  <div class="space-y-1">
                    <div
                      v-for="(comp, i) in runbook.abebooks_comparables"
                      :key="i"
                      class="flex justify-between text-gray-600"
                    >
                      <span class="truncate mr-2"
                        >{{ comp.title }} - {{ comp.condition || "N/A" }}</span
                      >
                      <span>{{ formatCurrency(comp.price) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Critical Issues -->
            <div class="border border-gray-200 rounded-lg">
              <button
                @click="toggleSection('issues')"
                class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
              >
                <span class="font-medium">Critical Issues & Recommendation</span>
                <span v-if="runbook.critical_issues?.length" class="text-sm text-yellow-600 mr-2">
                  {{ runbook.critical_issues.length }} issues
                </span>
              </button>
              <div v-if="isSectionOpen('issues')" class="p-3 pt-0 border-t border-gray-200 text-sm">
                <ul
                  v-if="runbook.critical_issues?.length"
                  class="list-disc list-inside text-gray-600 space-y-1"
                >
                  <li v-for="(issue, i) in runbook.critical_issues" :key="i">{{ issue }}</li>
                </ul>
                <p v-else class="text-gray-500">No critical issues identified.</p>
              </div>
            </div>

            <!-- Analysis Narrative -->
            <div class="border-t border-gray-200 pt-4">
              <div class="text-sm font-medium text-gray-600 mb-2 flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Analysis Findings
              </div>
              <div
                class="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 rounded-lg p-3 max-h-64 overflow-y-auto"
              >
                {{ runbook.analysis_narrative || "No analysis narrative available." }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Price Edit Modal -->
    <div
      v-if="showPriceEdit"
      class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
      @click.self="closePriceEdit"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div class="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 class="text-lg font-semibold">Update Asking Price</h3>
          <button @click="closePriceEdit" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <form @submit.prevent="submitPriceUpdate" class="p-4 space-y-4">
          <div>
            <div class="text-sm text-gray-500 mb-2">
              Original Listing Price: {{ formatCurrency(runbook?.original_asking_price) }}
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">New Price *</label>
            <div class="relative">
              <span class="absolute left-3 top-2 text-gray-500">$</span>
              <input
                v-model.number="priceForm.new_price"
                type="number"
                step="0.01"
                min="0"
                class="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Discount Code</label>
            <input
              v-model="priceForm.discount_code"
              type="text"
              placeholder="e.g., SAVE20"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              v-model="priceForm.notes"
              rows="2"
              placeholder="e.g., Seller accepted offer"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            ></textarea>
          </div>

          <!-- Score Impact Preview -->
          <div v-if="priceUpdatePreview" class="bg-gray-50 rounded-lg p-3 text-sm">
            <div class="font-medium mb-1">Score Impact Preview</div>
            <div>
              Current: {{ runbook?.total_score }} pts → New: {{ priceUpdatePreview.newScore }} pts
              <span :class="priceUpdatePreview.scoreDelta >= 0 ? 'text-green-600' : 'text-red-600'">
                ({{ priceUpdatePreview.scoreDelta >= 0 ? "+" : ""
                }}{{ priceUpdatePreview.scoreDelta }})
              </span>
            </div>
            <div class="text-gray-500">
              Status: {{ runbook?.recommendation }} →
              {{ priceUpdatePreview.newScore >= 80 ? "ACQUIRE" : "Still PASS" }}
              <span v-if="priceUpdatePreview.newScore < 80">
                (need {{ formatCurrency(runbook?.recommended_price) }} for ACQUIRE)
              </span>
            </div>
          </div>

          <div class="flex gap-3 pt-2">
            <button
              type="button"
              @click="closePriceEdit"
              class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="updatingPrice"
              class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ updatingPrice ? "Saving..." : "Save & Recalculate" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
