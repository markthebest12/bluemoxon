<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useAcquisitionsStore, type AcquisitionBook } from "@/stores/acquisitions";
import { useBooksStore } from "@/stores/books";
import { useCurrencyConversion } from "@/composables/useCurrencyConversion";
import TransitionModal from "./TransitionModal.vue";

const props = defineProps<{
  visible: boolean;
  book: AcquisitionBook;
}>();

const emit = defineEmits<{
  close: [];
  updated: [];
}>();

const acquisitionsStore = useAcquisitionsStore();
const booksStore = useBooksStore();

// Currency conversion from composable
const {
  selectedCurrency,
  exchangeRates,
  currencySymbol,
  convertToUsd,
  loadExchangeRates,
} = useCurrencyConversion();

const form = ref({
  value_low: props.book.value_low ?? null,
  value_mid: props.book.value_mid ?? null,
  value_high: props.book.value_high ?? null,
  source_url: props.book.source_url ?? "",
  volumes: props.book.volumes ?? 1,
  is_complete: props.book.is_complete ?? true,
  purchase_price: props.book.purchase_price ?? null,
});

// Computed USD price using composable's conversion
const priceInUsd = computed(() => convertToUsd(form.value.purchase_price) ?? 0);

// Track if price changed for eval runbook refresh
const originalPrice = props.book.purchase_price ?? null;

const submitting = ref(false);
const errorMessage = ref<string | null>(null);

onMounted(() => {
  void loadExchangeRates();
});

async function handleSubmit() {
  submitting.value = true;
  errorMessage.value = null;

  try {
    // Convert price to USD before submitting
    const priceToSubmit = form.value.purchase_price ? priceInUsd.value : undefined;

    const payload = {
      value_low: form.value.value_low ?? undefined,
      value_mid: form.value.value_mid ?? undefined,
      value_high: form.value.value_high ?? undefined,
      source_url: form.value.source_url || undefined,
      volumes: form.value.volumes || 1,
      is_complete: form.value.is_complete,
      purchase_price: priceToSubmit,
    };

    await acquisitionsStore.updateWatchlistItem(props.book.id, payload);

    // If price changed and book has eval runbook, trigger refresh
    // Compare USD values since originalPrice was in USD
    const priceChanged = priceToSubmit !== originalPrice;
    if (priceChanged && props.book.has_eval_runbook) {
      // Trigger async eval runbook regeneration - await so job is registered before emit
      try {
        await booksStore.generateEvalRunbookAsync(props.book.id);
      } catch (e) {
        console.error("Failed to trigger eval runbook refresh:", e);
      }
    }

    emit("updated");
    emit("close");
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to update item";
  } finally {
    submitting.value = false;
  }
}

function handleClose() {
  if (!submitting.value) {
    emit("close");
  }
}

function openSourceUrl() {
  if (form.value.source_url) {
    window.open(form.value.source_url, "_blank");
  }
}
</script>

<template>
  <TransitionModal :visible="visible" @backdrop-click="handleClose">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Edit Watchlist Item</h2>
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

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="p-4 flex flex-col gap-4">
        <!-- Error Message -->
        <div
          v-if="errorMessage"
          class="bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] text-[var(--color-status-error-text)] p-3 rounded-lg text-sm"
        >
          {{ errorMessage }}
        </div>

        <!-- Book Title (readonly) -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Title</label>
          <p class="text-gray-900 font-medium">{{ book.title }}</p>
          <p class="text-sm text-gray-500">{{ book.author?.name || "Unknown author" }}</p>
        </div>

        <!-- Asking Price with Currency Selector -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Asking Price</label>
          <div class="flex gap-2">
            <select v-model="selectedCurrency" class="select w-24">
              <option value="USD">USD $</option>
              <option value="GBP">GBP £</option>
              <option value="EUR">EUR €</option>
            </select>
            <div class="relative flex-1">
              <span class="absolute left-3 top-2.5 text-gray-500">{{ currencySymbol }}</span>
              <input
                v-model.number="form.purchase_price"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                class="input pl-7"
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
          <p class="text-xs text-gray-500 mt-1">
            Changing this will refresh the eval runbook if one exists
          </p>
        </div>

        <!-- FMV Section -->
        <div class="bg-gray-50 p-3 rounded-lg">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Fair Market Value (FMV)
          </label>
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="block text-xs text-gray-500 mb-1">Low</label>
              <div class="relative">
                <span class="absolute left-2 top-2 text-gray-500 text-sm">$</span>
                <input
                  v-model.number="form.value_low"
                  type="number"
                  step="1"
                  min="0"
                  placeholder="0"
                  class="input pl-6 text-sm"
                />
              </div>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Mid</label>
              <div class="relative">
                <span class="absolute left-2 top-2 text-gray-500 text-sm">$</span>
                <input
                  v-model.number="form.value_mid"
                  type="number"
                  step="1"
                  min="0"
                  placeholder="0"
                  class="input pl-6 text-sm"
                />
              </div>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">High</label>
              <div class="relative">
                <span class="absolute left-2 top-2 text-gray-500 text-sm">$</span>
                <input
                  v-model.number="form.value_high"
                  type="number"
                  step="1"
                  min="0"
                  placeholder="0"
                  class="input pl-6 text-sm"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Volumes & Complete Row -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Volumes</label>
            <input v-model.number="form.volumes" type="number" min="1" class="input" />
          </div>
          <div class="flex items-center pt-6">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                v-model="form.is_complete"
                type="checkbox"
                class="w-4 h-4 rounded-sm border-gray-300 text-victorian-hunter-600 focus:ring-victorian-gold-muted"
              />
              <span class="text-sm text-gray-700">Complete set</span>
            </label>
          </div>
        </div>

        <!-- Source URL -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Source URL</label>
          <div class="flex gap-2">
            <input
              v-model="form.source_url"
              type="url"
              placeholder="https://ebay.com/itm/..."
              class="input flex-1"
            />
            <button
              type="button"
              :disabled="!form.source_url"
              @click="openSourceUrl"
              class="btn-secondary px-3"
              title="Open URL"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </button>
          </div>
        </div>

        <!-- Footer Buttons -->
        <div class="flex gap-3 pt-4">
          <button
            type="button"
            @click="handleClose"
            :disabled="submitting"
            class="btn-secondary flex-1"
          >
            Cancel
          </button>
          <button type="submit" :disabled="submitting" class="btn-primary flex-1">
            {{ submitting ? "Saving..." : "Save Changes" }}
          </button>
        </div>
      </form>
    </div>
  </TransitionModal>
</template>
