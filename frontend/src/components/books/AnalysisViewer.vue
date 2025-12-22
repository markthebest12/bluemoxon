<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { api } from "@/services/api";
import { useBooksStore } from "@/stores/books";
import { useAuthStore } from "@/stores/auth";
import { useJobPolling } from "@/composables/useJobPolling";

const props = defineProps<{
  bookId: number;
  visible: boolean;
}>();

const emit = defineEmits<{
  close: [];
  deleted: [];
}>();

const booksStore = useBooksStore();
const authStore = useAuthStore();

// Analysis generation polling (async generation with status updates)
const analysisPoller = useJobPolling("analysis", {
  onComplete: async () => {
    // Reload analysis content when generation completes
    await loadAnalysis();
    generating.value = false;
  },
  onError: (_bookId, errorMsg) => {
    generateError.value = errorMsg;
    generating.value = false;
  },
});

const analysis = ref<string | null>(null);
const editedAnalysis = ref<string>("");
const extractionStatus = ref<string | null>(null); // "success", "degraded", "failed", or null (legacy)
const generatedAt = ref<string | null>(null); // Analysis generation timestamp
const loading = ref(true);
const saving = ref(false);
const deleting = ref(false);
const error = ref<string | null>(null);
const editMode = ref(false);
const showDeleteConfirm = ref(false);
const showPreview = ref(true);
const showMobileMenu = ref(false);

// Generate controls
const selectedModel = ref<"sonnet" | "opus">("sonnet");
const generating = ref(false);
const generateError = ref<string | null>(null);

const canEdit = computed(() => authStore.isEditor);

// Configure marked for GFM (GitHub Flavored Markdown) with tables
marked.setOptions({
  gfm: true,
  breaks: true,
});

onMounted(async () => {
  await loadAnalysis();
});

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
      // Reset edit mode when closing
      editMode.value = false;
      showDeleteConfirm.value = false;
      showMobileMenu.value = false;
    }
  }
);

async function loadAnalysis() {
  loading.value = true;
  error.value = null;
  extractionStatus.value = null;
  try {
    // Fetch raw markdown for display
    const rawResponse = await api.get(`/books/${props.bookId}/analysis/raw`);
    analysis.value = rawResponse.data;
    editedAnalysis.value = rawResponse.data || "";

    // Fetch metadata for extraction status indicator and generation timestamp
    try {
      const metaResponse = await api.get(`/books/${props.bookId}/analysis`);
      extractionStatus.value = metaResponse.data.extraction_status || null;
      generatedAt.value = metaResponse.data.generated_at || null;
    } catch {
      // Metadata fetch failed, continue without extraction status
    }
  } catch (e: any) {
    if (e.response?.status === 404) {
      // No analysis yet - allow creating one if editor
      analysis.value = null;
      editedAnalysis.value = "";
      if (!canEdit.value) {
        error.value = "No analysis available for this book.";
      }
    } else {
      error.value = "Failed to load analysis.";
    }
  } finally {
    loading.value = false;
  }
}

function startEditing() {
  editedAnalysis.value = analysis.value || "";
  editMode.value = true;
}

function cancelEditing() {
  editedAnalysis.value = analysis.value || "";
  editMode.value = false;
  error.value = null;
}

async function saveAnalysis() {
  if (saving.value) return;

  saving.value = true;
  error.value = null;
  try {
    await booksStore.updateAnalysis(props.bookId, editedAnalysis.value);
    analysis.value = editedAnalysis.value;
    editMode.value = false;
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || "Failed to save analysis.";
  } finally {
    saving.value = false;
  }
}

async function deleteAnalysis() {
  if (deleting.value) return;

  deleting.value = true;
  error.value = null;
  try {
    await api.delete(`/books/${props.bookId}/analysis`);
    analysis.value = null;
    editedAnalysis.value = "";
    showDeleteConfirm.value = false;
    // Update the book's has_analysis flag
    if (booksStore.currentBook) {
      booksStore.currentBook.has_analysis = false;
    }
    emit("deleted");
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || "Failed to delete analysis.";
  } finally {
    deleting.value = false;
  }
}

async function generateAnalysis() {
  if (generating.value || analysisPoller.isActive.value) return;

  generating.value = true;
  generateError.value = null;
  error.value = null;

  try {
    // Use async generation API + polling (not sync which can timeout on large books)
    await booksStore.generateAnalysisAsync(props.bookId, selectedModel.value);
    // Start polling - onComplete callback will reload analysis and set generating=false
    analysisPoller.start(props.bookId);
  } catch (e: any) {
    generateError.value =
      e.response?.data?.detail || e.message || "Failed to start analysis generation.";
    generating.value = false;
  }
  // Note: generating.value stays true until poller's onComplete/onError callback
}

