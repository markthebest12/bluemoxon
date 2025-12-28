<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useReferencesStore } from "@/stores/references";
import { useAcquisitionsStore } from "@/stores/acquisitions";
import {
  useListingsStore,
  type ImagePreview,
  type ExtractionStatusResponse,
} from "@/stores/listings";
import ComboboxWithAdd from "./ComboboxWithAdd.vue";

const emit = defineEmits<{
  close: [];
  added: [];
}>();

const refsStore = useReferencesStore();
const acquisitionsStore = useAcquisitionsStore();
const listingsStore = useListingsStore();

// Wizard steps: 'url' | 'extracting' | 'review' | 'saving'
const step = ref<"url" | "extracting" | "review" | "saving">("url");

// URL input
const urlInput = ref("");
const extracting = ref(false);
const extractError = ref<string | null>(null);

// Async extraction tracking
const currentItemId = ref<string | null>(null);
const extractionStatus = ref<ExtractionStatusResponse | null>(null);

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

// Saving progress steps (quick import - AI analysis happens later)
const savingSteps = [
  { id: "create", label: "Creating book record" },
  { id: "images", label: "Copying images to library" },
  { id: "runbook", label: "Generating quick evaluation" },
];
const currentSavingStep = ref(0);
let savingStepInterval: ReturnType<typeof setInterval> | null = null;

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
  // Clean up any active extraction polling
  if (currentItemId.value) {
    listingsStore.clearExtraction(currentItemId.value);
  }
  // Clean up saving step interval
  if (savingStepInterval) {
    clearInterval(savingStepInterval);
    savingStepInterval = null;
  }
});

onMounted(() => {
  refsStore.fetchAll();
});

// Computed: Is the URL a valid eBay URL?
// Accepts both standard ebay.com/itm/... URLs and ebay.us short URLs
const isValidEbayUrl = computed(() => {
  try {
    const url = new URL(urlInput.value);
    const hostname = url.hostname.toLowerCase();

    // Accept ebay.us short URLs (they redirect to full URLs on the backend)
    if (hostname === "ebay.us" || hostname === "www.ebay.us") {
      return url.pathname.length > 1; // Must have some path
    }

    // Standard eBay URLs must have /itm/ pattern
    const isEbayHost =
      hostname === "ebay.com" || hostname === "www.ebay.com" || hostname === "m.ebay.com";
    return isEbayHost && url.pathname.includes("/itm/");
  } catch {
    return false;
  }
});

// Helper: Check if URL is an ebay.us short URL (needs sync extraction)
function isEbayShortUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname.toLowerCase();
    return hostname === "ebay.us" || hostname === "www.ebay.us";
  } catch {
    return false;
  }
}

