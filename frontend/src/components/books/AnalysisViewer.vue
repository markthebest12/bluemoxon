<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { api } from "@/services/api";
import { useBooksStore } from "@/stores/books";
import { useAuthStore } from "@/stores/auth";

const props = defineProps<{
  bookId: number;
  visible: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const booksStore = useBooksStore();
const authStore = useAuthStore();

const analysis = ref<string | null>(null);
const editedAnalysis = ref<string>("");
const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);
const editMode = ref(false);

const canEdit = computed(() => authStore.isEditor);

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
    }
  }
);

async function loadAnalysis() {
  loading.value = true;
  error.value = null;
  try {
    const response = await api.get(`/books/${props.bookId}/analysis/raw`);
    analysis.value = response.data;
    editedAnalysis.value = response.data || "";
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

// Simple markdown to HTML conversion (basic)
const formattedAnalysis = computed(() => {
  if (!analysis.value) return "";

  let html = analysis.value
    // Headers
    .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-6 mb-2 text-gray-800">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold mt-8 mb-3 text-gray-900">$1</h2>')
    .replace(
      /^# (.+)$/gm,
      '<h1 class="text-2xl font-bold mt-8 mb-4 text-gray-900 border-b pb-2">$1</h1>'
    )
    // Bold and italic
    .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // Code blocks
    .replace(
      /```(\w*)\n([\s\S]*?)```/g,
      '<pre class="bg-gray-100 p-4 rounded my-4 overflow-x-auto"><code>$2</code></pre>'
    )
    .replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 rounded text-sm">$1</code>')
    // Lists
    .replace(/^- (.+)$/gm, '<li class="ml-4">$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li class="ml-4">$2</li>')
    // Horizontal rules
    .replace(/^---$/gm, '<hr class="my-6 border-gray-300">')
    // Blockquotes
    .replace(
      /^> (.+)$/gm,
      '<blockquote class="border-l-4 border-gray-300 pl-4 my-4 text-gray-600">$1</blockquote>'
    )
    // Line breaks - convert double newlines to paragraphs
    .replace(/\n\n/g, '</p><p class="my-3">')
    // Single newlines to <br>
    .replace(/\n/g, "<br>");

  // Wrap in paragraph
  html = '<p class="my-3">' + html + "</p>";

  // Clean up empty paragraphs
  html = html.replace(/<p class="my-3"><\/p>/g, "");

  // Wrap list items in ul/ol
  html = html.replace(/(<li class="ml-4">.+?<\/li>)+/g, '<ul class="list-disc my-3">$&</ul>');

  return html;
});

function handleBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) {
    emit("close");
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="slide">
      <div v-if="visible" class="fixed inset-0 z-50 flex" @click="handleBackdropClick">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/50" />

        <!-- Panel -->
        <div
          class="relative ml-auto w-full max-w-3xl bg-white shadow-xl h-full overflow-hidden flex flex-col"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b bg-victorian-cream">
            <h2 class="text-xl font-semibold text-gray-800">
              {{ editMode ? "Edit Analysis" : "Book Analysis" }}
            </h2>
            <div class="flex items-center gap-2">
              <!-- Edit/Save buttons for editors -->
              <template v-if="canEdit && !loading">
                <template v-if="editMode">
                  <button
                    @click="cancelEditing"
                    :disabled="saving"
                    class="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    @click="saveAnalysis"
                    :disabled="saving"
                    class="px-3 py-1.5 text-sm bg-victorian-burgundy text-white rounded hover:bg-victorian-burgundy/90 disabled:opacity-50 flex items-center gap-1"
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
                  <button
                    @click="startEditing"
                    class="px-3 py-1.5 text-sm text-victorian-burgundy hover:text-victorian-burgundy/80 flex items-center gap-1"
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
                </template>
              </template>
              <button @click="emit('close')" class="text-gray-500 hover:text-gray-700 ml-2">
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

          <!-- Content -->
          <div class="flex-1 overflow-y-auto p-6">
            <!-- Loading -->
            <div v-if="loading" class="text-center py-12">
              <p class="text-gray-500">Loading analysis...</p>
            </div>

            <!-- Error -->
            <div v-else-if="error && !editMode" class="text-center py-12">
              <p class="text-gray-500">{{ error }}</p>
              <button
                v-if="canEdit && !analysis"
                @click="startEditing"
                class="mt-4 px-4 py-2 bg-victorian-burgundy text-white rounded hover:bg-victorian-burgundy/90"
              >
                Create Analysis
              </button>
            </div>

            <!-- Edit Mode -->
            <div v-else-if="editMode" class="h-full flex flex-col">
              <div
                v-if="error"
                class="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm"
              >
                {{ error }}
              </div>
              <textarea
                v-model="editedAnalysis"
                class="flex-1 w-full p-4 border border-gray-300 rounded font-mono text-sm resize-none focus:ring-2 focus:ring-victorian-burgundy focus:border-transparent"
                placeholder="Enter markdown analysis..."
              ></textarea>
              <p class="mt-2 text-xs text-gray-500">
                Supports Markdown formatting: # headers, **bold**, *italic*, - lists, etc.
              </p>
            </div>

            <!-- View Mode - Analysis content -->
            <article
              v-else-if="analysis"
              class="prose prose-sm max-w-none text-gray-700"
              v-html="formattedAnalysis"
            />

            <!-- No analysis but can create -->
            <div v-else-if="canEdit" class="text-center py-12">
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
</style>
