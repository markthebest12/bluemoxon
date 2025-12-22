<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useAcquisitionsStore, type AcquisitionBook } from "@/stores/acquisitions";
import { useBooksStore } from "@/stores/books";
import { useAuthStore } from "@/stores/auth";
import { storeToRefs } from "pinia";
import { useJobPolling } from "@/composables/useJobPolling";
import { api } from "@/services/api";
import AcquireModal from "@/components/AcquireModal.vue";
import AddToWatchlistModal from "@/components/AddToWatchlistModal.vue";
import EditWatchlistModal from "@/components/EditWatchlistModal.vue";
import ImportListingModal from "@/components/ImportListingModal.vue";
import AddTrackingModal from "@/components/AddTrackingModal.vue";
import ScoreCard from "@/components/ScoreCard.vue";
import ArchiveStatusBadge from "@/components/ArchiveStatusBadge.vue";
import AnalysisViewer from "@/components/books/AnalysisViewer.vue";
import EvalRunbookModal from "@/components/books/EvalRunbookModal.vue";

const acquisitionsStore = useAcquisitionsStore();
const booksStore = useBooksStore();
const authStore = useAuthStore();
const { evaluating, inTransit, received, loading, error } = storeToRefs(acquisitionsStore);

// Job polling instances per book - store the composable return type directly
type JobPoller = ReturnType<typeof useJobPolling>;
const analysisPollers = new Map<number, JobPoller>();
const evalRunbookPollers = new Map<number, JobPoller>();

function getOrCreateAnalysisPoller(bookId: number) {
  if (!analysisPollers.has(bookId)) {
    const poller = useJobPolling("analysis", {
      onComplete: () => acquisitionsStore.refreshBook(bookId),
    });
    analysisPollers.set(bookId, poller);
  }
  return analysisPollers.get(bookId)!;
}

function getOrCreateEvalRunbookPoller(bookId: number) {
  if (!evalRunbookPollers.has(bookId)) {
    const poller = useJobPolling("eval-runbook", {
      onComplete: () => acquisitionsStore.refreshBook(bookId),
    });
    evalRunbookPollers.set(bookId, poller);
  }
  return evalRunbookPollers.get(bookId)!;
}

const showAcquireModal = ref(false);
const selectedBookId = ref<number | null>(null);
const showWatchlistModal = ref(false);
const showImportModal = ref(false);
const showEditModal = ref(false);
const editingBook = ref<AcquisitionBook | null>(null);
const showAnalysisViewer = ref(false);
const analysisBookId = ref<number | null>(null);
const showEvalRunbook = ref(false);
const evalRunbookBook = ref<AcquisitionBook | null>(null);
const showTrackingModal = ref(false);
const trackingBook = ref<AcquisitionBook | null>(null);

const selectedBook = computed(() => {
  if (!selectedBookId.value) return null;
  return evaluating.value.find((b) => b.id === selectedBookId.value);
});

function openAcquireModal(bookId: number) {
  selectedBookId.value = bookId;
  showAcquireModal.value = true;
}

function closeAcquireModal() {
  showAcquireModal.value = false;
  selectedBookId.value = null;
}

function openWatchlistModal() {
  showWatchlistModal.value = true;
}

function closeWatchlistModal() {
  showWatchlistModal.value = false;
}

async function handleWatchlistAdded() {
  showWatchlistModal.value = false;
  await acquisitionsStore.fetchAll();
  syncBackendJobPolling(); // Start polling for any running jobs on the new book
}

function openImportModal() {
  showImportModal.value = true;
}

function closeImportModal() {
  showImportModal.value = false;
}

async function handleImportAdded() {
  showImportModal.value = false;
  await acquisitionsStore.fetchAll();
  syncBackendJobPolling(); // Start polling for any running jobs on the new book
}

function openEditModal(book: AcquisitionBook) {
  editingBook.value = book;
  showEditModal.value = true;
}

function closeEditModal() {
  showEditModal.value = false;
  editingBook.value = null;
}