// Helper: Standardize name (capitalize words properly)
function standardizeName(name: string | undefined): string {
  if (!name) return "";
  return name
    .trim()
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

// Helper: Check if binding suggests custom/fine work (ornate, gilt, leather, morocco)
function isOrnateBinding(bindingType: string | undefined): boolean {
  if (!bindingType) return false;
  const ornateTerms = [
    "morocco",
    "gilt",
    "gilded",
    "gold",
    "tooled",
    "tooling",
    "ornate",
    "decorated",
    "inlaid",
    "jeweled",
    "jewelled",
    "leather",
    "calf",
    "vellum",
    "raised bands",
  ];
  const lower = bindingType.toLowerCase();
  return ornateTerms.some((term) => lower.includes(term));
}

// Computed: Suggested author name (standardized extracted name when no match)
const suggestedAuthorName = computed(() => {
  if (extractedData.value?.matches?.author) return undefined; // Has match, no suggestion needed
  return standardizeName(extractedData.value?.listing_data?.author);
});

// Computed: Suggested publisher name (standardized extracted name when no match)
const suggestedPublisherName = computed(() => {
  if (extractedData.value?.matches?.publisher) return undefined;
  return standardizeName(extractedData.value?.listing_data?.publisher);
});

// Computed: Suggested binder name - extracted name, or "Custom" for ornate bindings
const suggestedBinderName = computed(() => {
  if (extractedData.value?.matches?.binder) return undefined; // Has match
  const extractedBinder = extractedData.value?.listing_data?.binder;
  if (extractedBinder) return standardizeName(extractedBinder);
  // If binding is ornate but no binder identified, suggest "Custom"
  const bindingType = extractedData.value?.listing_data?.binding_type;
  if (isOrnateBinding(bindingType)) return "Custom";
  return undefined;
});

async function handleExtract() {
  if (!isValidEbayUrl.value) {
    extractError.value = "Please enter a valid eBay listing URL";
    return;
  }

  extracting.value = true;
  extractError.value = null;

  try {
    // Short URLs (ebay.us) must use sync extraction - async doesn't support them
    if (isEbayShortUrl(urlInput.value)) {
      step.value = "extracting"; // Show loading state
      const result = await listingsStore.extractListing(urlInput.value);

      // Populate extractedData from sync result
      extractedData.value = {
        listing_data: result.listing_data,
        images: result.images,
        image_urls: result.image_urls,
        matches: result.matches,
        ebay_url: result.ebay_url,
        ebay_item_id: result.ebay_item_id,
      };

      // Populate form with extracted data
      const data = result.listing_data;
      form.value.title = data.title || "";
      form.value.publication_date = data.publication_date || "";
      form.value.volumes = data.volumes || 1;
      form.value.source_url = result.ebay_url;
      form.value.binding_type = data.binding_type || data.binding || "";
      form.value.condition_notes = data.condition_description || data.condition || "";

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

      extracting.value = false;
      step.value = "review";
      return;
    }

    // Standard URLs use async extraction with polling
    const job = await listingsStore.extractListingAsync(urlInput.value);
    currentItemId.value = job.item_id;

    // Transition to extracting step (shows progress)
    step.value = "extracting";
  } catch (e: any) {
    if (e.response?.status === 429) {
      extractError.value = "Rate limited by eBay. Please try again in a few minutes.";
    } else if (e.response?.status === 400) {
      extractError.value = "Invalid eBay URL. Please check the URL and try again.";
    } else {
      extractError.value = e.message || "Failed to start extraction";
    }
    extracting.value = false;
    step.value = "url";
  }
}

// Watch for extraction status changes
watch(
  () => currentItemId.value && listingsStore.activeExtractions.get(currentItemId.value),
  (status) => {
    if (!status) return;

    extractionStatus.value = status;

    if (status.status === "ready" && status.listing_data) {
      // Extraction complete - populate form and go to review
      extractedData.value = {
        listing_data: status.listing_data,
        images: status.images,
        image_urls: [],
        matches: status.matches,
        ebay_url: status.ebay_url || `https://www.ebay.com/itm/${currentItemId.value}`,
        ebay_item_id: currentItemId.value!,
      };

      // Populate form with extracted data
      const data = status.listing_data;
      form.value.title = data.title || "";
      form.value.publication_date = data.publication_date || "";
      form.value.volumes = data.volumes || 1;
      form.value.source_url = status.ebay_url || `https://www.ebay.com/itm/${currentItemId.value}`;
      form.value.binding_type = data.binding_type || data.binding || "";
      form.value.condition_notes = data.condition_description || data.condition || "";

      // Set price
      if (data.price) {
        form.value.purchase_price = data.price;
      }

      // Apply matched references
      if (status.matches.author) {
        form.value.author_id = status.matches.author.id;
      }
      if (status.matches.binder) {
        form.value.binder_id = status.matches.binder.id;
      }
      if (status.matches.publisher) {
        form.value.publisher_id = status.matches.publisher.id;
      }

      extracting.value = false;
      step.value = "review";
    } else if (status.status === "error") {
      extractError.value = status.error || "Extraction failed";
      extracting.value = false;
      step.value = "url";
    }
  },
  { deep: true }
);

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
  currentSavingStep.value = 0;

  // Animate through steps to show progress (since backend is synchronous)
  // Quick import completes in ~5 seconds, so animate faster
  savingStepInterval = setInterval(() => {
    if (currentSavingStep.value < savingSteps.length - 1) {
      currentSavingStep.value++;
    }
  }, 1500); // Move to next step every 1.5 seconds for quick import

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
      purchase_price: form.value.purchase_price ?? undefined,
      binding_type: form.value.binding_type || undefined,
      condition_notes: form.value.condition_notes || undefined,
      // Pass S3 keys so backend can copy images
      listing_s3_keys: extractedData.value?.images?.map((img) => img.s3_key) || [],
    };

    await acquisitionsStore.addToWatchlist(payload);

    // Images are copied by backend during addToWatchlist

    emit("added");
    emit("close");
  } catch (e: any) {
    errorMessage.value = e.message || "Failed to add to watchlist";
    step.value = "review";
  } finally {
    submitting.value = false;
    if (savingStepInterval) {
      clearInterval(savingStepInterval);
      savingStepInterval = null;
    }
  }
}

function handleClose() {
  if (!extracting.value && !submitting.value) {
    emit("close");
  }
}

