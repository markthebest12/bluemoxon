<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useReferencesStore } from "@/stores/references";
import { useAcquisitionsStore } from "@/stores/acquisitions";
import { useListingsStore, type ImagePreview } from "@/stores/listings";
import { api } from "@/services/api";
import ComboboxWithAdd from "./ComboboxWithAdd.vue";

const emit = defineEmits<{
  close: [];
  added: [];
}>();

const refsStore = useReferencesStore();
const acquisitionsStore = useAcquisitionsStore();
const listingsStore = useListingsStore();

// Wizard steps: 'url' | 'review' | 'saving'
const step = ref<"url" | "review" | "saving">("url");

// URL input
const urlInput = ref("");
const extracting = ref(false);
const extractError = ref<string | null>(null);

// Extracted data (using new S3-based image format)
const extractedData = ref<{
  listing_data: Record<string, any>;
  images: ImagePreview[];
  image_urls: string[];
  matches: Record<string, { id: number; name: string; similarity: number }>;
  ebay_url: string;
  ebay_item_id: string;
} | null>(null);

// Form for editing
const form = ref({
  title: "",
  author_id: null as number | null,
  publisher_id: null as number | null,
  binder_id: null as number | null,
  publication_date: "",
  volumes: 1,
  source_url: "",
  purchase_price: null as number | null,
  binding_type: "",
  condition_notes: "",
});

const submitting = ref(false);
const errorMessage = ref<string | null>(null);
const validationErrors = ref<Record<string, string>>({});

// Image upload progress
const uploadingImages = ref(false);
const imageUploadProgress = ref({ current: 0, total: 0 });

// Copy images from listings/ to books/ path in S3
async function copyImagesToBook(bookId: number) {
  const images = extractedData.value?.images || [];
  if (images.length === 0) return;

  uploadingImages.value = true;
  imageUploadProgress.value = { current: 0, total: images.length };

  for (let i = 0; i < images.length; i++) {
    const img = images[i];
    try {
      // Copy from listings/{item_id}/ to books/{book_id}/
      // The backend handles the S3 copy operation
      await api.post(`/books/${bookId}/images/copy-from-listing`, {
        s3_key: img.s3_key,
      });

      imageUploadProgress.value.current = i + 1;
    } catch (e) {
      console.error(`Failed to copy image ${i + 1}:`, e);
      // Continue with other images even if one fails
    }
  }

  uploadingImages.value = false;
}

// Lock body scroll when modal is open
watch(
  () => true,
  () => {
    document.body.style.overflow = "hidden";
  },
  { immediate: true }
);

onUnmounted(() => {
  document.body.style.overflow = "";
});

onMounted(() => {
  refsStore.fetchAll();
});

// Computed: Is the URL a valid eBay URL?
const isValidEbayUrl = computed(() => {
  try {
    const url = new URL(urlInput.value);
    return url.hostname.includes("ebay.com") && url.pathname.includes("/itm/");
  } catch {
    return false;
  }
});

async function handleExtract() {
  if (!isValidEbayUrl.value) {
    extractError.value = "Please enter a valid eBay listing URL";
    return;
  }

  extracting.value = true;
  extractError.value = null;

  try {
    const result = await listingsStore.extractListing(urlInput.value);
    extractedData.value = result;

    // Populate form with extracted data
    const data = result.listing_data;
    form.value.title = data.title || "";
    form.value.publication_date = data.publication_date || "";
    form.value.volumes = data.volumes || 1;
    form.value.source_url = result.ebay_url;
    form.value.binding_type = data.binding_type || data.binding || "";
    form.value.condition_notes = data.condition_description || "";

    // Set price
    if (data.price) {
      form.value.purchase_price = data.price;
    }

    // Apply matched references
    if (result.matches.author) {
      form.value.author_id = result.matches.author.id;
    }
    if (result.matches.binder) {
      form.value.binder_id = result.matches.binder.id;
    }
    if (result.matches.publisher) {
      form.value.publisher_id = result.matches.publisher.id;
    }

    step.value = "review";
  } catch (e: any) {
    if (e.response?.status === 429) {
      extractError.value = "Rate limited by eBay. Please try again in a few minutes.";
    } else if (e.response?.status === 502) {
      extractError.value = "Failed to scrape listing. The page may have changed.";
    } else {
      extractError.value = e.message || "Failed to extract listing data";
    }
  } finally {
    extracting.value = false;
  }
}

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
  step.value = "saving";

  try {
    const payload = {
      title: form.value.title.trim(),
      author_id: form.value.author_id!,
      publisher_id: form.value.publisher_id || undefined,
      binder_id: form.value.binder_id || undefined,
      publication_date: form.value.publication_date || undefined,
      volumes: form.value.volumes || 1,
      source_url: form.value.source_url || undefined,
      source_item_id: extractedData.value?.ebay_item_id,
      purchase_price: form.value.purchase_price || undefined,
      binding_type: form.value.binding_type || undefined,
      condition_notes: form.value.condition_notes || undefined,
      // Pass S3 keys so backend can copy images
      listing_s3_keys: extractedData.value?.images?.map((img) => img.s3_key) || [],
    };

    const book = await acquisitionsStore.addToWatchlist(payload);

    // Images are now copied by backend during addToWatchlist
    // No need for separate copy step

    emit("added");
    emit("close");
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to add to watchlist";
    step.value = "review";
  } finally {
    submitting.value = false;
  }
}