// Strip machine-readable structured data blocks before rendering
// NOTE: Napoleon v2 STRUCTURED-DATA blocks are stripped entirely (machine-only data)
// Also strips empty STRUCTURED DATA SECTION from Napoleon output (AI doesn't fill it)
function stripStructuredData(markdown: string): string {
  if (!markdown) return markdown;
  let result = markdown;
  // Remove Napoleon v2 structured data block (for machine parsing only)
  result = result.replace(/---STRUCTURED-DATA---[\s\S]*?---END-STRUCTURED-DATA---\s*/gi, "");
  // Remove empty STRUCTURED DATA SECTION (header + empty code block + hr)
  // Matches: ## STRUCTURED DATA SECTION\n\n```\n```\n\n---
  result = result.replace(/##\s*STRUCTURED DATA SECTION\s*\n+```\s*```\s*\n+---\s*\n*/gi, "");
  return result;
}

// Pre-process markdown to wrap legacy YAML summary in styled container
// NOTE: This only applies to legacy YAML format (## SUMMARY), not Napoleon v2
function preprocessYamlSummary(markdown: string): string {
  if (!markdown) return markdown;

  // Match YAML block: ## SUMMARY followed by --- ... ---
  const pattern = /(##\s*SUMMARY\s*\n)(---\n)([\s\S]*?)(---)/i;
  const match = markdown.match(pattern);

  if (!match) return markdown;

  // Extract the YAML content and format it as a code block
  const yamlContent = match[3].trim();

  // Replace the original block with a styled version
  return markdown.replace(
    pattern,
    `$1<div class="yaml-summary"><pre><code>${yamlContent}</code></pre></div>\n\n`
  );
}

// Render markdown to sanitized HTML
function renderMarkdown(markdown: string): string {
  if (!markdown) return "";
  // First strip Napoleon v2 structured data blocks (machine-only data)
  const stripped = stripStructuredData(markdown);
  // Then style legacy YAML summary block (if present)
  const processed = preprocessYamlSummary(stripped);
  const rawHtml = marked(processed) as string;
  return DOMPurify.sanitize(rawHtml);
}

// Computed property for rendered analysis (view mode)
const formattedAnalysis = computed(() => {
  if (!analysis.value) return "";
  return renderMarkdown(analysis.value);
});

// Computed property for live preview (edit mode)
const previewHtml = computed(() => {
  if (!editedAnalysis.value)
    return '<p class="text-gray-400 italic">Start typing to see preview...</p>';
  return renderMarkdown(editedAnalysis.value);
});

function handleBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) {
    emit("close");
  }
}

// Keyboard shortcuts
function handleKeydown(e: KeyboardEvent) {
  if (editMode.value && e.metaKey && e.key === "s") {
    e.preventDefault();
    saveAnalysis();
  }
  if (e.key === "Escape") {
    if (showDeleteConfirm.value) {
      showDeleteConfirm.value = false;
    } else if (editMode.value) {
      cancelEditing();
    } else {
      emit("close");
    }
  }
}

// Print function - adds class to hide background page during print
function printAnalysis() {
  document.body.classList.add("printing-analysis");
  window.print();
  // Remove class after print dialog closes
  setTimeout(() => {
    document.body.classList.remove("printing-analysis");
  }, 100);
}

