<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useBooksStore } from "@/stores/books";
import { useAuthStore } from "@/stores/auth";
import { api } from "@/services/api";
import BookThumbnail from "@/components/books/BookThumbnail.vue";
import ImageCarousel from "@/components/books/ImageCarousel.vue";
import ImageReorderModal from "@/components/books/ImageReorderModal.vue";
import ImageUploadModal from "@/components/books/ImageUploadModal.vue";
import AnalysisViewer from "@/components/books/AnalysisViewer.vue";
import EvalRunbookModal from "@/components/books/EvalRunbookModal.vue";
import ArchiveStatusBadge from "@/components/ArchiveStatusBadge.vue";

const route = useRoute();
const router = useRouter();
const booksStore = useBooksStore();
const authStore = useAuthStore();

// Image gallery state
const images = ref<any[]>([]);
const carouselVisible = ref(false);
const carouselInitialIndex = ref(0);
const reorderModalVisible = ref(false);
const uploadModalVisible = ref(false);

// Image delete state
const deleteImageModalVisible = ref(false);
const imageToDelete = ref<any>(null);
const deletingImage = ref(false);
const deleteImageError = ref<string | null>(null);

// Analysis state
const analysisVisible = ref(false);
const hasAnalysis = computed(() => booksStore.currentBook?.has_analysis ?? false);

// Analysis polling state
let analysisPollingInterval: ReturnType<typeof setInterval> | null = null;
const ANALYSIS_POLL_INTERVAL = 5000; // 5 seconds

function startAnalysisPolling() {
  if (analysisPollingInterval) return; // Already polling

  analysisPollingInterval = setInterval(async () => {
    const book = booksStore.currentBook;
    if (!book) return;

    // Only poll if there's an active job
    const status = book.analysis_job_status;
    if (status !== "running" && status !== "pending") {
      stopAnalysisPolling();
      return;
    }

    // Refresh book data
    await booksStore.fetchBook(book.id);

    // Check if job completed (status becomes null) or failed
    const newStatus = booksStore.currentBook?.analysis_job_status;
    if (newStatus !== "running" && newStatus !== "pending") {
      stopAnalysisPolling();
    }
  }, ANALYSIS_POLL_INTERVAL);
}

function stopAnalysisPolling() {
  if (analysisPollingInterval) {
    clearInterval(analysisPollingInterval);
    analysisPollingInterval = null;
  }
}

// Watch for analysis job status changes to start/stop polling
watch(
  () => booksStore.currentBook?.analysis_job_status,
  (newStatus) => {
    if (newStatus === "running" || newStatus === "pending") {
      startAnalysisPolling();
    } else {
      stopAnalysisPolling();
    }
  },
  { immediate: true }
);

// Analysis generation state
const startingAnalysis = ref(false);
const selectedModel = ref<"sonnet" | "opus">("sonnet");
const modelOptions = [
  { value: "sonnet", label: "Sonnet 4.5" },
  { value: "opus", label: "Opus 4.5" },
];

// Eval Runbook state
const evalRunbookVisible = ref(false);

// Delete confirmation state
const deleteModalVisible = ref(false);
const deleting = ref(false);
const deleteError = ref<string | null>(null);

// Status management
const statusOptions = ["ON_HAND", "IN_TRANSIT", "SOLD", "REMOVED"];
const updatingStatus = ref(false);

// Computed property for back link that preserves filter state
const backToCollectionLink = computed(() => {
  const query: Record<string, string> = {};
  // Empty string (All Collections) is stored as "ALL" in URL
  if (booksStore.filters.inventory_type === "") {
    query.inventory_type = "ALL";
  } else if (booksStore.filters.inventory_type && booksStore.filters.inventory_type !== "PRIMARY") {
    query.inventory_type = booksStore.filters.inventory_type;
  }
  if (booksStore.filters.q) {
    query.q = booksStore.filters.q;
  }
  if (booksStore.filters.binding_authenticated !== undefined) {
    query.binding_authenticated = String(booksStore.filters.binding_authenticated);
  }
  return { path: "/books", query };
});

// Provenance editing
const provenanceEditing = ref(false);
const provenanceText = ref("");
const savingProvenance = ref(false);

onMounted(async () => {
  const id = Number(route.params.id);
  await booksStore.fetchBook(id);

  // Fetch images
  try {
    const response = await api.get(`/books/${id}/images`);
    images.value = response.data;
  } catch {
    images.value = [];
  }
});

