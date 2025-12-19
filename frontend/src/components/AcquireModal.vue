<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useAcquisitionsStore, type AcquirePayload } from "@/stores/acquisitions";
import { api } from "@/services/api";
import PasteOrderModal from "./PasteOrderModal.vue";

const props = defineProps<{
  bookId: number;
  bookTitle: string;
  valueMid?: number;
}>();

const emit = defineEmits<{
  close: [];
  acquired: [];
}>();

const acquisitionsStore = useAcquisitionsStore();

type Currency = "USD" | "GBP" | "EUR";
const selectedCurrency = ref<Currency>("USD");
const exchangeRates = ref({ gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 });
const loadingRates = ref(false);

const form = ref<AcquirePayload>({
  purchase_price: 0,
  purchase_date: new Date().toISOString().split("T")[0],
  order_number: "",
  place_of_purchase: "eBay",
  estimated_delivery: undefined,
  tracking_number: undefined,
  tracking_carrier: undefined,
});

const submitting = ref(false);
const errorMessage = ref<string | null>(null);
const showPasteModal = ref(false);

const currencySymbol = computed(() => {
  switch (selectedCurrency.value) {
    case "GBP":
      return "£";
    case "EUR":
      return "€";
    default:
      return "$";
  }
});

const priceInUsd = computed(() => {
  if (!form.value.purchase_price) return 0;
  switch (selectedCurrency.value) {
    case "GBP":
      return form.value.purchase_price * exchangeRates.value.gbp_to_usd_rate;
    case "EUR":
      return form.value.purchase_price * exchangeRates.value.eur_to_usd_rate;
    default:
      return form.value.purchase_price;
  }
});

// Safely convert valueMid to number (API may return string)
const valueMidNumeric = computed(() => {
  if (props.valueMid == null) return null;
  const num = Number(props.valueMid);
  return isNaN(num) ? null : num;
});

const estimatedDiscount = computed(() => {
  if (!valueMidNumeric.value || !priceInUsd.value) return null;
  const discount = ((valueMidNumeric.value - priceInUsd.value) / valueMidNumeric.value) * 100;
  return discount.toFixed(1);
});

async function loadExchangeRates() {
  loadingRates.value = true;
  try {
    const res = await api.get("/admin/config");
    exchangeRates.value = res.data;
  } catch (e) {
    console.error("Failed to load exchange rates:", e);
  } finally {
    loadingRates.value = false;
  }
}

onMounted(() => {
  loadExchangeRates();
});

// Lock body scroll when modal is open
watch(
  () => true, // Modal is always visible when component exists
  () => {
    document.body.style.overflow = "hidden";
  },
  { immediate: true }
);

// Clean up on unmount
onUnmounted(() => {
  document.body.style.overflow = "";
});

async function handleSubmit() {
  if (!form.value.purchase_price || !form.value.order_number) {
    errorMessage.value = "Please fill in all required fields";
    return;
  }

  submitting.value = true;
  errorMessage.value = null;

  try {
    // Convert price to USD before submitting
    const payload = {
      ...form.value,
      purchase_price: priceInUsd.value,
    };
    await acquisitionsStore.acquireBook(props.bookId, payload);
    emit("acquired");
    emit("close");
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to acquire book";
  } finally {
    submitting.value = false;
  }
}

function handleClose() {
  if (!submitting.value) {
    emit("close");
  }
}