// Format timestamp in Pacific timezone for display
function formatPacificTime(isoString: string): string {
  const date = new Date(isoString);
  const formatted = date.toLocaleString("en-US", {
    timeZone: "America/Los_Angeles",
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  return `${formatted} Pacific`;
}
</script>

<template>
  <Teleport to="body">
    <Transition name="slide">
      <div
        v-if="visible"
        class="fixed inset-0 z-50 flex"
        data-analysis-viewer
        @click="handleBackdropClick"
        @keydown="handleKeydown"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/50" />

        <!-- Panel - wider in edit mode -->
        <div
          :class="[
            'relative ml-auto bg-white shadow-xl h-full overflow-hidden flex flex-col transition-all duration-300',
            editMode ? 'w-full max-w-6xl' : 'w-full max-w-3xl',
          ]"
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b bg-victorian-cream"
          >
            <h2 class="text-lg sm:text-xl font-semibold text-gray-800 truncate mr-2">
              {{ editMode ? "Edit Analysis" : "Book Analysis" }}
            </h2>
            <div class="flex items-center gap-1 sm:gap-2 flex-shrink-0">
              <!-- Edit mode controls - hidden on mobile except save/cancel -->
              <template v-if="canEdit && !loading">
                <template v-if="editMode">
                  <!-- Preview toggle - hidden on mobile -->
                  <button
                    @click="showPreview = !showPreview"
                    :class="[
                      'hidden sm:flex px-3 py-1.5 text-sm rounded items-center gap-1',
                      showPreview
                        ? 'bg-gray-200 text-gray-700'
                        : 'text-gray-500 hover:text-gray-700',
                    ]"
                    title="Toggle preview"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                      />
                    </svg>
                    Preview
                  </button>
                  <button
                    @click="cancelEditing"
                    :disabled="saving"
                    class="px-2 sm:px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    @click="saveAnalysis"
                    :disabled="saving"
                    class="px-2 sm:px-3 py-1.5 text-sm bg-victorian-burgundy text-white rounded hover:bg-victorian-burgundy/90 disabled:opacity-50 flex items-center gap-1"
                  >
                    <svg v-if="saving" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                      ></circle>
                      <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    {{ saving ? "Saving..." : "Save" }}
                  </button>
                </template>
                <template v-else>
                  <!-- Generate controls (admin only, when not in edit mode) - hidden on mobile -->
                  <div class="hidden sm:flex items-center gap-2">
                    <select
                      v-model="selectedModel"
                      class="text-sm border border-gray-300 rounded px-2 py-1"
                      :disabled="generating"
                    >
                      <option value="sonnet">Sonnet 4.5</option>
                      <option value="opus">Opus 4.5</option>
                    </select>
                    <button
                      @click="generateAnalysis"
                      :disabled="generating"
                      class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
                    >
                      <span v-if="generating" class="flex items-center gap-2">
                        <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                          <circle
                            class="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            stroke-width="4"
                            fill="none"
                          />
                          <path
                            class="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                          />
                        </svg>
                        Generating...
                      </span>
                      <span v-else>{{ analysis ? "🔄 Regenerate" : "⚡ Generate" }}</span>
                    </button>
                  </div>
                  <button
                    @click="startEditing"
                    class="hidden sm:flex px-3 py-1.5 text-sm text-victorian-burgundy hover:text-victorian-burgundy/80 items-center gap-1"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                    Edit
                  </button>
                  <!-- Delete button (only if analysis exists) - hidden on mobile -->
                  <button
                    v-if="analysis"
                    @click="showDeleteConfirm = true"
                    class="hidden sm:flex px-3 py-1.5 text-sm text-red-600 hover:text-red-700 items-center gap-1"
                    title="Delete analysis"
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
                  <!-- Mobile actions menu (3-dot menu) - visible only on mobile -->
                  <div class="relative sm:hidden">
                    <button
                      @click="showMobileMenu = !showMobileMenu"
                      class="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full"
                      title="More actions"
                    >
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
                        />
                      </svg>
                    </button>
                    <!-- Dropdown menu -->
                    <div
                      v-if="showMobileMenu"
                      class="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border py-1 z-20"
                    >
                      <button
                        @click="
                          startEditing();
                          showMobileMenu = false;
                        "
                        class="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                          />
                        </svg>
                        Edit
                      </button>
                      <button
                        @click="
                          generateAnalysis();
                          showMobileMenu = false;
                        "
                        :disabled="generating"
                        class="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2 disabled:opacity-50"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M13 10V3L4 14h7v7l9-11h-7z"
                          />
                        </svg>
                        {{ analysis ? "Regenerate" : "Generate" }}
                      </button>
                      <button
                        v-if="analysis"
                        @click="
                          showDeleteConfirm = true;
                          showMobileMenu = false;
                        "
                        class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                        Delete
                      </button>
                    </div>
                    <!-- Backdrop to close menu -->
                    <div
                      v-if="showMobileMenu"
                      class="fixed inset-0 z-10"
                      @click="showMobileMenu = false"
                    />
                  </div>
                </template>
              </template>
              <!-- Print button - visible in view mode when analysis exists -->
              <button
                v-if="!editMode && analysis"
                @click="printAnalysis"
                class="no-print p-2 text-victorian-ink-muted hover:text-victorian-ink-dark hover:bg-victorian-paper-cream rounded-full transition-colors"
                title="Print analysis"
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
              <!-- Close button - always visible and prominent -->
              <button
                @click="emit('close')"
                class="no-print p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors ml-1 sm:ml-2"
                title="Close"
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

          <!-- Extraction status warning banner -->
          <div
            v-if="extractionStatus === 'degraded'"
            class="px-4 sm:px-6 py-2 bg-amber-50 border-b border-amber-200 text-amber-800 text-sm flex items-center gap-2"
          >
            <svg
              class="w-4 h-4 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <span>
              <strong>Degraded extraction:</strong> Structured data was extracted using fallback
              parsing due to AI service throttling. Values may be less accurate.
            </span>
          </div>

          <!-- Delete confirmation modal -->
          <div
            v-if="showDeleteConfirm"
            class="absolute inset-0 z-10 flex items-center justify-center bg-black/50"
          >
            <div class="bg-white rounded-lg shadow-xl p-6 max-w-md mx-4">
              <h3 class="text-lg font-semibold text-gray-900 mb-2">Delete Analysis?</h3>
              <p class="text-gray-600 mb-4">
                This will permanently delete the analysis for this book. This action cannot be
                undone.
              </p>
              <div
                v-if="error"
                class="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm"
              >
                {{ error }}
              </div>
              <div class="flex justify-end gap-3">
                <button
                  @click="showDeleteConfirm = false"
                  :disabled="deleting"
                  class="px-4 py-2 text-gray-600 hover:text-gray-800 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  @click="deleteAnalysis"
                  :disabled="deleting"
                  class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
                >
                  <svg v-if="deleting" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle
                      class="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      stroke-width="4"
                    ></circle>
                    <path
                      class="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  {{ deleting ? "Deleting..." : "Delete" }}
                </button>
              </div>
            </div>
          </div>

          <!-- Content -->
          <div class="flex-1 overflow-hidden">
            <!-- Loading -->
            <div v-if="loading" class="h-full flex items-center justify-center">
              <p class="text-gray-500">Loading analysis...</p>
            </div>

            <!-- Error (not in edit mode) -->
            <div
              v-else-if="error && !editMode"
              class="h-full flex flex-col items-center justify-center p-6"
            >
              <p class="text-gray-500">{{ error }}</p>
              <button
                v-if="canEdit && !analysis"
                @click="startEditing"
                class="mt-4 px-4 py-2 bg-victorian-burgundy text-white rounded hover:bg-victorian-burgundy/90"
              >
                Create Analysis
              </button>
            </div>

            <!-- Edit Mode - Split pane -->
            <div v-else-if="editMode" class="h-full flex flex-col">
              <div
                v-if="error"
                class="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm"
              >
                {{ error }}
              </div>
              <div
                v-if="generateError"
                class="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm"
              >
                {{ generateError }}
              </div>
              <div class="flex-1 flex overflow-hidden">
                <!-- Editor pane -->
                <div :class="['flex flex-col', showPreview ? 'w-1/2 border-r' : 'w-full']">
                  <div class="px-4 py-2 bg-gray-50 border-b text-xs text-gray-500 font-medium">
                    MARKDOWN
                  </div>
                  <textarea
                    v-model="editedAnalysis"
                    class="flex-1 w-full p-4 font-mono text-sm resize-none focus:outline-none"
                    placeholder="Enter markdown analysis...

