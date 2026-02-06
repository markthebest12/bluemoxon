<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useBooksStore, type Book } from "@/stores/books";
import { useJobPolling } from "@/composables/useJobPolling";
import { useModelLabels } from "@/composables/useModelLabels";
import { DEFAULT_ANALYSIS_MODEL, type AnalysisModel } from "@/config";
import AnalysisViewer from "@/components/books/AnalysisViewer.vue";
import EvalRunbookModal from "@/components/books/EvalRunbookModal.vue";
import AnalysisIssuesWarning from "@/components/AnalysisIssuesWarning.vue";

const props = defineProps<{
  book: Book;
  isEditor: boolean;
}>();

const booksStore = useBooksStore();

// Model labels from the public API (single source of truth)
const { labels } = useModelLabels();

// Internal state
const analysisVisible = ref(false);
const evalRunbookVisible = ref(false);
const startingAnalysis = ref(false);
const selectedModel = ref<AnalysisModel>(DEFAULT_ANALYSIS_MODEL);

// Model options for the dropdown — derived from the registry labels
const modelOptions = computed(() => {
  // Only show models that can run analysis (opus, sonnet)
  const analysisKeys: AnalysisModel[] = ["opus", "sonnet"];
  return analysisKeys.map((key) => ({
    value: key,
    label: labels.value[key] || key.charAt(0).toUpperCase() + key.slice(1),
  }));
});

// Analysis polling setup
// Note: useJobPolling auto-cleans up via onUnmounted in the composable
const analysisPoller = useJobPolling("analysis");

// Computed for whether analysis exists
const hasAnalysis = computed(() => props.book?.has_analysis ?? false);

// Helper to check if analysis is running via poller
function isAnalysisRunning(): boolean {
  return analysisPoller.isActive.value;
}

// Get current job status from poller
function getJobStatus() {
  return {
    status: analysisPoller.status.value,
    error: analysisPoller.error.value,
  };
}

// Watch for job status changes to start/stop polling
watch(
  () => props.book?.analysis_job_status,
  (newStatus) => {
    if (!props.book) return;
    if (newStatus === "running" || newStatus === "pending") {
      analysisPoller.start(props.book.id);
    } else {
      analysisPoller.stop();
    }
  },
  { immediate: true }
);

// Open analysis viewer
function openAnalysis() {
  analysisVisible.value = true;
}

// Close analysis viewer
function closeAnalysis() {
  analysisVisible.value = false;
}

// Handle generate analysis button click
async function handleGenerateAnalysis() {
  if (!props.book) return;

  startingAnalysis.value = true;
  try {
    await booksStore.generateAnalysisAsync(props.book.id, selectedModel.value);
  } finally {
    startingAnalysis.value = false;
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Eval Runbook Button -->
    <div v-if="book?.has_eval_runbook" class="card card-info">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-gray-800">Eval Runbook</h2>
          <p class="text-sm text-gray-600 mt-1">
            Quick strategic fit scoring and acquisition recommendation.
          </p>
        </div>
        <button class="btn-primary flex items-center gap-2" @click="evalRunbookVisible = true">
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
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 class="text-lg font-semibold text-gray-800">Detailed Analysis</h2>
          <!-- State: Job running or pending -->
          <div
            v-if="
              isAnalysisRunning() ||
              book?.analysis_job_status === 'running' ||
              book?.analysis_job_status === 'pending'
            "
            class="text-sm text-status-running mt-1 flex items-center gap-1"
          >
            <span class="animate-spin">&#8987;</span>
            <span>
              {{
                (getJobStatus()?.status || book?.analysis_job_status) === "pending"
                  ? "Queued..."
                  : "Analyzing..."
              }}
            </span>
          </div>
          <!-- State: Job failed (failed status only comes from poller, not book.analysis_job_status) -->
          <p
            v-else-if="getJobStatus()?.status === 'failed'"
            class="text-sm text-[var(--color-status-error-accent)] mt-1"
          >
            Analysis failed. Please try again.
          </p>
          <!-- State: Has analysis -->
          <p v-else-if="hasAnalysis" class="text-sm text-gray-600 mt-1">
            View the full Napoleon-style acquisition analysis for this book.
          </p>
          <!-- State: No analysis (editor/admin can generate) -->
          <p v-else-if="isEditor" class="text-sm text-gray-600 mt-1">
            Generate a Napoleon-style acquisition analysis for this book.
          </p>
          <!-- State: No analysis (viewer - no action available) -->
          <p v-else class="text-sm text-gray-500 mt-1">No analysis available for this book.</p>
        </div>

        <!-- Action buttons -->
        <div class="flex flex-wrap items-center gap-2">
          <!-- View Analysis button (all users, when analysis exists) -->
          <button
            v-if="hasAnalysis && !isAnalysisRunning() && !book?.analysis_job_status"
            class="btn-primary"
            @click="openAnalysis"
          >
            View Analysis
          </button>
          <AnalysisIssuesWarning :issues="book?.analysis_issues" />

          <!-- Model selector (editor/admin only, when not running) -->
          <select
            v-if="isEditor && !isAnalysisRunning() && !book?.analysis_job_status"
            v-model="selectedModel"
            class="select text-sm w-32 pr-8"
            :disabled="startingAnalysis"
          >
            <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>

          <!-- Generate button (editor/admin, no analysis exists) -->
          <button
            v-if="!hasAnalysis && isEditor && !isAnalysisRunning() && !book?.analysis_job_status"
            :disabled="startingAnalysis"
            class="btn-primary flex items-center gap-1 disabled:opacity-50"
            @click="handleGenerateAnalysis"
          >
            <span v-if="startingAnalysis" class="animate-spin">&#8987;</span>
            <span v-else>&#9889;</span>
            {{ startingAnalysis ? "Starting..." : "Generate Analysis" }}
          </button>

          <!-- Regenerate button (editor/admin, analysis exists) -->
          <button
            v-if="hasAnalysis && isEditor && !isAnalysisRunning() && !book?.analysis_job_status"
            :disabled="startingAnalysis"
            class="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-sm hover:bg-gray-200 disabled:opacity-50 flex items-center gap-1"
            title="Regenerate analysis with selected model"
            @click="handleGenerateAnalysis"
          >
            <span v-if="startingAnalysis" class="animate-spin">&#8987;</span>
            <span v-else>&#128260;</span>
            {{ startingAnalysis ? "Starting..." : "Regenerate" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Eval Runbook Modal -->
    <EvalRunbookModal
      v-if="book"
      :visible="evalRunbookVisible"
      :book-id="book.id"
      :book-title="book.title"
      @close="evalRunbookVisible = false"
    />

    <!-- Analysis Viewer Modal -->
    <AnalysisViewer :book-id="book.id" :visible="analysisVisible" @close="closeAnalysis" />
  </div>
</template>