function handlePasteApply(data: any) {
  if (data.order_number) {
    form.value.order_number = data.order_number;
  }
  if (data.total_usd) {
    form.value.purchase_price = data.total_usd;
  } else if (data.total) {
    form.value.purchase_price = data.total;
  }
  if (data.purchase_date) {
    form.value.purchase_date = data.purchase_date;
  }
  if (data.estimated_delivery) {
    form.value.estimated_delivery = data.estimated_delivery;
  }
  showPasteModal.value = false;
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="handleClose"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">Acquire Book</h2>
            <p class="text-sm text-gray-600 truncate">{{ bookTitle }}</p>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="showPasteModal = true"
              :disabled="submitting"
              class="text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50 flex items-center gap-1"
              title="Paste order details from email"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
              Paste Order
            </button>
            <button
              @click="handleClose"
              :disabled="submitting"
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
        </div>

        <!-- Form -->
        <form @submit.prevent="handleSubmit" class="p-4 space-y-4">
          <!-- Error Message -->
          <div
            v-if="errorMessage"
            class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm"
          >
            {{ errorMessage }}
          </div>

          <!-- Purchase Price with Currency Selector -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"> Purchase Price * </label>
            <div class="flex gap-2">
              <select
                v-model="selectedCurrency"
                class="w-24 px-2 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="USD">USD $</option>
                <option value="GBP">GBP £</option>
                <option value="EUR">EUR €</option>
              </select>
              <div class="relative flex-1">
                <span class="absolute left-3 top-2 text-gray-500">{{ currencySymbol }}</span>
                <input
                  v-model.number="form.purchase_price"
                  type="number"
                  step="0.01"
                  min="0"
                  class="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
            </div>
            <div
              v-if="selectedCurrency !== 'USD' && form.purchase_price"
              class="mt-1 text-sm text-gray-600"
            >
              ≈ ${{ priceInUsd.toFixed(2) }} USD
              <span class="text-gray-400"
                >(rate:
                {{
                  selectedCurrency === "GBP"
                    ? exchangeRates.gbp_to_usd_rate
                    : exchangeRates.eur_to_usd_rate
                }})</span
              >
            </div>
            <p v-if="estimatedDiscount" class="mt-1 text-sm text-green-600">
              {{ estimatedDiscount }}% discount from FMV (${{ valueMidNumeric?.toFixed(2) }})
            </p>
          </div>

          <!-- Purchase Date -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"> Purchase Date * </label>
            <input
              v-model="form.purchase_date"
              type="date"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <!-- Order Number -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"> Order Number * </label>
            <input
              v-model="form.order_number"
              type="text"
              placeholder="19-13940-40744"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <!-- Platform -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"> Platform * </label>
            <select
              v-model="form.place_of_purchase"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="eBay">eBay</option>
              <option value="Etsy">Etsy</option>
              <option value="AbeBooks">AbeBooks</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <!-- Estimated Delivery -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"> Estimated Delivery </label>
            <input
              v-model="form.estimated_delivery"
              type="date"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Tracking Number (Optional) -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Tracking Number (Optional)
            </label>
            <input
              v-model="form.tracking_number"
              type="text"
              placeholder="e.g., 1Z999AA10123456784"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p class="mt-1 text-xs text-gray-500">
              Carrier will be auto-detected. Add tracking now or later.
            </p>
          </div>

          <!-- Carrier Override (Optional) -->
          <div v-if="form.tracking_number">
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Carrier (Optional Override)
            </label>
            <select
              v-model="form.tracking_carrier"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Auto-detect</option>
              <option value="USPS">USPS</option>
              <option value="UPS">UPS</option>
              <option value="FedEx">FedEx</option>
              <option value="DHL">DHL</option>
              <option value="Royal Mail">Royal Mail</option>
              <option value="Parcelforce">Parcelforce</option>
            </select>
            <p class="mt-1 text-xs text-gray-500">Override if auto-detection fails</p>
          </div>

          <!-- Footer Buttons -->
          <div class="flex gap-3 pt-4">
            <button
              type="button"
              @click="handleClose"
              :disabled="submitting"
              class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="submitting"
              class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ submitting ? "Processing..." : "Confirm Acquire" }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Paste Order Modal -->
    <PasteOrderModal
      v-if="showPasteModal"
      @close="showPasteModal = false"
      @apply="handlePasteApply"
    />
  </Teleport>
</template>

<style scoped></style>