// Cleanup polling on unmount
onUnmounted(() => {
  stopAnalysisPolling();
});

function formatCurrency(value: number | null): string {
  if (value === null) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
  }).format(value);
}

function openCarousel(index: number = 0) {
  carouselInitialIndex.value = index;
  carouselVisible.value = true;
}

function closeCarousel() {
  carouselVisible.value = false;
}

function openReorderModal() {
  reorderModalVisible.value = true;
}

function closeReorderModal() {
  reorderModalVisible.value = false;
}

function handleImagesReordered(newImages: typeof images.value) {
  images.value = newImages;
}

function openUploadModal() {
  uploadModalVisible.value = true;
}

function closeUploadModal() {
  uploadModalVisible.value = false;
}

async function handleImagesUploaded() {
  // Refresh images list
  if (booksStore.currentBook) {
    try {
      const response = await api.get(`/books/${booksStore.currentBook.id}/images`);
      images.value = response.data;
    } catch {
      // Keep existing images
    }
  }
}

function openDeleteImageModal(img: any) {
  imageToDelete.value = img;
  deleteImageError.value = null;
  deleteImageModalVisible.value = true;
}

function closeDeleteImageModal() {
  deleteImageModalVisible.value = false;
  imageToDelete.value = null;
}

async function confirmDeleteImage() {
  if (!booksStore.currentBook || !imageToDelete.value) return;

  deletingImage.value = true;
  deleteImageError.value = null;

  try {
    await api.delete(`/books/${booksStore.currentBook.id}/images/${imageToDelete.value.id}`);
    // Remove from local array
    images.value = images.value.filter((img) => img.id !== imageToDelete.value.id);
    closeDeleteImageModal();
  } catch (e: any) {
    deleteImageError.value = e.response?.data?.detail || e.message || "Failed to delete image";
  } finally {
    deletingImage.value = false;
  }
}

function openAnalysis() {
  analysisVisible.value = true;
}

function closeAnalysis() {
  analysisVisible.value = false;
}

// Analysis job tracking
function isAnalysisRunning(): boolean {
  if (!booksStore.currentBook) return false;
  return booksStore.hasActiveJob(booksStore.currentBook.id);
}

function getJobStatus() {
  if (!booksStore.currentBook) return null;
  return booksStore.getActiveJob(booksStore.currentBook.id);
}

async function handleGenerateAnalysis() {
  const book = booksStore.currentBook;
  if (!book || isAnalysisRunning() || startingAnalysis.value) return;

  startingAnalysis.value = true;
  try {
    await booksStore.generateAnalysisAsync(book.id, selectedModel.value);
  } catch (e: unknown) {
    console.error("Failed to start analysis:", e);
    const err = e as { response?: { data?: { detail?: string } }; message?: string };
    const message = err.response?.data?.detail || err.message || "Failed to start analysis";
    alert(message);
  } finally {
    startingAnalysis.value = false;
  }
}

function openDeleteModal() {
  deleteError.value = null;
  deleteModalVisible.value = true;
}

function closeDeleteModal() {
  deleteModalVisible.value = false;
}

async function confirmDelete() {
  if (!booksStore.currentBook) return;

  deleting.value = true;
  deleteError.value = null;

  try {
    await booksStore.deleteBook(booksStore.currentBook.id);
    deleteModalVisible.value = false;
    router.push("/books");
  } catch (e: any) {
    deleteError.value = e.message || "Failed to delete book";
  } finally {
    deleting.value = false;
  }
}

async function updateStatus(newStatus: string) {
  if (!booksStore.currentBook || updatingStatus.value) return;

  updatingStatus.value = true;
  try {
    await api.patch(`/books/${booksStore.currentBook.id}/status?status=${newStatus}`);
    booksStore.currentBook.status = newStatus;
  } catch (e: any) {
    console.error("Failed to update status:", e);
  } finally {
    updatingStatus.value = false;
  }
}

function startProvenanceEdit() {
  provenanceText.value = booksStore.currentBook?.provenance || "";
  provenanceEditing.value = true;
}

function cancelProvenanceEdit() {
  provenanceEditing.value = false;
  provenanceText.value = "";
}