function handleEditUpdated() {
  showEditModal.value = false;
  editingBook.value = null;
  acquisitionsStore.fetchAll();
}

function openAnalysisViewer(bookId: number) {
  analysisBookId.value = bookId;
  showAnalysisViewer.value = true;
}

function closeAnalysisViewer() {
  showAnalysisViewer.value = false;
  analysisBookId.value = null;
}

function openEvalRunbook(book: AcquisitionBook) {
  evalRunbookBook.value = book;
  showEvalRunbook.value = true;
}

function closeEvalRunbook() {
  showEvalRunbook.value = false;
  evalRunbookBook.value = null;
}

function openTrackingModal(book: AcquisitionBook) {
  trackingBook.value = book;
  showTrackingModal.value = true;
}

function closeTrackingModal() {
  showTrackingModal.value = false;
  trackingBook.value = null;
}

function handleTrackingAdded() {
  showTrackingModal.value = false;
  trackingBook.value = null;
}

function formatTrackingNumber(number?: string | null): string {
  if (!number) return "";
  // Truncate long tracking numbers for display
  if (number.length > 12) {
    return number.slice(0, 6) + "..." + number.slice(-4);
  }
  return number;
}

function formatPrice(price?: number | string | null): string {
  if (price == null) return "-";
  const numPrice = typeof price === "string" ? parseFloat(price) : price;
  if (isNaN(numPrice)) return "-";
  return `$${numPrice.toFixed(2)}`;
}

