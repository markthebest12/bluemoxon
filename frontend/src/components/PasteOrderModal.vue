<script setup lang="ts">
import { ref } from "vue";
import { api } from "@/services/api";
import TransitionModal from "./TransitionModal.vue";

const props = defineProps<{
  visible: boolean;
}>();

interface ExtractedData {
  order_number?: string;
  item_price?: number;
  shipping?: number;
  total?: number;
  currency?: string;
  total_usd?: number;
  purchase_date?: string;
  platform?: string;
  estimated_delivery?: string;
  tracking_number?: string;
  confidence: number;
  used_llm: boolean;
  field_confidence: Record<string, number>;
}

const emit = defineEmits<{
  close: [];
  apply: [data: ExtractedData];
}>();

const pastedText = ref("");
const extractedData = ref<ExtractedData | null>(null);
const extracting = ref(false);
const error = ref("");

async function handleExtract() {
  if (!pastedText.value.trim()) {
    error.value = "Please paste order text";
    return;
  }

  extracting.value = true;
  error.value = "";

  try {
    const res = await api.post("/orders/extract", { text: pastedText.value });
    extractedData.value = res.data;

    if (!res.data.order_number && !res.data.total) {
      error.value = "Could not extract order details. Try a different format.";
      extractedData.value = null;
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || "Extraction failed";
  } finally {
    extracting.value = false;
  }
}

function handleApply() {
  if (extractedData.value) {
    emit("apply", extractedData.value);
  }
}

function handleBack() {
  extractedData.value = null;
  error.value = "";
}

function getConfidenceIcon(field: string): string {
  const conf = extractedData.value?.field_confidence[field] || 0;
  return conf >= 0.8 ? "check" : "warning";
}

function getConfidenceClass(field: string): string {
  const conf = extractedData.value?.field_confidence[field] || 0;
  return conf >= 0.8 ? "text-green-600" : "text-yellow-600";
}

async function copyTracking() {
  if (extractedData.value?.tracking_number) {
    await navigator.clipboard.writeText(extractedData.value.tracking_number);
  }
}

function getCurrencySymbol(currency: string): string {
  const symbols: Record<string, string> = {
    GBP: "£",
    EUR: "€",
    USD: "$",
  };
  return symbols[currency] || "$";
}

function handleClose() {
  if (!extracting.value) {
    emit("close");
  }
}
</script>

<template>
  <TransitionModal :visible="visible" @backdrop-click="handleClose">
    <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200 shrink-0">
          <h2 class="text-lg font-semibold text-gray-900">
            {{ extractedData ? "Extracted Order Details" : "Paste Order Details" }}
          </h2>
          <button
            @click="handleClose"
            :disabled="extracting"
            class="text-gray-500 hover:text-gray-700 disabled:opacity-50"
          >
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

        <!-- Input State -->
        <div v-if="!extractedData" class="p-4 flex flex-col gap-4 overflow-y-auto flex-1">
          <p class="text-sm text-gray-600">Paste your eBay order confirmation email text below.</p>
          <textarea
            v-model="pastedText"
            rows="10"
            class="input font-mono"
            placeholder="Your order has been confirmed!&#10;Order number: 21-13904-88107&#10;..."
          ></textarea>
          <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
          <div class="flex justify-end gap-2">
            <button @click="handleClose" class="btn-secondary">Cancel</button>
            <button @click="handleExtract" :disabled="extracting" class="btn-primary">
              {{ extracting ? "Extracting..." : "Extract" }}
            </button>
          </div>
        </div>

        <!-- Results State -->
        <div v-else class="p-4 flex flex-col gap-4 overflow-y-auto flex-1">
          <div
            v-if="extractedData.used_llm"
            class="text-xs text-victorian-hunter-600 bg-moxon-50 px-2 py-1 rounded-sm inline-block"
          >
            Enhanced with AI
          </div>

          <div class="flex flex-col gap-2">
            <div v-if="extractedData.order_number" class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Order Number</span>
              <span class="font-medium flex items-center gap-1">
                {{ extractedData.order_number }}
                <span :class="getConfidenceClass('order_number')">
                  <svg
                    v-if="getConfidenceIcon('order_number') === 'check'"
                    class="w-4 h-4"
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
                  <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </span>
              </span>
            </div>

            <div v-if="extractedData.total" class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Total</span>
              <span class="font-medium flex items-center gap-1">
                {{ getCurrencySymbol(extractedData.currency || "USD")
                }}{{ extractedData.total?.toFixed(2) }}
                <span
                  v-if="extractedData.total_usd && extractedData.currency !== 'USD'"
                  class="text-gray-500 text-sm"
                >
                  (${{ extractedData.total_usd?.toFixed(2) }})
                </span>
                <span :class="getConfidenceClass('total')">
                  <svg
                    v-if="getConfidenceIcon('total') === 'check'"
                    class="w-4 h-4"
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
                  <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </span>
              </span>
            </div>

            <div v-if="extractedData.item_price" class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Item Price</span>
              <span class="font-medium flex items-center gap-1">
                {{ getCurrencySymbol(extractedData.currency || "USD")
                }}{{ extractedData.item_price?.toFixed(2) }}
                <span :class="getConfidenceClass('item_price')">
                  <svg
                    v-if="getConfidenceIcon('item_price') === 'check'"
                    class="w-4 h-4"
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
                  <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </span>
              </span>
            </div>

            <div v-if="extractedData.shipping" class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Shipping</span>
              <span class="font-medium flex items-center gap-1">
                {{ getCurrencySymbol(extractedData.currency || "USD")
                }}{{ extractedData.shipping?.toFixed(2) }}
                <span :class="getConfidenceClass('shipping')">
                  <svg
                    v-if="getConfidenceIcon('shipping') === 'check'"
                    class="w-4 h-4"
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
                  <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </span>
              </span>
            </div>

            <div v-if="extractedData.purchase_date" class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Purchase Date</span>
              <span class="font-medium flex items-center gap-1">
                {{ extractedData.purchase_date }}
                <span :class="getConfidenceClass('purchase_date')">
                  <svg
                    v-if="getConfidenceIcon('purchase_date') === 'check'"
                    class="w-4 h-4"
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
                  <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </span>
              </span>
            </div>

            <div v-if="extractedData.estimated_delivery" class="flex justify-between items-center">
              <span class="text-sm text-gray-600">Est. Delivery</span>
              <span class="font-medium flex items-center gap-1">
                {{ extractedData.estimated_delivery }}
                <span :class="getConfidenceClass('estimated_delivery')">
                  <svg
                    v-if="getConfidenceIcon('estimated_delivery') === 'check'"
                    class="w-4 h-4"
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
                  <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </span>
              </span>
            </div>

            <!-- Tracking Number (display only with copy) -->
            <div
              v-if="extractedData.tracking_number"
              class="flex justify-between items-center bg-gray-50 p-2 rounded-sm"
            >
              <span class="text-sm text-gray-600">Tracking</span>
              <div class="flex items-center gap-2">
                <code class="text-xs bg-gray-100 px-2 py-1 rounded-sm">{{
                  extractedData.tracking_number
                }}</code>
                <button @click="copyTracking" class="link text-xs" title="Copy">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <div class="text-xs text-gray-500 flex items-center gap-2">
            <svg
              class="w-4 h-4 text-green-600"
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
            <span>High confidence</span>
            <span class="mx-1">|</span>
            <svg
              class="w-4 h-4 text-yellow-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <span>Review recommended</span>
          </div>

          <div class="flex justify-end gap-2 pt-2 border-t">
            <button @click="handleBack" class="btn-secondary">Back</button>
            <button @click="handleApply" class="btn-primary">Apply to Form</button>
          </div>
        </div>
      </div>
  </TransitionModal>
</template>