async function saveProvenance() {
  if (!booksStore.currentBook || savingProvenance.value) return;

  savingProvenance.value = true;
  try {
    await booksStore.updateBook(booksStore.currentBook.id, {
      provenance: provenanceText.value || null,
    });
    provenanceEditing.value = false;
  } catch (e: any) {
    console.error("Failed to save provenance:", e);
  } finally {
    savingProvenance.value = false;
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case "ON_HAND":
      return "bg-green-100 text-green-800";
    case "IN_TRANSIT":
      return "bg-blue-100 text-blue-800";
    case "SOLD":
      return "bg-gray-100 text-gray-800";
    case "REMOVED":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

// Print function
function printPage() {
  window.print();
}
</script>

<template>
  <div v-if="booksStore.loading" class="text-center py-12">
    <p class="text-gray-500">Loading book details...</p>
  </div>

  <div v-else-if="booksStore.currentBook" class="max-w-5xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 sm:gap-0">
        <RouterLink
          :to="backToCollectionLink"
          class="text-moxon-600 hover:text-moxon-800 inline-block"
        >
          &larr; Back to Collection
        </RouterLink>
        <div class="flex gap-2">
          <!-- Print button (visible to all users) -->
          <button
            @click="printPage"
            class="no-print text-victorian-ink-muted hover:text-victorian-ink-dark p-2 rounded hover:bg-victorian-paper-cream transition-colors"
            title="Print this page"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
              />
            </svg>
          </button>
          <!-- Editor-only actions -->
          <template v-if="authStore.isEditor">
            <RouterLink
              :to="`/books/${booksStore.currentBook.id}/edit`"
              class="btn-secondary text-sm sm:text-base px-3 sm:px-4 no-print"
            >
              Edit Book
            </RouterLink>
            <button @click="openDeleteModal" class="btn-danger text-sm sm:text-base px-3 sm:px-4 no-print">
              Delete
            </button>
          </template>
        </div>
      </div>
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-800 mt-4">
        {{ booksStore.currentBook.title }}
      </h1>
      <p class="text-lg sm:text-xl text-gray-600 mt-2">
        {{ booksStore.currentBook.author?.name || "Unknown Author" }}
      </p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Main Content (2 columns) -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Image Gallery -->
        <div class="card">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-gray-800">Images</h2>
            <div v-if="authStore.isEditor" class="flex items-center gap-3">
              <button
                @click="openUploadModal"
                class="text-sm text-moxon-600 hover:text-moxon-800 flex items-center gap-1"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 4v16m8-8H4"
                  />
                </svg>
                Add Images
              </button>
              <button
                v-if="images.length > 1"
                @click="openReorderModal"
                class="text-sm text-moxon-600 hover:text-moxon-800 flex items-center gap-1"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
                  />
                </svg>
                Reorder
              </button>
            </div>
          </div>
          <div v-if="images.length > 0" class="grid grid-cols-4 gap-3">
            <div
              v-for="(img, idx) in images"
              :key="img.id"
              class="relative group aspect-square rounded overflow-hidden"
            >
              <button
                @click="openCarousel(idx)"
                class="w-full h-full hover:ring-2 hover:ring-moxon-500 transition-all"
              >
                <img
                  :src="img.thumbnail_url"
                  :alt="img.caption || `Image ${idx + 1}`"
                  loading="lazy"
                  decoding="async"
                  class="w-full h-full object-cover"
                />
                <!-- Zoom hint overlay -->
                <div
                  class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all flex items-center justify-center"
                >
                  <svg
                    class="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"
                    />
                  </svg>
                </div>
              </button>
              <!-- Delete button (visible on hover, editors only) -->
              <button
                v-if="authStore.isEditor"
                @click.stop="openDeleteImageModal(img)"
                class="absolute top-1 right-1 p-1 bg-red-600 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-700"
                title="Delete image"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          </div>
          <div v-else class="flex items-center justify-center py-8">
            <div class="text-center">
              <BookThumbnail :book-id="booksStore.currentBook.id" size="lg" />
              <p class="text-sm text-gray-500 mt-3">No images available</p>
            </div>
          </div>
        </div>

        <!-- Publication Details -->
        <div class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Publication Details</h2>
          <dl class="grid grid-cols-2 gap-4">
            <div>
              <dt class="text-sm text-gray-500">Publisher</dt>
              <dd class="font-medium">
                {{ booksStore.currentBook.publisher?.name || "-" }}
                <span v-if="booksStore.currentBook.publisher?.tier" class="text-xs text-moxon-600">
                  ({{ booksStore.currentBook.publisher.tier }})
                </span>
                <!-- First Edition Badge -->
                <span
                  v-if="booksStore.currentBook.is_first_edition"
                  class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded bg-amber-100 text-amber-800"
                >
                  1st Edition
                </span>
                <!-- Provenance Badges -->
                <span
                  v-if="
                    booksStore.currentBook.has_provenance &&
                    booksStore.currentBook.provenance_tier === 'Tier 1'
                  "
                  class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded bg-amber-100 text-amber-800"
                >
                  Tier 1 Provenance
                </span>
                <span
                  v-if="
                    booksStore.currentBook.has_provenance &&
                    booksStore.currentBook.provenance_tier === 'Tier 2'
                  "
                  class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-800"
                >
                  Tier 2 Provenance
                </span>
                <span
                  v-if="
                    booksStore.currentBook.has_provenance &&
                    booksStore.currentBook.provenance_tier === 'Tier 3'
                  "
                  class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-800"
                >
                  Tier 3 Provenance
                </span>
                <span
                  v-if="
                    booksStore.currentBook.has_provenance && !booksStore.currentBook.provenance_tier
                  "
                  class="ml-2 inline-block px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-600"
                >
                  Has Provenance
                </span>
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Date</dt>
              <dd class="font-medium">
                {{ booksStore.currentBook.publication_date || "-" }}
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Edition</dt>
              <dd class="font-medium">
                {{ booksStore.currentBook.edition || "-" }}
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Volumes</dt>
              <dd class="font-medium">{{ booksStore.currentBook.volumes }}</dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Category</dt>
              <dd class="font-medium">
                {{ booksStore.currentBook.category || "-" }}
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Status</dt>
              <dd>
                <!-- Editors can change status -->
                <select
                  v-if="authStore.isEditor"
                  :value="booksStore.currentBook.status"
                  @change="updateStatus(($event.target as HTMLSelectElement).value)"
                  :disabled="updatingStatus"
                  :class="[
                    'px-2 py-1 rounded text-sm font-medium border-0 cursor-pointer',
                    getStatusColor(booksStore.currentBook.status),
                    updatingStatus ? 'opacity-50' : '',
                  ]"
                >
                  <option v-for="status in statusOptions" :key="status" :value="status">
                    {{ status.replace("_", " ") }}
                  </option>
                </select>
                <!-- Viewers see read-only badge -->
                <span
                  v-else
                  :class="[
                    'px-2 py-1 rounded text-sm font-medium',
                    getStatusColor(booksStore.currentBook.status),
                  ]"
                >
                  {{ booksStore.currentBook.status.replace("_", " ") }}
                </span>
              </dd>
            </div>
          </dl>
        </div>

        <!-- Binding -->
        <div class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Binding</h2>
          <dl class="space-y-2">
            <div>
              <dt class="text-sm text-gray-500">Type</dt>
              <dd class="font-medium">
                {{ booksStore.currentBook.binding_type || "-" }}
              </dd>
            </div>
            <div v-if="booksStore.currentBook.binding_authenticated">
              <dt class="text-sm text-gray-500">Bindery</dt>
              <dd class="font-medium text-victorian-burgundy">
                {{ booksStore.currentBook.binder?.name }} (Authenticated)
              </dd>
            </div>
            <div v-if="booksStore.currentBook.binding_description">
              <dt class="text-sm text-gray-500">Description</dt>
              <dd class="text-gray-700">
                {{ booksStore.currentBook.binding_description }}
              </dd>
            </div>
          </dl>
        </div>

        <!-- Notes -->
        <div v-if="booksStore.currentBook.notes" class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Notes</h2>
          <p class="text-gray-700 whitespace-pre-wrap">
            {{ booksStore.currentBook.notes }}
          </p>
        </div>

        <!-- Provenance -->
        <div class="card">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-gray-800">Provenance</h2>
            <button
              v-if="authStore.isEditor && !provenanceEditing"
              @click="startProvenanceEdit"
              class="text-sm text-moxon-600 hover:text-moxon-800"
            >
              {{ booksStore.currentBook.provenance ? "Edit" : "Add provenance" }}
            </button>
          </div>

          <!-- View mode -->
          <div v-if="!provenanceEditing">
            <p v-if="booksStore.currentBook.provenance" class="text-gray-700 whitespace-pre-wrap">
              {{ booksStore.currentBook.provenance }}
            </p>
            <p v-else class="text-gray-400 italic">
              No provenance information recorded. Click "Add provenance" to document ownership
              history.
            </p>
          </div>

          <!-- Edit mode -->
          <div v-else>
            <textarea
              v-model="provenanceText"
              rows="4"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-moxon-500 focus:border-moxon-500"
              placeholder="Document ownership history, previous owners, bookplates, inscriptions, etc."
            ></textarea>
            <div class="flex justify-end gap-2 mt-3">
              <button
                @click="cancelProvenanceEdit"
                :disabled="savingProvenance"
                class="btn-secondary text-sm"
              >
                Cancel
              </button>
              <button
                @click="saveProvenance"
                :disabled="savingProvenance"
                class="btn-primary text-sm"
              >
                {{ savingProvenance ? "Saving..." : "Save" }}
              </button>
            </div>
          </div>
        </div>

        <!-- Eval Runbook and Analysis Buttons -->
        <div class="space-y-4">
          <!-- Eval Runbook Button -->
          <div
            v-if="booksStore.currentBook?.has_eval_runbook"
            class="card bg-blue-50 border-blue-200"
          >
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-lg font-semibold text-gray-800">Eval Runbook</h2>
                <p class="text-sm text-gray-600 mt-1">
                  Quick strategic fit scoring and acquisition recommendation.
                </p>
              </div>
              <button
                @click="evalRunbookVisible = true"
                class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                View Runbook
              </button>
            </div>
          </div>

          <!-- Analysis Card -->
          <div class="card bg-victorian-cream border-victorian-burgundy/20">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-lg font-semibold text-gray-800">Detailed Analysis</h2>
                <!-- State: Job running -->
                <div
                  v-if="isAnalysisRunning() || booksStore.currentBook?.analysis_job_status"
                  class="text-sm text-blue-600 mt-1 flex items-center gap-1"
                >
                  <span class="animate-spin">&#8987;</span>
                  <span>
                    {{
                      (getJobStatus()?.status || booksStore.currentBook?.analysis_job_status) ===
                      "pending"
                        ? "Queued..."
                        : "Analyzing..."
                    }}
                  </span>
                </div>
                <!-- State: Job failed -->
                <p
                  v-else-if="getJobStatus()?.status === 'failed'"
                  class="text-sm text-red-600 mt-1"
                >
                  Analysis failed. Please try again.
                </p>
                <!-- State: Has analysis -->
                <p v-else-if="hasAnalysis" class="text-sm text-gray-600 mt-1">
                  View the full Napoleon-style acquisition analysis for this book.
                </p>
                <!-- State: No analysis (editor/admin can generate) -->
                <p v-else-if="authStore.isEditor" class="text-sm text-gray-600 mt-1">
                  Generate a Napoleon-style acquisition analysis for this book.
                </p>
                <!-- State: No analysis (viewer - no action available) -->
                <p v-else class="text-sm text-gray-500 mt-1">
                  No analysis available for this book.
                </p>
              </div>

              <!-- Action buttons -->
              <div class="flex items-center gap-2">
                <!-- View Analysis button (all users, when analysis exists) -->
                <button
                  v-if="
                    hasAnalysis &&
                    !isAnalysisRunning() &&
                    !booksStore.currentBook?.analysis_job_status
                  "
                  @click="openAnalysis"
                  class="btn-primary"
                >
                  View Analysis
                </button>

                <!-- Model selector (editor/admin only, when not running) -->
                <select
                  v-if="
                    authStore.isEditor &&
                    !isAnalysisRunning() &&
                    !booksStore.currentBook?.analysis_job_status
                  "
                  v-model="selectedModel"
                  class="text-sm border border-gray-300 rounded px-2 py-1.5"
                  :disabled="startingAnalysis"
                >
                  <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>

                <!-- Generate button (editor/admin, no analysis exists) -->
                <button
                  v-if="
                    !hasAnalysis &&
                    authStore.isEditor &&
                    !isAnalysisRunning() &&
                    !booksStore.currentBook?.analysis_job_status
                  "
                  @click="handleGenerateAnalysis"
                  :disabled="startingAnalysis"
                  class="btn-primary flex items-center gap-1 disabled:opacity-50"
                >
                  <span v-if="startingAnalysis" class="animate-spin">&#8987;</span>
                  <span v-else>&#9889;</span>
                  {{ startingAnalysis ? "Starting..." : "Generate Analysis" }}
                </button>

                <!-- Regenerate button (editor/admin, analysis exists) -->
                <button
                  v-if="
                    hasAnalysis &&
                    authStore.isEditor &&
                    !isAnalysisRunning() &&
                    !booksStore.currentBook?.analysis_job_status
                  "
                  @click="handleGenerateAnalysis"
                  :disabled="startingAnalysis"
                  class="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 flex items-center gap-1"
                  title="Regenerate analysis with selected model"
                >
                  <span v-if="startingAnalysis" class="animate-spin">&#8987;</span>
                  <span v-else>&#128260;</span>
                  {{ startingAnalysis ? "Starting..." : "Regenerate" }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Sidebar - Valuation -->
      <div class="space-y-6">
        <div class="card bg-victorian-cream">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Valuation</h2>
          <div class="text-center">
            <p class="text-3xl font-bold text-victorian-gold">
              {{ formatCurrency(booksStore.currentBook.value_mid) }}
            </p>
            <p class="text-sm text-gray-500 mt-1">Mid Estimate</p>
          </div>
          <div class="flex justify-between mt-4 text-sm">
            <div class="text-center">
              <p class="font-medium">
                {{ formatCurrency(booksStore.currentBook.value_low) }}
              </p>
              <p class="text-gray-500">Low</p>
            </div>
            <div class="text-center">
              <p class="font-medium">
                {{ formatCurrency(booksStore.currentBook.value_high) }}
              </p>
              <p class="text-gray-500">High</p>
            </div>
          </div>
          <!-- Purchase Price -->
          <div
            v-if="booksStore.currentBook.purchase_price"
            class="mt-4 pt-4 border-t border-gray-200"
          >
            <div class="text-center">
              <p class="text-xl font-semibold text-gray-700">
                {{ formatCurrency(booksStore.currentBook.purchase_price) }}
              </p>
              <p class="text-sm text-gray-500">Purchase Price</p>
            </div>
          </div>
        </div>

        <div v-if="booksStore.currentBook.purchase_price" class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Acquisition</h2>
          <dl class="space-y-2">
            <div>
              <dt class="text-sm text-gray-500">Purchase Price</dt>
              <dd class="font-medium">
                {{ formatCurrency(booksStore.currentBook.purchase_price) }}
              </dd>
            </div>
            <div v-if="booksStore.currentBook.acquisition_cost">
              <dt class="text-sm text-gray-500">Acquisition Cost</dt>
              <dd class="font-medium">
                {{ formatCurrency(booksStore.currentBook.acquisition_cost) }}
                <span class="text-xs text-gray-400">(incl. shipping/tax)</span>
              </dd>
            </div>
            <div v-if="booksStore.currentBook.discount_pct">
              <dt class="text-sm text-gray-500">Discount</dt>
              <dd class="font-medium text-green-600">{{ booksStore.currentBook.discount_pct }}%</dd>
            </div>
            <div v-if="booksStore.currentBook.roi_pct">
              <dt class="text-sm text-gray-500">ROI</dt>
              <dd class="font-medium text-green-600">{{ booksStore.currentBook.roi_pct }}%</dd>
            </div>
          </dl>
        </div>

        <!-- Source Archive -->
        <div v-if="booksStore.currentBook.source_url" class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Source Archive</h2>
          <dl class="space-y-3">
            <div>
              <dt class="text-sm text-gray-500">Original Listing</dt>
              <dd class="font-medium truncate">
                <a
                  :href="booksStore.currentBook.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-moxon-600 hover:text-moxon-800 hover:underline"
                  :title="booksStore.currentBook.source_url"
                >
                  View Source
                </a>
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500 mb-1">Archive Status</dt>
              <dd>
                <ArchiveStatusBadge
                  :status="booksStore.currentBook.archive_status"
                  :archived-url="booksStore.currentBook.source_archived_url"
                />
              </dd>
            </div>
          </dl>
        </div>

        <!-- Quick Stats -->
        <div class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Quick Info</h2>
          <dl class="space-y-2 text-sm">
            <div class="flex justify-between">
              <dt class="text-gray-500">Images</dt>
              <dd class="font-medium">{{ images.length }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Has Analysis</dt>
              <dd class="font-medium">{{ hasAnalysis ? "Yes" : "No" }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Inventory Type</dt>
              <dd class="font-medium">
                {{ booksStore.currentBook.inventory_type }}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </div>

    <!-- Image Carousel Modal -->
    <ImageCarousel
      :book-id="booksStore.currentBook.id"
      :visible="carouselVisible"
      :initial-index="carouselInitialIndex"
      @close="closeCarousel"
    />

    <!-- Image Reorder Modal -->
    <ImageReorderModal
      :book-id="booksStore.currentBook.id"
      :visible="reorderModalVisible"
      :images="images"
      @close="closeReorderModal"
      @reordered="handleImagesReordered"
    />

    <!-- Image Upload Modal -->
    <ImageUploadModal
      :book-id="booksStore.currentBook.id"
      :visible="uploadModalVisible"
      @close="closeUploadModal"
      @uploaded="handleImagesUploaded"
    />

    <!-- Delete Image Confirmation Modal -->
    <Teleport to="body">
      <div
        v-if="deleteImageModalVisible"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/50" @click="closeDeleteImageModal"></div>

        <!-- Modal -->
        <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
          <h3 class="text-xl font-semibold text-gray-800 mb-4">Delete Image</h3>

          <div class="mb-6">
            <p class="text-gray-600 mb-3">Are you sure you want to delete this image?</p>
            <div v-if="imageToDelete" class="flex justify-center">
              <img
                :src="imageToDelete.thumbnail_url"
                :alt="imageToDelete.caption || 'Image'"
                class="w-32 h-32 object-cover rounded"
              />
            </div>
            <p class="text-sm text-red-600 mt-3 text-center">This action cannot be undone.</p>
          </div>

          <div
            v-if="deleteImageError"
            class="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm"
          >
            {{ deleteImageError }}
          </div>

          <div class="flex justify-end gap-3">
            <button @click="closeDeleteImageModal" :disabled="deletingImage" class="btn-secondary">
              Cancel
            </button>
            <button @click="confirmDeleteImage" :disabled="deletingImage" class="btn-danger">
              {{ deletingImage ? "Deleting..." : "Delete Image" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Eval Runbook Modal -->
    <EvalRunbookModal
      v-if="evalRunbookVisible && booksStore.currentBook"
      :book-id="booksStore.currentBook.id"
      :book-title="booksStore.currentBook.title"
      @close="evalRunbookVisible = false"
    />

    <!-- Analysis Viewer Modal -->
    <AnalysisViewer
      :book-id="booksStore.currentBook.id"
      :visible="analysisVisible"
      @close="closeAnalysis"
    />

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <div v-if="deleteModalVisible" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/50" @click="closeDeleteModal"></div>

        <!-- Modal -->
        <div class="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
          <h3 class="text-xl font-semibold text-gray-800 mb-4">Delete Book</h3>

          <div class="mb-6">
            <p class="text-gray-600 mb-3">Are you sure you want to delete this book?</p>
            <p class="font-medium text-gray-800 mb-2">"{{ booksStore.currentBook.title }}"</p>
            <p class="text-sm text-red-600">
              This will permanently delete the book along with all associated images ({{
                images.length
              }}) and analysis data.
            </p>
          </div>

          <div
            v-if="deleteError"
            class="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm"
          >
            {{ deleteError }}
          </div>

          <div class="flex justify-end gap-3">
            <button @click="closeDeleteModal" :disabled="deleting" class="btn-secondary">
              Cancel
            </button>
            <button @click="confirmDelete" :disabled="deleting" class="btn-danger">
              {{ deleting ? "Deleting..." : "Delete Book" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* Print styles */
@media print {
  .no-print {
    display: none !important;
  }

  /* Optimize layout for print */
  .max-w-5xl {
    max-width: none !important;
  }

  .card {
    break-inside: avoid;
    box-shadow: none !important;
    border: 1px solid #ddd !important;
  }

  /* Hide interactive elements */
  select,
  button {
    display: none !important;
  }

  /* Show status as text instead of dropdown */
  .card dd span {
    display: inline !important;
  }

  /* Ensure images print */
  img {
    max-width: 100% !important;
  }
}
</style>