# Executive Summary
Brief overview of the item...

## Condition Assessment
Detailed condition notes...

## Market Analysis
| Comparable | Price | Source |
|------------|-------|--------|
| Similar item | $500 | AbeBooks |

## Recommendations
- Point 1
- Point 2"
                  ></textarea>
                </div>
                <!-- Preview pane -->
                <div v-if="showPreview" class="w-1/2 flex flex-col overflow-hidden">
                  <div class="px-4 py-2 bg-gray-50 border-b text-xs text-gray-500 font-medium">
                    PREVIEW
                  </div>
                  <div class="flex-1 overflow-y-auto p-6">
                    <article class="analysis-content" v-html="previewHtml" />
                  </div>
                </div>
              </div>
              <div class="px-4 py-2 bg-gray-50 border-t text-xs text-gray-500 flex justify-between">
                <span
                  >Supports GitHub Flavored Markdown: # headers, **bold**, *italic*, - lists, |
                  tables |</span
                >
                <span class="text-gray-400">⌘S to save • Esc to cancel</span>
              </div>
            </div>

            <!-- View Mode - Analysis content -->
            <div v-else-if="analysis" class="h-full overflow-y-auto p-6">
              <article class="analysis-content" v-html="formattedAnalysis" />
              <!-- Generation timestamp footer -->
              <p
                v-if="generatedAt"
                class="mt-8 pt-4 border-t border-gray-200 text-sm text-gray-500 italic"
              >
                Analysis generated: {{ formatPacificTime(generatedAt) }}
              </p>
            </div>

            <!-- No analysis but can create -->
            <div v-else-if="canEdit" class="h-full flex flex-col items-center justify-center p-6">
              <p class="text-gray-500 mb-4">No analysis available for this book.</p>
              <button
                @click="startEditing"
                class="px-4 py-2 bg-victorian-burgundy text-white rounded hover:bg-victorian-burgundy/90"
              >
                Create Analysis
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