function handleClose() {
  if (!extracting.value && !submitting.value) {
    emit("close");
  }
}

function goBack() {
  step.value = "url";
  extractedData.value = null;
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
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="handleClose"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">
            {{
              step === "url"
                ? "Import from eBay"
                : step === "review"
                  ? "Review Listing"
                  : "Saving..."
            }}
          </h2>
          <button
            @click="handleClose"
            :disabled="extracting || submitting"
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

        <!-- Step 1: URL Input -->
        <div v-if="step === 'url'" class="p-4 space-y-4">
          <div
            v-if="extractError"
            class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm"
          >
            {{ extractError }}
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1"> eBay Listing URL </label>
            <input
              v-model="urlInput"
              type="url"
              placeholder="https://www.ebay.com/itm/..."
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :class="{ 'border-red-500': extractError }"
              @keyup.enter="handleExtract"
            />
            <p class="mt-1 text-sm text-gray-500">
              Paste an eBay listing URL to automatically extract book details
            </p>
          </div>

          <div class="flex gap-3">
            <button
              type="button"
              @click="handleClose"
              :disabled="extracting"
              class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              @click="handleExtract"
              :disabled="extracting || !urlInput"
              class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ extracting ? "Extracting..." : "Extract Details" }}
            </button>
          </div>
        </div>

        <!-- Step 2: Review & Edit -->
        <div v-if="step === 'review'" class="p-4 space-y-4">
          <!-- Image Preview (using presigned URLs from S3) -->
          <div v-if="extractedData?.images?.length" class="flex gap-2 overflow-x-auto pb-2">
            <img
              v-for="(img, idx) in extractedData.images.slice(0, 4)"
              :key="idx"
              :src="img.presigned_url"
              class="w-24 h-24 object-cover rounded-lg border border-gray-200"
              :alt="`Image ${idx + 1}`"
            />
            <div
              v-if="extractedData.images.length > 4"
              class="w-24 h-24 flex items-center justify-center bg-gray-100 rounded-lg border border-gray-200 text-gray-500 text-sm"
            >
              +{{ extractedData.images.length - 4 }} more
            </div>
          </div>

          <!-- Error Message -->
          <div
            v-if="errorMessage"
            class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm"
          >
            {{ errorMessage }}
          </div>

          <!-- Form -->
          <form @submit.prevent="handleSubmit" class="space-y-4">
            <!-- Title -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Title <span class="text-red-500">*</span>
              </label>
              <input
                v-model="form.title"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                <p v-if="extractedData?.matches?.author" class="mt-1 text-xs text-green-600">
                  Matched: {{ extractedData.matches.author.name }} ({{
                    Math.round(extractedData.matches.author.similarity * 100)
                  }}%)
                </p>
              </div>
              <div>
                <ComboboxWithAdd
                  label="Publisher"
                  :options="refsStore.publishers"
                  v-model="form.publisher_id"
                  @create="handleCreatePublisher"
                />
                <p v-if="extractedData?.matches?.publisher" class="mt-1 text-xs text-green-600">
                  Matched: {{ extractedData.matches.publisher.name }}
                </p>
              </div>
            </div>

            <!-- Binder & Publication Date Row -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <ComboboxWithAdd
                  label="Binder"
                  :options="refsStore.binders"
                  v-model="form.binder_id"
                  @create="handleCreateBinder"
                />
                <p v-if="extractedData?.matches?.binder" class="mt-1 text-xs text-green-600">
                  Matched: {{ extractedData.matches.binder.name }}
                </p>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Publication Date
                </label>
                <input
                  v-model="form.publication_date"
                  type="text"
                  placeholder="1867"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <!-- Volumes & Asking Price Row -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1"> Volumes </label>
                <input
                  v-model.number="form.volumes"
                  type="number"
                  min="1"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1"> Asking Price </label>
                <div class="relative">
                  <span class="absolute left-3 top-2 text-gray-500">$</span>
                  <input
                    v-model.number="form.purchase_price"
                    type="number"
                    step="0.01"
                    min="0"
                    class="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>

            <!-- Binding Type & Condition -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1"> Binding Type </label>
                <input
                  v-model="form.binding_type"
                  type="text"
                  placeholder="Full morocco, half calf, etc."
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Condition Notes
                </label>
                <input
                  v-model="form.condition_notes"
                  type="text"
                  placeholder="Fine, minor foxing, etc."
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <!-- Source URL (read-only with link) -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1"> Source URL </label>
              <div class="flex gap-2">
                <input
                  v-model="form.source_url"
                  type="url"
                  readonly
                  class="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
                />
                <button
                  type="button"
                  :disabled="!form.source_url"
                  @click="openSourceUrl"
                  class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
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
                @click="goBack"
                :disabled="submitting"
                class="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Back
              </button>
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
                {{ submitting ? "Adding..." : "Add to Watchlist" }}
              </button>
            </div>
          </form>
        </div>

        <!-- Step 3: Saving -->
        <div v-if="step === 'saving'" class="p-8 text-center">
          <div
            class="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mx-auto mb-4"
          ></div>
          <p class="text-gray-600">Saving to watchlist...</p>
        </div>
      </div>
    </div>
  </Teleport>
</template>
