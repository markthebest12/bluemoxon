<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { useBooksStore, type Book } from "@/stores/books";
import { useReferencesStore } from "@/stores/references";
import { api } from "@/services/api";

const props = defineProps<{
  bookId?: number;
}>();

const router = useRouter();
const booksStore = useBooksStore();
const refsStore = useReferencesStore();

// Currency conversion for acquisition fields
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

const purchasePriceInUsd = computed(() => {
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

const acquisitionCostInUsd = computed(() => {
  if (!form.value.acquisition_cost) return 0;
  switch (selectedCurrency.value) {
    case "GBP":
      return form.value.acquisition_cost * exchangeRates.value.gbp_to_usd_rate;
    case "EUR":
      return form.value.acquisition_cost * exchangeRates.value.eur_to_usd_rate;
    default:
      return form.value.acquisition_cost;
  }
});

async function loadExchangeRates() {
  try {
    const res = await api.get("/admin/config");
    exchangeRates.value = res.data;
  } catch (e) {
    console.error("Failed to load exchange rates:", e);
  }
}

const isEditing = computed(() => !!props.bookId);

// Form data
const form = ref({
  title: "",
  author_id: null as number | null,
  publisher_id: null as number | null,
  binder_id: null as number | null,
  publication_date: "",
  edition: "",
  volumes: 1,
  category: "",
  inventory_type: "PRIMARY",
  binding_type: "",
  binding_description: "",
  condition_grade: "",
  condition_notes: "",
  value_low: null as number | null,
  value_mid: null as number | null,
  value_high: null as number | null,
  purchase_price: null as number | null,
  acquisition_cost: null as number | null,
  purchase_date: "",
  purchase_source: "",
  status: "ON_HAND",
  notes: "",
  provenance: "",
});

const saving = ref(false);
const errorMessage = ref("");

// Duplicate detection
interface DuplicateMatch {
  id: number;
  title: string;
  author_name: string | null;
  status: string;
  similarity_score: number;
}
const showDuplicateWarning = ref(false);
const duplicateMatches = ref<DuplicateMatch[]>([]);
const skipDuplicateCheck = ref(false);

// Category options
const categories = [
  "Victorian Poetry",
  "Victorian Literature",
  "Victorian Biography",
  "Romantic Poetry",
  "Romantic Literature",
  "Reference",
  "History",
  "Education",
  "Literature",
];

// Status options
const statuses = ["ON_HAND", "IN_TRANSIT", "SOLD", "REMOVED"];

onMounted(async () => {
  // Fetch reference data for dropdowns and exchange rates
  await Promise.all([refsStore.fetchAll(), loadExchangeRates()]);

  // If editing, load the book data
  if (props.bookId) {
    await booksStore.fetchBook(props.bookId);
    if (booksStore.currentBook) {
      populateForm(booksStore.currentBook);
    }
  }
});

function populateForm(book: Book) {
  form.value = {
    title: book.title || "",
    author_id: book.author?.id || null,
    publisher_id: book.publisher?.id || null,
    binder_id: book.binder?.id || null,
    publication_date: book.publication_date || "",
    edition: (book as any).edition || "",
    volumes: book.volumes || 1,
    category: book.category || "",
    inventory_type: book.inventory_type || "PRIMARY",
    binding_type: book.binding_type || "",
    binding_description: (book as any).binding_description || "",
    condition_grade: (book as any).condition_grade || "",
    condition_notes: (book as any).condition_notes || "",
    value_low: book.value_low,
    value_mid: book.value_mid,
    value_high: book.value_high,
    purchase_price: (book as any).purchase_price || null,
    acquisition_cost: (book as any).acquisition_cost || null,
    purchase_date: (book as any).purchase_date || "",
    purchase_source: (book as any).purchase_source || "",
    status: book.status || "ON_HAND",
    notes: book.notes || "",
    provenance: (book as any).provenance || "",
  };
}

function prepareFormData() {
  // Prepare data - only include non-empty values
  const data: any = {
    title: form.value.title,
    volumes: form.value.volumes,
    inventory_type: form.value.inventory_type,
    status: form.value.status,
  };

  // Optional fields
  if (form.value.author_id) data.author_id = form.value.author_id;
  if (form.value.publisher_id) data.publisher_id = form.value.publisher_id;
  if (form.value.binder_id) data.binder_id = form.value.binder_id;
  if (form.value.publication_date) data.publication_date = form.value.publication_date;
  if (form.value.edition) data.edition = form.value.edition;
  if (form.value.category) data.category = form.value.category;
  if (form.value.binding_type) data.binding_type = form.value.binding_type;
  if (form.value.binding_description) data.binding_description = form.value.binding_description;
  if (form.value.condition_grade) data.condition_grade = form.value.condition_grade;
  if (form.value.condition_notes) data.condition_notes = form.value.condition_notes;
  if (form.value.value_low !== null) data.value_low = form.value.value_low;
  if (form.value.value_mid !== null) data.value_mid = form.value.value_mid;
  if (form.value.value_high !== null) data.value_high = form.value.value_high;
  // Convert acquisition prices to USD before saving
  if (form.value.purchase_price !== null) data.purchase_price = purchasePriceInUsd.value;
  if (form.value.acquisition_cost !== null) data.acquisition_cost = acquisitionCostInUsd.value;
  if (form.value.purchase_date) data.purchase_date = form.value.purchase_date;
  if (form.value.purchase_source) data.purchase_source = form.value.purchase_source;
  if (form.value.notes) data.notes = form.value.notes;
  if (form.value.provenance) data.provenance = form.value.provenance;

  return data;
}

async function handleSubmit() {
  saving.value = true;
  errorMessage.value = "";

  try {
    const data = prepareFormData();

    // Check for duplicates when creating new books (not editing)
    if (!isEditing.value && !skipDuplicateCheck.value) {
      const duplicateCheck = await booksStore.checkDuplicate(
        form.value.title,
        form.value.author_id
      );
      if (duplicateCheck.has_duplicates) {
        duplicateMatches.value = duplicateCheck.matches;
        showDuplicateWarning.value = true;
        saving.value = false;
        return;
      }
    }

    let result;
    if (isEditing.value && props.bookId) {
      result = await booksStore.updateBook(props.bookId, data);
    } else {
      result = await booksStore.createBook(data);
    }

    // Navigate to the book detail page
    router.push(`/books/${result.id}`);
  } catch (e: any) {
    errorMessage.value = e.response?.data?.detail || e.message || "Failed to save book";
  } finally {
    saving.value = false;
    skipDuplicateCheck.value = false;
  }
}

function confirmCreateDuplicate() {
  showDuplicateWarning.value = false;
  skipDuplicateCheck.value = true;
  handleSubmit();
}

function cancelDuplicateWarning() {
  showDuplicateWarning.value = false;
  duplicateMatches.value = [];
}

function cancel() {
  if (props.bookId) {
    router.push(`/books/${props.bookId}`);
  } else {
    router.push("/books");
  }
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="max-w-4xl mx-auto space-y-8">
    <!-- Error message -->
    <div v-if="errorMessage" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
      {{ errorMessage }}
    </div>

    <!-- Basic Information -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Basic Information</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Title *</label>
          <input
            v-model="form.title"
            type="text"
            required
            class="input w-full"
            placeholder="Book title"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Author</label>
          <select v-model="form.author_id" class="input w-full">
            <option :value="null">-- Select Author --</option>
            <option v-for="author in refsStore.authors" :key="author.id" :value="author.id">
              {{ author.name }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Publisher</label>
          <select v-model="form.publisher_id" class="input w-full">
            <option :value="null">-- Select Publisher --</option>
            <option v-for="pub in refsStore.publishers" :key="pub.id" :value="pub.id">
              {{ pub.name }}
              <template v-if="pub.tier"> ({{ pub.tier }})</template>
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Publication Date</label>
          <input
            v-model="form.publication_date"
            type="text"
            class="input w-full"
            placeholder="e.g., 1867-1880 or 1851"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Edition</label>
          <input
            v-model="form.edition"
            type="text"
            class="input w-full"
            placeholder="e.g., First Edition"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Volumes</label>
          <input v-model.number="form.volumes" type="number" min="1" class="input w-full" />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Category</label>
          <select v-model="form.category" class="input w-full">
            <option value="">-- Select Category --</option>
            <option v-for="cat in categories" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Inventory Type</label>
          <select v-model="form.inventory_type" class="input w-full">
            <option value="PRIMARY">Primary Collection</option>
            <option value="EXTENDED">Extended Inventory</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select v-model="form.status" class="input w-full">
            <option v-for="status in statuses" :key="status" :value="status">
              {{ status.replace("_", " ") }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Binding Information -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Binding</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Premium Binder
            <span class="text-victorian-burgundy">(Authenticated)</span>
          </label>
          <select v-model="form.binder_id" class="input w-full">
            <option :value="null">-- No Premium Binding --</option>
            <option v-for="binder in refsStore.binders" :key="binder.id" :value="binder.id">
              {{ binder.name }}
              <template v-if="binder.full_name"> - {{ binder.full_name }}</template>
            </option>
          </select>
          <p class="text-xs text-gray-500 mt-1">
            Selecting a binder automatically marks this as an authenticated binding
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Binding Type</label>
          <input
            v-model="form.binding_type"
            type="text"
            class="input w-full"
            placeholder="e.g., Full morocco, Half calf"
          />
        </div>

        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Binding Description</label>
          <textarea
            v-model="form.binding_description"
            rows="2"
            class="input w-full"
            placeholder="Detailed binding description..."
          />
        </div>
      </div>
    </div>

    <!-- Condition -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Condition</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Condition Grade</label>
          <input
            v-model="form.condition_grade"
            type="text"
            class="input w-full"
            placeholder="e.g., Very Good, Good, Fair"
          />
        </div>

        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Condition Notes</label>
          <textarea
            v-model="form.condition_notes"
            rows="2"
            class="input w-full"
            placeholder="Details about condition..."
          />
        </div>
      </div>
    </div>

    <!-- Valuation -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Valuation</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Value Low ($)</label>
          <input
            v-model.number="form.value_low"
            type="number"
            step="0.01"
            min="0"
            class="input w-full"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Value Mid ($)</label>
          <input
            v-model.number="form.value_mid"
            type="number"
            step="0.01"
            min="0"
            class="input w-full"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Value High ($)</label>
          <input
            v-model.number="form.value_high"
            type="number"
            step="0.01"
            min="0"
            class="input w-full"
          />
        </div>
      </div>
    </div>

    <!-- Acquisition -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-800">Acquisition</h2>
        <div class="flex items-center gap-2">
          <label class="text-sm text-gray-600">Currency:</label>
          <select
            v-model="selectedCurrency"
            class="px-2 py-1 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="USD">USD $</option>
            <option value="GBP">GBP £</option>
            <option value="EUR">EUR €</option>
          </select>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1"
            >Purchase Price ({{ currencySymbol }})</label
          >
          <div class="relative">
            <span class="absolute left-3 top-2 text-gray-500">{{ currencySymbol }}</span>
            <input
              v-model.number="form.purchase_price"
              type="number"
              step="0.01"
              min="0"
              class="input w-full pl-7"
            />
          </div>
          <p class="text-xs text-gray-500 mt-1">Listing price only</p>
          <p
            v-if="selectedCurrency !== 'USD' && form.purchase_price"
            class="text-xs text-blue-600 mt-1"
          >
            ≈ ${{ purchasePriceInUsd.toFixed(2) }} USD
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1"
            >Acquisition Cost ({{ currencySymbol }})</label
          >
          <div class="relative">
            <span class="absolute left-3 top-2 text-gray-500">{{ currencySymbol }}</span>
            <input
              v-model.number="form.acquisition_cost"
              type="number"
              step="0.01"
              min="0"
              class="input w-full pl-7"
            />
          </div>
          <p class="text-xs text-gray-500 mt-1">Total incl. shipping & tax</p>
          <p
            v-if="selectedCurrency !== 'USD' && form.acquisition_cost"
            class="text-xs text-blue-600 mt-1"
          >
            ≈ ${{ acquisitionCostInUsd.toFixed(2) }} USD
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Purchase Date</label>
          <input v-model="form.purchase_date" type="date" class="input w-full" />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Purchase Source</label>
          <input
            v-model="form.purchase_source"
            type="text"
            class="input w-full"
            placeholder="e.g., eBay, AbeBooks"
          />
        </div>
      </div>
    </div>

    <!-- Notes -->
    <div class="card">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">Notes</h2>
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea
            v-model="form.notes"
            rows="4"
            class="input w-full"
            placeholder="General notes about this book..."
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Provenance</label>
          <textarea
            v-model="form.provenance"
            rows="2"
            class="input w-full"
            placeholder="Ownership history, bookplates, inscriptions..."
          />
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex justify-end space-x-4">
      <button type="button" @click="cancel" class="btn-secondary">Cancel</button>
      <button type="submit" :disabled="saving" class="btn-primary">
        {{ saving ? "Saving..." : isEditing ? "Update Book" : "Create Book" }}
      </button>
    </div>

    <!-- Duplicate Warning Dialog -->
    <Teleport to="body">
      <div
        v-if="showDuplicateWarning"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="cancelDuplicateWarning"
      >
        <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
          <div class="p-4 border-b border-gray-200">
            <h3 class="text-lg font-semibold text-amber-600 flex items-center gap-2">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clip-rule="evenodd"
                />
              </svg>
              Potential Duplicate Found
            </h3>
          </div>
          <div class="p-4">
            <p class="text-gray-700 mb-4">
              Similar books already exist in your collection. Are you sure you want to create
              another entry?
            </p>
            <div class="space-y-2 max-h-48 overflow-y-auto">
              <div
                v-for="match in duplicateMatches"
                :key="match.id"
                class="p-3 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div class="font-medium text-gray-900">{{ match.title }}</div>
                <div class="text-sm text-gray-600 flex gap-4">
                  <span v-if="match.author_name">{{ match.author_name }}</span>
                  <span
                    class="px-2 py-0.5 text-xs rounded"
                    :class="{
                      'bg-green-100 text-green-800': match.status === 'ON_HAND',
                      'bg-blue-100 text-blue-800': match.status === 'IN_TRANSIT',
                      'bg-yellow-100 text-yellow-800': match.status === 'EVALUATING',
                      'bg-gray-100 text-gray-800': match.status === 'SOLD',
                    }"
                  >
                    {{ match.status }}
                  </span>
                  <span class="text-gray-400"
                    >{{ Math.round(match.similarity_score * 100) }}% match</span
                  >
                </div>
              </div>
            </div>
          </div>
          <div class="p-4 border-t border-gray-200 flex gap-3 justify-end">
            <button
              type="button"
              @click="cancelDuplicateWarning"
              class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="button"
              @click="confirmCreateDuplicate"
              class="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700"
            >
              Create Anyway
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </form>
</template>