.slide-enter-active > div:first-child,
.slide-leave-active > div:first-child {
  transition: opacity 0.3s ease;
}

.slide-enter-from > div:first-child,
.slide-leave-to > div:first-child {
  opacity: 0;
}

/* Analysis content styling - applied to rendered markdown */
.analysis-content {
  @apply text-gray-700 leading-relaxed;
}

.analysis-content :deep(h1) {
  @apply text-2xl font-bold mt-8 mb-4 text-gray-900 border-b pb-2;
}

.analysis-content :deep(h2) {
  @apply text-xl font-bold mt-8 mb-3 text-gray-900;
}

.analysis-content :deep(h3) {
  @apply text-lg font-semibold mt-6 mb-2 text-gray-800;
}

.analysis-content :deep(h4) {
  @apply text-base font-semibold mt-4 mb-2 text-gray-800;
}

.analysis-content :deep(p) {
  @apply my-3;
}

.analysis-content :deep(ul) {
  @apply list-disc ml-6 my-3;
}

.analysis-content :deep(ol) {
  @apply list-decimal ml-6 my-3;
}

.analysis-content :deep(li) {
  @apply my-1;
}

.analysis-content :deep(strong) {
  @apply font-semibold;
}

.analysis-content :deep(em) {
  @apply italic;
}

.analysis-content :deep(code) {
  @apply bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono;
}

.analysis-content :deep(pre) {
  @apply bg-gray-100 p-4 rounded my-4 overflow-x-auto;
}

.analysis-content :deep(pre code) {
  @apply bg-transparent p-0;
}

.analysis-content :deep(blockquote) {
  @apply border-l-4 border-gray-300 pl-4 my-4 text-gray-600 italic;
}

.analysis-content :deep(hr) {
  @apply my-6 border-gray-300;
}

/* YAML summary block styling - smaller, monospace, subtle background */
.analysis-content :deep(.yaml-summary) {
  @apply mb-6 rounded-lg bg-gray-50 border border-gray-200;
}

.analysis-content :deep(.yaml-summary pre) {
  @apply m-0 p-3 bg-transparent text-xs leading-relaxed;
}

.analysis-content :deep(.yaml-summary code) {
  @apply bg-transparent p-0 text-gray-600 text-xs;
}

.analysis-content :deep(a) {
  @apply text-victorian-burgundy hover:underline;
}

/* Table styling - critical for Napoleon-style analyses */
.analysis-content :deep(table) {
  @apply w-full my-4 border-collapse text-sm;
}

.analysis-content :deep(thead) {
  @apply bg-gray-100;
}

.analysis-content :deep(th) {
  @apply px-3 py-2 text-left font-semibold text-gray-700 border border-gray-300;
}

.analysis-content :deep(td) {
  @apply px-3 py-2 border border-gray-300;
}

.analysis-content :deep(tr:nth-child(even)) {
  @apply bg-gray-50;
}

/* Print styles */
@media print {
  /* Make the modal container static and full width */
  .fixed {
    position: static !important;
  }

  /* Hide the backdrop overlay */
  .absolute {
    display: none !important;
  }

  /* Make panel full width for print */
  .relative {
    position: static !important;
    max-width: none !important;
    width: 100% !important;
    height: auto !important;
    overflow: visible !important;
    box-shadow: none !important;
  }

  /* Hide header bar (close button, edit buttons) */
  .border-b.bg-victorian-cream {
    display: none !important;
  }

  /* Make content area printable */
  .overflow-y-auto {
    overflow: visible !important;
    height: auto !important;
  }

  /* Ensure analysis content prints well */
  .analysis-content {
    max-width: 100% !important;
    padding: 0 !important;
  }

  .analysis-content :deep(table) {
    page-break-inside: avoid;
  }

  .analysis-content :deep(h1),
  .analysis-content :deep(h2),
  .analysis-content :deep(h3) {
    page-break-after: avoid;
  }
}
</style>
