<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useReferencesStore } from "@/stores/references";
import { useAcquisitionsStore } from "@/stores/acquisitions";
import { api } from "@/services/api";
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

// Currency support
type Currency = "USD" | "GBP" | "EUR";
const selectedCurrency = ref<Currency>("USD");
const exchangeRates = ref({ gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 });

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
  if (!form.value.purchase_price) return null;
  switch (selectedCurrency.value) {
    case "GBP":
      return (
        Math.round(form.value.purchase_price * exchangeRates.value.gbp_to_usd_rate * 100) / 100
      );
    case "EUR":
      return (
        Math.round(form.value.purchase_price * exchangeRates.value.eur_to_usd_rate * 100) / 100
      );
    default:
      return form.value.purchase_price;
  }
});

const form = ref({
  title: "",
  author_id: null as number | null,
  publisher_id: null as number | null,
  binder_id: null as number | null,
  publication_date: "",
  volumes: 1,
  source_url: "",
  purchase_price: null as number | null, // Asking price in selected currency
});

const submitting = ref(false);
const errorMessage = ref<string | null>(null);
const validationErrors = ref<Record<string, string>>({});

async function loadExchangeRates() {
  try {
    const res = await api.get("/admin/config");
    exchangeRates.value = res.data;
  } catch (e) {
    console.error("Failed to load exchange rates:", e);
  }
}

onMounted(() => {
  refsStore.fetchAll();
  loadExchangeRates();
});

function validate(): boolean {
  validationErrors.value = {};

  if (!form.value.title.trim()) {
    validationErrors.value.title = "Title is required";
  }
  if (!form.value.author_id) {
    validationErrors.value.author = "Author is required";
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
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to add to watchlist";
  } finally {
    submitting.value = false;
  }
}

function handleClose() {
  if (!submitting.value) {
    emit("close");
  }
}

async function handleCreateAuthor(name: string) {
  try {
    const author = await refsStore.createAuthor(name);
    form.value.author_id = author.id;
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to create author";
  }
}

async function handleCreatePublisher(name: string) {
  try {
    const publisher = await refsStore.createPublisher(name);
    form.value.publisher_id = publisher.id;
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to create publisher";
  }
}

async function handleCreateBinder(name: string) {
  try {
    const binder = await refsStore.createBinder(name);
    form.value.binder_id = binder.id;
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to create binder";
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
    <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">Add to Watchlist</h2>
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
            class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm"
          >
            {{ errorMessage }}
          </div>

          <!-- Title -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Title <span class="text-red-500">*</span>
            </label>
            <input
              v-model="form.title"
              type="text"
              class="input"
              :class="{ 'border-red-500': validationErrors.title }"
            />
            <p v-if="validationErrors.title" class="mt-1 text-sm text-red-500">
              {{ validationErrors.title }}
            </p>
          </div>

          <!-- Author & Publisher Row -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <ComboboxWithAdd
                label="Author"
                :options="refsStore.authors"
                v-model="form.author_id"
                @create="handleCreateAuthor"
              />
              <p v-if="validationErrors.author" class="mt-1 text-sm text-red-500">
                {{ validationErrors.author }}
              </p>
            </div>
            <ComboboxWithAdd
              label="Publisher"
              :options="refsStore.publishers"
              v-model="form.publisher_id"
              @create="handleCreatePublisher"
            />
          </div>

          <!-- Binder & Publication Date Row -->
          <div class="grid grid-cols-2 gap-4">
            <ComboboxWithAdd
              label="Binder"
              :options="refsStore.binders"
              v-model="form.binder_id"
              @create="handleCreateBinder"
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
              {{ submitting ? "Adding..." : "Add to List" }}
            </button>
          </div>
        </form>
      </div>
  </TransitionModal>
</template>
