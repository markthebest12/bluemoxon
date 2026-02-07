<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useReferencesStore } from "@/stores/references";
import { useAcquisitionsStore } from "@/stores/acquisitions";
import { useCurrencyConversion } from "@/composables/useCurrencyConversion";
import { getErrorMessage } from "@/types/errors";
import { BOOK_CATEGORIES } from "@/constants";
import ComboboxWithAdd from "./ComboboxWithAdd.vue";
import TransitionModal from "./TransitionModal.vue";

defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  close: [];
  added: [];
}>();

const refsStore = useReferencesStore();
const acquisitionsStore = useAcquisitionsStore();
const { selectedCurrency, currencySymbol, convertToUsd, loadExchangeRates } =
  useCurrencyConversion();

const form = ref({
  title: "",
  author_id: null as number | null,
  publisher_id: null as number | null,
  binder_id: null as number | null,
  publication_date: "",
  volumes: 1,
  source_url: "",
  purchase_price: null as number | null, // Asking price in selected currency
  category: "" as string,
});

const submitting = ref(false);
const errorMessage = ref<string | null>(null);
const validationErrors = ref<Record<string, string>>({});

const priceInUsd = computed(() => convertToUsd(form.value.purchase_price));

onMounted(() => {
  void refsStore.fetchAll();
  void loadExchangeRates();
});

function validate(): boolean {
  validationErrors.value = {};

  if (!form.value.title.trim()) {
    validationErrors.value.title = "Title is required";
  }
  if (!form.value.author_id) {
    validationErrors.value.author = "Author is required";
  }
  if (!form.value.category) {
    validationErrors.value.category = "Category is required";
  }

  return Object.keys(validationErrors.value).length === 0;
}

async function handleSubmit() {
  if (!validate()) return;

  submitting.value = true;
  errorMessage.value = null;

  try {
    const payload = {
      title: form.value.title.trim(),
      author_id: form.value.author_id!,
      category: form.value.category,
      publisher_id: form.value.publisher_id || undefined,
      binder_id: form.value.binder_id || undefined,
      publication_date: form.value.publication_date || undefined,
      volumes: form.value.volumes || 1,
      source_url: form.value.source_url || undefined,
      purchase_price: priceInUsd.value ?? undefined, // Use ?? to preserve 0, only convert null/undefined
    };

    await acquisitionsStore.addToWatchlist(payload);
    emit("added");
    emit("close");
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : "Failed to add to watchlist";
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

function handleEntityError(err: unknown) {
  errorMessage.value = getErrorMessage(err, "Failed to create entity");
}
</script>

<template>
  <TransitionModal :visible="visible" @backdrop-click="handleClose">
    <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Add to Watchlist</h2>
        <button
          :disabled="submitting"
          class="text-gray-500 hover:text-gray-700 disabled:opacity-50"
          @click="handleClose"
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
      <form class="p-4 flex flex-col gap-4" @submit.prevent="handleSubmit">
        <!-- Error Message -->
        <div
          v-if="errorMessage"
          class="bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] text-[var(--color-status-error-text)] p-3 rounded-lg text-sm"
        >
          {{ errorMessage }}
        </div>

        <!-- Title -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Title <span class="text-[var(--color-status-error-accent)]">*</span>
          </label>
          <input
            v-model="form.title"
            type="text"
            class="input"
            :class="{ 'border-[var(--color-status-error-accent)]': validationErrors.title }"
          />
          <p
            v-if="validationErrors.title"
            class="mt-1 text-sm text-[var(--color-status-error-accent)]"
          >
            {{ validationErrors.title }}
          </p>
        </div>

        <!-- Author & Publisher Row -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <ComboboxWithAdd
              v-model="form.author_id"
              label="Author"
              :options="refsStore.authors"
              :create-fn="refsStore.createAuthor"
              @error="handleEntityError"
            />
            <p
              v-if="validationErrors.author"
              class="mt-1 text-sm text-[var(--color-status-error-accent)]"
            >
              {{ validationErrors.author }}
            </p>
          </div>
          <ComboboxWithAdd
            v-model="form.publisher_id"
            label="Publisher"
            :options="refsStore.publishers"
            :create-fn="refsStore.createPublisher"
            @error="handleEntityError"
          />
        </div>

        <!-- Binder & Publication Date Row -->
        <div class="grid grid-cols-2 gap-4">
          <ComboboxWithAdd
            v-model="form.binder_id"
            label="Binder"
            :options="refsStore.binders"
            :create-fn="refsStore.createBinder"
            @error="handleEntityError"
          />
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"> Publication Date </label>
            <input v-model="form.publication_date" type="text" placeholder="1867" class="input" />
          </div>
        </div>

        <!-- Volumes & Asking Price Row -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"> Volumes </label>
            <input v-model.number="form.volumes" type="number" min="1" class="input" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"> Asking Price </label>
            <div class="flex gap-2">
              <select v-model="selectedCurrency" class="select w-20">
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
                  placeholder="Optional"
                  class="input pl-7"
                />
              </div>
            </div>
            <p
              v-if="form.purchase_price && selectedCurrency !== 'USD'"
              class="mt-1 text-xs text-gray-500"
            >
              ≈ ${{ priceInUsd?.toFixed(2) }} USD
            </p>
          </div>
        </div>

        <!-- Category -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Category <span class="text-[var(--color-status-error-accent)]">*</span>
          </label>
          <select
            v-model="form.category"
            class="input w-full"
            :class="{ 'border-[var(--color-status-error-accent)]': validationErrors.category }"
          >
            <option value="">-- Select Category --</option>
            <option v-for="cat in BOOK_CATEGORIES" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>
          <p
            v-if="validationErrors.category"
            class="mt-1 text-sm text-[var(--color-status-error-accent)]"
          >
            {{ validationErrors.category }}
          </p>
        </div>

        <!-- Source URL -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1"> Source URL </label>
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
              class="btn-secondary px-3"
              title="Open URL"
              @click="openSourceUrl"
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
            :disabled="submitting"
            class="btn-secondary flex-1"
            @click="handleClose"
          >
            Cancel
          </button>
          <button type="submit" :disabled="submitting" class="btn-primary flex-1">
            {{ submitting ? "Adding..." : "Add to List" }}
          </button>
        </div>
      </form>
    </div>
  </TransitionModal>
</template>