function formatDiscount(discount?: number | string | null): string {
  if (discount == null) return "-";
  const numDiscount = typeof discount === "string" ? parseFloat(discount) : discount;
  if (isNaN(numDiscount)) return "-";
  return `${numDiscount.toFixed(0)}%`;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatDateRange(startDate?: string, endDate?: string): string {
  if (!startDate) return "-";
  const start = formatDate(startDate);
  if (!endDate) return start;
  const end = formatDate(endDate);
  return `${start} - ${end}`;
}

async function handleMarkReceived(bookId: number) {
  await acquisitionsStore.markReceived(bookId);
}

async function handleDelete(bookId: number) {
  if (confirm("Delete this item from watchlist?")) {
    deletingBook.value = bookId;
    try {
      await acquisitionsStore.deleteEvaluating(bookId);
    } catch (e: unknown) {
      console.error("Failed to delete:", e);
      alert("Failed to delete item. Please try again.");
    } finally {
      deletingBook.value = null;
    }
  }
}

// Job status tracking using composable-based polling
function getJobStatus(bookId: number) {
  const poller = analysisPollers.get(bookId);
  return poller ? { status: poller.status.value, error_message: poller.error.value } : null;
}

function isAnalysisRunning(bookId: number) {
  const poller = analysisPollers.get(bookId);
  return poller?.isActive.value ?? false;
}

function getEvalRunbookJobStatus(bookId: number) {
  const poller = evalRunbookPollers.get(bookId);
  return poller ? { status: poller.status.value, error_message: poller.error.value } : null;
}

function isEvalRunbookRunning(bookId: number) {
  const poller = evalRunbookPollers.get(bookId);
  return poller?.isActive.value ?? false;
}

async function handleGenerateAnalysis(bookId: number) {
  if (isAnalysisRunning(bookId) || startingAnalysis.value === bookId) return;

  startingAnalysis.value = bookId;
  try {
    await api.post(`/books/${bookId}/analysis/generate-async`, { model: "sonnet" });
    const poller = getOrCreateAnalysisPoller(bookId);
    poller.start(bookId);
  } catch (e: any) {
    console.error("Failed to start analysis:", e);
    const message = e.response?.data?.detail || e.message || "Failed to start analysis";
    alert(message);
  } finally {
    startingAnalysis.value = null;
  }
}

async function handleGenerateEvalRunbook(bookId: number) {
  if (isEvalRunbookRunning(bookId) || startingEvalRunbook.value === bookId) return;

  startingEvalRunbook.value = bookId;
  try {
    await api.post(`/books/${bookId}/eval-runbook/generate`);
    const poller = getOrCreateEvalRunbookPoller(bookId);
    poller.start(bookId);
  } catch (err) {
    console.error("Failed to start eval runbook generation:", err);
  } finally {
    startingEvalRunbook.value = null;
  }
}

/**
 * Sync backend job status with frontend polling.
 * Called after fetchAll to start polling for any running jobs from other sessions.
 * This handles the case where a job was started in a previous browser session.
 */
function syncBackendJobPolling() {
  for (const book of evaluating.value) {
    // Start polling for any running eval runbook jobs
    if (
      (book.eval_runbook_job_status === "running" || book.eval_runbook_job_status === "pending") &&
      !isEvalRunbookRunning(book.id)
    ) {
      const poller = getOrCreateEvalRunbookPoller(book.id);
      poller.start(book.id);
    }

    // Start polling for any running analysis jobs
    if (
      (book.analysis_job_status === "running" || book.analysis_job_status === "pending") &&
      !isAnalysisRunning(book.id)
    ) {
      const poller = getOrCreateAnalysisPoller(book.id);
      poller.start(book.id);
    }
  }
}

onMounted(async () => {
  await acquisitionsStore.fetchAll();

  // Start polling for any jobs that are running on backend but not tracked locally
  syncBackendJobPolling();
});

const recalculatingScore = ref<number | null>(null);

async function handleRecalculateScore(bookId: number) {
  if (recalculatingScore.value) return;
  recalculatingScore.value = bookId;
  try {
    await booksStore.calculateScores(bookId);
    await acquisitionsStore.fetchAll();
  } finally {
    recalculatingScore.value = null;
  }
}

const archivingBook = ref<number | null>(null);
const deletingBook = ref<number | null>(null);
const startingAnalysis = ref<number | null>(null);
const startingEvalRunbook = ref<number | null>(null);
const refreshingTracking = ref<number | null>(null);

async function handleRefreshTracking(bookId: number) {
  if (refreshingTracking.value) return;
  refreshingTracking.value = bookId;
  try {
    await acquisitionsStore.refreshTracking(bookId);
  } catch (e: unknown) {
    console.error("Failed to refresh tracking:", e);
  } finally {
    refreshingTracking.value = null;
  }
}

async function handleArchiveSource(bookId: number) {
  if (archivingBook.value) return;
  archivingBook.value = bookId;
  try {
    await acquisitionsStore.archiveSource(bookId);
  } catch (e: unknown) {
    console.error("Failed to archive source:", e);
  } finally {
    archivingBook.value = null;
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6">
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="mb-6 flex items-start justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Acquisitions</h1>
          <p class="text-gray-600">Track books from watchlist through delivery</p>
        </div>
        <div class="flex gap-2">
          <button
            data-testid="import-from-ebay"
            @click="openImportModal"
            class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            🔗 Import from eBay
          </button>
          <button
            data-testid="add-to-watchlist"
            @click="openWatchlistModal"
            class="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 flex items-center gap-2"
          >
            + Add Manually
          </button>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <p class="text-red-700">{{ error }}</p>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>

      <!-- Kanban Board -->
      <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- EVALUATING Column -->
        <div class="bg-white rounded-lg shadow">
          <div class="p-4 border-b border-gray-200">
            <h2 class="font-semibold text-gray-900 flex items-center gap-2">
              <span class="w-3 h-3 bg-yellow-400 rounded-full"></span>
              Evaluating
              <span class="ml-auto text-sm text-gray-500">{{ evaluating.length }}</span>
            </h2>
          </div>
          <div class="p-4 space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto">
            <div
              v-for="book in evaluating"
              :key="book.id"
              class="bg-gray-50 rounded-lg p-3 border border-gray-200 hover:border-blue-300 transition-colors"
            >
              <a
                :href="`/books/${book.id}`"
                target="_blank"
                rel="noopener noreferrer"
                class="block hover:text-blue-600"
              >
                <h3 class="font-medium text-gray-900 text-sm truncate hover:underline">
                  {{ book.title }}
                </h3>
              </a>
              <p class="text-xs text-gray-600 truncate">
                {{ book.author?.name || "Unknown author" }}
              </p>
              <div class="mt-2 flex items-center justify-between text-xs">
                <span class="text-gray-500">FMV: {{ formatPrice(book.value_mid) }}</span>
                <a
                  v-if="book.source_url"
                  :href="book.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  title="View eBay listing"
                >
                  🛒 Listing
                </a>
              </div>

              <!-- Score Card -->
              <div class="mt-3">
                <ScoreCard
                  :book-id="book.id"
                  :investment-grade="book.investment_grade"
                  :strategic-fit="book.strategic_fit"
                  :collection-impact="book.collection_impact"
                  :overall-score="book.overall_score"
                  @recalculate="handleRecalculateScore(book.id)"
                />
              </div>

              <div class="mt-3 flex gap-2">
                <button
                  @click="openAcquireModal(book.id)"
                  class="flex-1 px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                >
                  Acquire
                </button>
                <button
                  @click="openEditModal(book)"
                  class="px-2 py-1 text-gray-600 text-xs hover:bg-gray-100 rounded"
                  title="Edit FMV and details"
                >
                  Edit
                </button>
                <button
                  @click="handleDelete(book.id)"
                  :disabled="deletingBook === book.id"
                  class="px-2 py-1 text-red-600 text-xs hover:bg-red-50 rounded disabled:opacity-50"
                >
                  {{ deletingBook === book.id ? "Deleting..." : "Delete" }}
                </button>
              </div>
              <!-- Analysis Section -->
              <div class="mt-2 flex items-center justify-start gap-3">
                <!-- View Analysis link (visible to all when analysis exists) -->
                <button
                  v-if="book.has_analysis"
                  @click="openAnalysisViewer(book.id)"
                  class="text-xs text-green-700 hover:text-green-900 flex items-center gap-1"
                  title="View analysis"
                >
                  📄 View Analysis
                </button>
                <!-- Analysis job in progress indicator (check both in-memory and API status) -->
                <div
                  v-if="isAnalysisRunning(book.id) || book.analysis_job_status"
                  class="text-xs text-blue-600 flex items-center gap-1"
                >
                  <span class="animate-spin">⏳</span>
                  <span>
                    {{
                      (getJobStatus(book.id)?.status || book.analysis_job_status) === "pending"
                        ? "Queued..."
                        : "Analyzing..."
                    }}
                  </span>
                </div>
                <!-- Analysis job failed indicator -->
                <div
                  v-if="getJobStatus(book.id)?.status === 'failed'"
                  class="text-xs text-red-600 flex items-center gap-1"
                  :title="getJobStatus(book.id)?.error_message || 'Analysis failed'"
                >
                  ❌ Failed - click to retry
                </div>
                <!-- Generate Analysis button (admin only, when no analysis exists and not running) -->
                <button
                  v-if="
                    !book.has_analysis &&
                    authStore.isAdmin &&
                    !isAnalysisRunning(book.id) &&
                    !book.analysis_job_status
                  "
                  @click="handleGenerateAnalysis(book.id)"
                  :disabled="startingAnalysis === book.id"
                  class="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 disabled:opacity-50"
                  title="Generate analysis"
                >
                  <span v-if="startingAnalysis === book.id" class="animate-spin">⏳</span>
                  <span v-else>⚡</span>
                  {{ startingAnalysis === book.id ? "Starting..." : "Generate Analysis" }}
                </button>
                <!-- Regenerate button (admin only, when analysis exists and not running) -->
                <button
                  v-if="
                    book.has_analysis &&
                    authStore.isAdmin &&
                    !isAnalysisRunning(book.id) &&
                    !book.analysis_job_status
                  "
                  @click="handleGenerateAnalysis(book.id)"
                  :disabled="startingAnalysis === book.id"
                  class="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
                  title="Regenerate analysis"
                >
                  <span v-if="startingAnalysis === book.id" class="animate-spin">⏳</span>
                  <span v-else>🔄</span>
                </button>
              </div>

              <!-- Eval Runbook Section (separate row for clarity) -->
              <div class="mt-1 flex items-center justify-start gap-3">
                <!-- View Eval Runbook link -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="openEvalRunbook(book)"
                  class="text-xs text-purple-700 hover:text-purple-900 flex items-center gap-1"
                  title="View eval runbook"
                >
                  📋 Eval Runbook
                </button>
                <!-- Eval runbook job in progress indicator (check both in-memory and API status) -->
                <div
                  v-if="isEvalRunbookRunning(book.id) || book.eval_runbook_job_status"
                  class="text-xs text-purple-600 flex items-center gap-1"
                >
                  <span class="animate-spin">⏳</span>
                  <span>
                    {{
                      (getEvalRunbookJobStatus(book.id)?.status || book.eval_runbook_job_status) ===
                      "pending"
                        ? "Queued..."
                        : "Generating runbook..."
                    }}
                  </span>
                </div>
                <!-- Generate Eval Runbook button (admin only, when no runbook exists and not running) -->
                <button
                  v-if="
                    !book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 disabled:opacity-50"
                  title="Generate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>⚡</span>
                  {{ startingEvalRunbook === book.id ? "Starting..." : "Generate Runbook" }}
                </button>
                <!-- Regenerate Eval Runbook button (admin only, when runbook exists and not running) -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 disabled:opacity-50"
                  title="Regenerate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>🔄</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- IN_TRANSIT Column -->
        <div class="bg-white rounded-lg shadow">
          <div class="p-4 border-b border-gray-200">
            <h2 class="font-semibold text-gray-900 flex items-center gap-2">
              <span class="w-3 h-3 bg-blue-400 rounded-full"></span>
              In Transit
              <span class="ml-auto text-sm text-gray-500">{{ inTransit.length }}</span>
            </h2>
          </div>
          <div class="p-4 space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto">
            <div
              v-for="book in inTransit"
              :key="book.id"
              class="bg-gray-50 rounded-lg p-3 border border-gray-200"
            >
              <a
                :href="`/books/${book.id}`"
                target="_blank"
                rel="noopener noreferrer"
                class="block hover:text-blue-600"
              >
                <h3 class="font-medium text-gray-900 text-sm truncate hover:underline">
                  {{ book.title }}
                </h3>
              </a>
              <p class="text-xs text-gray-600 truncate">
                {{ book.author?.name || "Unknown author" }}
              </p>
              <div class="mt-2 grid grid-cols-2 gap-1 text-xs">
                <span class="text-gray-500">Paid: {{ formatPrice(book.purchase_price) }}</span>
                <span class="text-green-600 font-medium"
                  >{{ formatDiscount(book.discount_pct) }} off</span
                >
              </div>
              <!-- eBay Listing Link -->
              <div v-if="book.source_url" class="mt-1">
                <a
                  :href="book.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
                  title="View eBay listing"
                >
                  🛒 View Listing
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>
              </div>

              <!-- Compact Score Card -->
              <div class="mt-2">
                <ScoreCard :overall-score="book.overall_score" compact />
              </div>

              <div
                v-if="book.estimated_delivery"
                class="mt-1 text-xs text-gray-500 flex items-center gap-2"
              >
                <span>
                  Est. Delivery:
                  {{ formatDateRange(book.estimated_delivery, book.estimated_delivery_end) }}
                </span>
                <button
                  v-if="book.tracking_number && book.tracking_carrier"
                  @click="handleRefreshTracking(book.id)"
                  :disabled="refreshingTracking === book.id"
                  class="p-0.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded disabled:opacity-50"
                  title="Refresh tracking info"
                >
                  <svg
                    class="w-3.5 h-3.5"
                    :class="{ 'animate-spin': refreshingTracking === book.id }"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                </button>
              </div>

              <!-- Tracking Info -->
              <div v-if="book.tracking_url" class="mt-2">
                <a
                  :href="book.tracking_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
                >
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                  <span v-if="book.tracking_carrier">{{ book.tracking_carrier }}:</span>
                  <span>{{ formatTrackingNumber(book.tracking_number) || "Track" }}</span>
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>
              </div>

              <div v-if="book.source_url" class="mt-1">
                <ArchiveStatusBadge
                  :status="book.archive_status"
                  :archived-url="book.source_archived_url"
                  :show-archive-button="true"
                  :archiving="archivingBook === book.id"
                  @archive="handleArchiveSource(book.id)"
                />
              </div>
              <div class="mt-3 flex gap-2">
                <button
                  v-if="!book.tracking_url"
                  @click="openTrackingModal(book)"
                  class="flex-1 px-2 py-1 border border-blue-600 text-blue-600 text-xs rounded hover:bg-blue-50"
                >
                  Add Tracking
                </button>
                <button
                  @click="handleMarkReceived(book.id)"
                  class="flex-1 px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                >
                  Mark Received
                </button>
              </div>
              <!-- Analysis Section -->
              <div class="mt-2 flex items-center justify-start gap-3">
                <!-- View Analysis link (visible to all when analysis exists) -->
                <button
                  v-if="book.has_analysis"
                  @click="openAnalysisViewer(book.id)"
                  class="text-xs text-green-700 hover:text-green-900 flex items-center gap-1"
                  title="View analysis"
                >
                  📄 View Analysis
                </button>
                <!-- Analysis job in progress indicator -->
                <div
                  v-if="isAnalysisRunning(book.id) || book.analysis_job_status"
                  class="text-xs text-blue-600 flex items-center gap-1"
                >
                  <span class="animate-spin">⏳</span>
                  <span>
                    {{
                      (getJobStatus(book.id)?.status || book.analysis_job_status) === "pending"
                        ? "Queued..."
                        : "Analyzing..."
                    }}
                  </span>
                </div>
                <!-- Analysis job failed indicator -->
                <div
                  v-if="getJobStatus(book.id)?.status === 'failed'"
                  class="text-xs text-red-600 flex items-center gap-1"
                  :title="getJobStatus(book.id)?.error_message || 'Analysis failed'"
                >
                  ❌ Failed - click to retry
                </div>
                <!-- Generate Analysis button (admin only, when no analysis exists and not running) -->
                <button
                  v-if="
                    !book.has_analysis &&
                    authStore.isAdmin &&
                    !isAnalysisRunning(book.id) &&
                    !book.analysis_job_status
                  "
                  @click="handleGenerateAnalysis(book.id)"
                  :disabled="startingAnalysis === book.id"
                  class="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 disabled:opacity-50"
                  title="Generate analysis"
                >
                  <span v-if="startingAnalysis === book.id" class="animate-spin">⏳</span>
                  <span v-else>⚡</span>
                  {{ startingAnalysis === book.id ? "Starting..." : "Generate Analysis" }}
                </button>
                <!-- Regenerate button (admin only, when analysis exists and not running) -->
                <button
                  v-if="
                    book.has_analysis &&
                    authStore.isAdmin &&
                    !isAnalysisRunning(book.id) &&
                    !book.analysis_job_status
                  "
                  @click="handleGenerateAnalysis(book.id)"
                  :disabled="startingAnalysis === book.id"
                  class="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
                  title="Regenerate analysis"
                >
                  <span v-if="startingAnalysis === book.id" class="animate-spin">⏳</span>
                  <span v-else>🔄</span>
                </button>
              </div>

              <!-- Eval Runbook Section -->
              <div class="mt-1 flex items-center justify-start gap-3">
                <!-- View Eval Runbook link -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="openEvalRunbook(book)"
                  class="text-xs text-purple-700 hover:text-purple-900 flex items-center gap-1"
                  title="View eval runbook"
                >
                  📋 Eval Runbook
                </button>
                <!-- Eval runbook job in progress indicator -->
                <div
                  v-if="isEvalRunbookRunning(book.id) || book.eval_runbook_job_status"
                  class="text-xs text-purple-600 flex items-center gap-1"
                >
                  <span class="animate-spin">⏳</span>
                  <span>
                    {{
                      (getEvalRunbookJobStatus(book.id)?.status || book.eval_runbook_job_status) ===
                      "pending"
                        ? "Queued..."
                        : "Generating runbook..."
                    }}
                  </span>
                </div>
                <!-- Generate Eval Runbook button (admin only) -->
                <button
                  v-if="
                    !book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 disabled:opacity-50"
                  title="Generate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>⚡</span>
                  {{ startingEvalRunbook === book.id ? "Starting..." : "Generate Runbook" }}
                </button>
                <!-- Regenerate Eval Runbook button (admin only) -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 disabled:opacity-50"
                  title="Regenerate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>🔄</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- RECEIVED Column -->
        <div class="bg-white rounded-lg shadow">
          <div class="p-4 border-b border-gray-200">
            <h2 class="font-semibold text-gray-900 flex items-center gap-2">
              <span class="w-3 h-3 bg-green-400 rounded-full"></span>
              Received (30d)
              <span class="ml-auto text-sm text-gray-500">{{ received.length }}</span>
            </h2>
          </div>
          <div class="p-4 space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto">
            <div
              v-for="book in received"
              :key="book.id"
              class="bg-gray-50 rounded-lg p-3 border border-gray-200"
            >
              <a
                :href="`/books/${book.id}`"
                target="_blank"
                rel="noopener noreferrer"
                class="block hover:text-blue-600"
              >
                <h3 class="font-medium text-gray-900 text-sm truncate hover:underline">
                  {{ book.title }}
                </h3>
              </a>
              <p class="text-xs text-gray-600 truncate">
                {{ book.author?.name || "Unknown author" }}
              </p>
              <div class="mt-2 grid grid-cols-2 gap-1 text-xs">
                <span class="text-gray-500">Paid: {{ formatPrice(book.purchase_price) }}</span>
                <span class="text-green-600 font-medium"
                  >{{ formatDiscount(book.discount_pct) }} off</span
                >
              </div>
              <!-- eBay Listing Link -->
              <div v-if="book.source_url" class="mt-1">
                <a
                  :href="book.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
                  title="View eBay listing"
                >
                  🛒 View Listing
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>
              </div>

              <!-- Compact Score Card -->
              <div class="mt-2">
                <ScoreCard :overall-score="book.overall_score" compact />
              </div>
              <!-- Analysis Section -->
              <div class="mt-2 flex items-center justify-start gap-3">
                <!-- View Analysis link (visible to all when analysis exists) -->
                <button
                  v-if="book.has_analysis"
                  @click="openAnalysisViewer(book.id)"
                  class="text-xs text-green-700 hover:text-green-900 flex items-center gap-1"
                  title="View analysis"
                >
                  📄 View Analysis
                </button>
                <!-- Analysis job in progress indicator -->
                <div
                  v-if="isAnalysisRunning(book.id) || book.analysis_job_status"
                  class="text-xs text-blue-600 flex items-center gap-1"
                >
                  <span class="animate-spin">⏳</span>
                  <span>
                    {{
                      (getJobStatus(book.id)?.status || book.analysis_job_status) === "pending"
                        ? "Queued..."
                        : "Analyzing..."
                    }}
                  </span>
                </div>
                <!-- Analysis job failed indicator -->
                <div
                  v-if="getJobStatus(book.id)?.status === 'failed'"
                  class="text-xs text-red-600 flex items-center gap-1"
                  :title="getJobStatus(book.id)?.error_message || 'Analysis failed'"
                >
                  ❌ Failed - click to retry
                </div>
                <!-- Generate Analysis button (admin only, when no analysis exists and not running) -->
                <button
                  v-if="
                    !book.has_analysis &&
                    authStore.isAdmin &&
                    !isAnalysisRunning(book.id) &&
                    !book.analysis_job_status
                  "
                  @click="handleGenerateAnalysis(book.id)"
                  :disabled="startingAnalysis === book.id"
                  class="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 disabled:opacity-50"
                  title="Generate analysis"
                >
                  <span v-if="startingAnalysis === book.id" class="animate-spin">⏳</span>
                  <span v-else>⚡</span>
                  {{ startingAnalysis === book.id ? "Starting..." : "Generate Analysis" }}
                </button>
                <!-- Regenerate button (admin only, when analysis exists and not running) -->
                <button
                  v-if="
                    book.has_analysis &&
                    authStore.isAdmin &&
                    !isAnalysisRunning(book.id) &&
                    !book.analysis_job_status
                  "
                  @click="handleGenerateAnalysis(book.id)"
                  :disabled="startingAnalysis === book.id"
                  class="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
                  title="Regenerate analysis"
                >
                  <span v-if="startingAnalysis === book.id" class="animate-spin">⏳</span>
                  <span v-else>🔄</span>
                </button>
              </div>

              <!-- Eval Runbook Section -->
              <div class="mt-1 flex items-center justify-start gap-3">
                <!-- View Eval Runbook link -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="openEvalRunbook(book)"
                  class="text-xs text-purple-700 hover:text-purple-900 flex items-center gap-1"
                  title="View eval runbook"
                >
                  📋 Eval Runbook
                </button>
                <!-- Eval runbook job in progress indicator -->
                <div
                  v-if="isEvalRunbookRunning(book.id) || book.eval_runbook_job_status"
                  class="text-xs text-purple-600 flex items-center gap-1"
                >
                  <span class="animate-spin">⏳</span>
                  <span>
                    {{
                      (getEvalRunbookJobStatus(book.id)?.status || book.eval_runbook_job_status) ===
                      "pending"
                        ? "Queued..."
                        : "Generating runbook..."
                    }}
                  </span>
                </div>
                <!-- Generate Eval Runbook button (admin only) -->
                <button
                  v-if="
                    !book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 disabled:opacity-50"
                  title="Generate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>⚡</span>
                  {{ startingEvalRunbook === book.id ? "Starting..." : "Generate Runbook" }}
                </button>
                <!-- Regenerate Eval Runbook button (admin only) -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 disabled:opacity-50"
                  title="Regenerate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>🔄</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Acquire Modal -->
    <AcquireModal
      v-if="showAcquireModal && selectedBook"
      :book-id="selectedBook.id"
      :book-title="selectedBook.title"
      :value-mid="selectedBook.value_mid"
      @close="closeAcquireModal"
      @acquired="closeAcquireModal"
    />

    <!-- Add to Watchlist Modal -->
    <AddToWatchlistModal
      v-if="showWatchlistModal"
      @close="closeWatchlistModal"
      @added="handleWatchlistAdded"
    />

    <!-- Import from eBay Modal -->
    <ImportListingModal
      v-if="showImportModal"
      @close="closeImportModal"
      @added="handleImportAdded"
    />

    <!-- Edit Watchlist Modal -->
    <EditWatchlistModal
      v-if="showEditModal && editingBook"
      :book="editingBook"
      @close="closeEditModal"
      @updated="handleEditUpdated"
    />

    <!-- Analysis Viewer -->
    <!-- :key forces remount when bookId changes, ensuring fresh data load -->
    <AnalysisViewer
      v-if="analysisBookId"
      :key="analysisBookId"
      :book-id="analysisBookId"
      :visible="showAnalysisViewer"
      @close="closeAnalysisViewer"
    />

    <!-- Add Tracking Modal -->
    <AddTrackingModal
      v-if="showTrackingModal && trackingBook"
      :book-id="trackingBook.id"
      :book-title="trackingBook.title"
      @close="closeTrackingModal"
      @added="handleTrackingAdded"
    />

    <!-- Eval Runbook Modal -->
    <EvalRunbookModal
      v-if="showEvalRunbook && evalRunbookBook"
      :book-id="evalRunbookBook.id"
      :book-title="evalRunbookBook.title"
      @close="closeEvalRunbook"
    />
  </div>
</template>
