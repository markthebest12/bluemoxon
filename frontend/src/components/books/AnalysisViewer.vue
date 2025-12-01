<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { api } from "@/services/api";

const props = defineProps<{
  bookId: number;
  visible: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const analysis = ref<string | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

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
    }
  }
);

async function loadAnalysis() {
  try {
    const response = await api.get(`/books/${props.bookId}/analysis/raw`);
    analysis.value = response.data;
  } catch (e: any) {
    if (e.response?.status === 404) {
      error.value = "No analysis available for this book.";
    } else {
      error.value = "Failed to load analysis.";
    }
  } finally {
    loading.value = false;
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
            <h2 class="text-xl font-semibold text-gray-800">Book Analysis</h2>
            <button @click="emit('close')" class="text-gray-500 hover:text-gray-700">
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

          <!-- Content -->
          <div class="flex-1 overflow-y-auto p-6">
            <!-- Loading -->
            <div v-if="loading" class="text-center py-12">
              <p class="text-gray-500">Loading analysis...</p>
            </div>

            <!-- Error -->
            <div v-else-if="error" class="text-center py-12">
              <p class="text-gray-500">{{ error }}</p>
            </div>

            <!-- Analysis content -->
            <article
              v-else
              class="prose prose-sm max-w-none text-gray-700"
              v-html="formattedAnalysis"
            />
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