function goBack() {
  // Clean up any active extraction polling
  if (currentItemId.value) {
    listingsStore.clearExtraction(currentItemId.value);
    currentItemId.value = null;
  }
  extractionStatus.value = null;
  extracting.value = false;
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
                : step === "extracting"
                  ? "Extracting Listing..."
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
        <div v-if="step === 'url'" class="p-4 flex flex-col gap-4">
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
              placeholder="https://www.ebay.com/itm/... or https://ebay.us/..."
              class="input"
              :class="{ 'border-red-500': extractError }"
              @keyup.enter="handleExtract"
            />
            <p class="mt-1 text-sm text-gray-500">
              Paste an eBay listing URL (including short URLs like ebay.us/xxx)
            </p>
          </div>

          <div class="flex gap-3">
            <button
              type="button"
              @click="handleClose"
              :disabled="extracting"
              class="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="button"
              @click="handleExtract"
              :disabled="extracting || !urlInput"
              class="btn-primary flex-1"
            >
              {{ extracting ? "Extracting..." : "Extract Details" }}
            </button>
          </div>
        </div>

        <!-- Step 2: Extracting (async progress) -->
        <div v-if="step === 'extracting'" class="p-8 text-center">
          <div class="spinner spinner-xl mx-auto mb-4"></div>
          <p class="text-gray-600 mb-2">
            {{
              extractionStatus?.status === "pending"
                ? "Scraping eBay listing..."
                : extractionStatus?.status === "scraped"
                  ? "Extracting book details..."
                  : "Processing..."
            }}
          </p>
          <p class="text-sm text-gray-500">This may take up to 2 minutes. Please wait.</p>
          <button @click="goBack" class="mt-4 px-4 py-2 text-gray-600 hover:text-gray-800">
            Cancel
          </button>
        </div>

        <!-- Step 3: Review & Edit -->
        <div v-if="step === 'review'" class="p-4 flex flex-col gap-4">
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
          <form @submit.prevent="handleSubmit" class="flex flex-col gap-4">
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
                  :suggested-name="suggestedAuthorName"
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
                <p
                  v-else-if="extractedData?.listing_data?.author"
                  class="mt-1 text-xs text-amber-600"
                >
                  Extracted: "{{ extractedData.listing_data.author }}" (no match found - create
                  new?)
                </p>
              </div>
              <div>
                <ComboboxWithAdd
                  label="Publisher"
                  :options="refsStore.publishers"
                  v-model="form.publisher_id"
                  :suggested-name="suggestedPublisherName"
                  @create="handleCreatePublisher"
                />
                <p v-if="extractedData?.matches?.publisher" class="mt-1 text-xs text-green-600">
                  Matched: {{ extractedData.matches.publisher.name }}
                </p>
                <p
                  v-else-if="extractedData?.listing_data?.publisher"
                  class="mt-1 text-xs text-amber-600"
                >
                  Extracted: "{{ extractedData.listing_data.publisher }}" (no match)
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
                  :suggested-name="suggestedBinderName"
                  @create="handleCreateBinder"
                />
                <p v-if="extractedData?.matches?.binder" class="mt-1 text-xs text-green-600">
                  Matched: {{ extractedData.matches.binder.name }}
                </p>
                <p
                  v-else-if="extractedData?.listing_data?.binder"
                  class="mt-1 text-xs text-amber-600"
                >
                  Extracted: "{{ extractedData.listing_data.binder }}" (no match)
                </p>
                <p v-else-if="suggestedBinderName === 'Custom'" class="mt-1 text-xs text-amber-600">
                  Ornate binding detected - suggested "Custom" binder
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
                  class="input"
                />
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
                <div class="relative">
                  <span class="absolute left-3 top-2 text-gray-500">$</span>
                  <input
                    v-model.number="form.purchase_price"
                    type="number"
                    step="0.01"
                    min="0"
                    class="input pl-7"
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
                  class="input"
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
                  class="input"
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
                  class="input flex-1 bg-gray-50 text-gray-600"
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
              <button type="button" @click="goBack" :disabled="submitting" class="btn-secondary">
                Back
              </button>
              <button
                type="button"
                @click="handleClose"
                :disabled="submitting"
                class="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button type="submit" :disabled="submitting" class="btn-primary flex-1">
                {{ submitting ? "Adding..." : "Add to Watchlist" }}
              </button>
            </div>
          </form>
        </div>

        <!-- Step 4: Saving with progress steps -->
        <div v-if="step === 'saving'" class="p-6">
          <div class="flex items-center justify-center mb-6">
            <div class="spinner spinner-lg"></div>
          </div>
          <p class="text-center text-gray-600 mb-6">Saving to watchlist...</p>

          <!-- Progress steps -->
          <div class="flex flex-col gap-3 max-w-sm mx-auto">
            <div
              v-for="(stepItem, index) in savingSteps"
              :key="stepItem.id"
              class="flex items-center gap-3"
            >
              <!-- Step indicator -->
              <div class="shrink-0 w-6 h-6 flex items-center justify-center">
                <svg
                  v-if="index < currentSavingStep"
                  class="w-5 h-5 text-green-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clip-rule="evenodd"
                  />
                </svg>
                <div v-else-if="index === currentSavingStep" class="spinner w-4 h-4"></div>
                <div v-else class="w-3 h-3 rounded-full bg-gray-300"></div>
              </div>
              <!-- Step label -->
              <span
                :class="[
                  'text-sm',
                  index < currentSavingStep
                    ? 'text-green-600'
                    : index === currentSavingStep
                      ? 'text-victorian-hunter-600 font-medium'
                      : 'text-gray-400',
                ]"
              >
                {{ stepItem.label }}
              </span>
            </div>
          </div>

          <p class="text-center text-xs text-gray-400 mt-6">
            This should only take a few seconds...
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>
