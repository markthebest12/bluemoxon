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

const scoreBadgeColor = computed(() => {
  if (!runbook.value) return "";
  return runbook.value.recommendation === "ACQUIRE"
    ? "bg-green-100 text-green-800"
    : "bg-yellow-100 text-yellow-800";
});

const fmvRange = computed(() => {
  if (!runbook.value?.fmv_low || !runbook.value?.fmv_high) return null;
  return `$${runbook.value.fmv_low.toFixed(0)}-$${runbook.value.fmv_high.toFixed(0)}`;
});

const priceDelta = computed(() => {
  if (!runbook.value?.current_asking_price || !runbook.value?.recommended_price) return null;
  return runbook.value.recommended_price - runbook.value.current_asking_price;
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
        ? (runbook.value.fmv_low + runbook.value.fmv_high) / 2
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
            <!-- Score Summary -->
            <div class="bg-gray-50 rounded-lg p-4">
              <div class="text-sm font-medium text-gray-600 mb-2">Strategic Fit Score</div>
              <div class="relative h-4 bg-gray-200 rounded-full overflow-hidden mb-2">
                <div
                  :class="scoreColor"
                  class="absolute h-full transition-all duration-300"
                  :style="{ width: `${runbook.total_score}%` }"
                ></div>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-2xl font-bold">{{ runbook.total_score }} / 100</span>
                <span :class="scoreBadgeColor" class="px-3 py-1 rounded-full text-sm font-medium">
                  {{ runbook.recommendation }}
                </span>
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
