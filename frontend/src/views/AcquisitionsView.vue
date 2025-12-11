<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useAcquisitionsStore } from "@/stores/acquisitions";
import { useBooksStore } from "@/stores/books";
import { useAuthStore } from "@/stores/auth";
import { storeToRefs } from "pinia";
import AcquireModal from "@/components/AcquireModal.vue";
import AddToWatchlistModal from "@/components/AddToWatchlistModal.vue";

const acquisitionsStore = useAcquisitionsStore();
const booksStore = useBooksStore();
const authStore = useAuthStore();
const { evaluating, inTransit, received, loading, error } = storeToRefs(acquisitionsStore);

const showAcquireModal = ref(false);
const selectedBookId = ref<number | null>(null);
const showWatchlistModal = ref(false);

const selectedBook = computed(() => {
  if (!selectedBookId.value) return null;
  return evaluating.value.find((b) => b.id === selectedBookId.value);
});

onMounted(() => {
  acquisitionsStore.fetchAll();
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

function handleWatchlistAdded() {
  showWatchlistModal.value = false;
  acquisitionsStore.fetchAll();
}

function formatPrice(price?: number | null): string {
  if (price == null || typeof price !== "number") return "-";
  return `$${price.toFixed(2)}`;
}

function formatDiscount(discount?: number | null): string {
  if (discount == null || typeof discount !== "number") return "-";
  return `${discount.toFixed(0)}%`;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

async function handleMarkReceived(bookId: number) {
  await acquisitionsStore.markReceived(bookId);
}

async function handleDelete(bookId: number) {
  if (confirm("Delete this item from watchlist?")) {
    await acquisitionsStore.deleteEvaluating(bookId);
  }
}

const generatingAnalysis = ref<number | null>(null);

async function handleGenerateAnalysis(bookId: number) {
  if (generatingAnalysis.value) return;

  generatingAnalysis.value = bookId;
  try {
    await booksStore.generateAnalysis(bookId);
    // Refresh to show has_analysis = true
    await acquisitionsStore.fetchAll();
  } catch (e: any) {
    console.error("Failed to generate analysis:", e);
  } finally {
    generatingAnalysis.value = null;
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6">
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Acquisitions</h1>
        <p class="text-gray-600">Track books from watchlist through delivery</p>
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
              <h3 class="font-medium text-gray-900 text-sm truncate">{{ book.title }}</h3>
              <p class="text-xs text-gray-600 truncate">
                {{ book.author?.name || "Unknown author" }}
              </p>
              <div class="mt-2 flex items-center justify-between text-xs">
                <span class="text-gray-500">FMV: {{ formatPrice(book.value_mid) }}</span>
              </div>
              <div class="mt-3 flex gap-2">
                <button
                  @click="openAcquireModal(book.id)"
                  class="flex-1 px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                >
                  Acquire
                </button>
                <button
                  @click="handleDelete(book.id)"
                  class="px-2 py-1 text-red-600 text-xs hover:bg-red-50 rounded"
                >
                  Delete
                </button>
              </div>
              <div v-if="authStore.isAdmin" class="mt-2">
                <button
                  @click="handleGenerateAnalysis(book.id)"
                  :disabled="generatingAnalysis === book.id"
                  class="w-full text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
                >
                  <span v-if="generatingAnalysis === book.id">Generating...</span>
                  <span v-else>{{ book.has_analysis ? "🔄" : "⚡" }} Analysis</span>
                </button>
              </div>
            </div>

            <!-- Add Item Button -->
            <button
              data-testid="add-to-watchlist"
              @click="openWatchlistModal"
              class="block w-full p-3 border-2 border-dashed border-gray-300 rounded-lg text-center text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600"
            >
              + Add to Watchlist
            </button>
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
              <h3 class="font-medium text-gray-900 text-sm truncate">{{ book.title }}</h3>
              <p class="text-xs text-gray-600 truncate">
                {{ book.author?.name || "Unknown author" }}
              </p>
              <div class="mt-2 grid grid-cols-2 gap-1 text-xs">
                <span class="text-gray-500">Paid: {{ formatPrice(book.purchase_price) }}</span>
                <span class="text-green-600 font-medium"
                  >{{ formatDiscount(book.discount_pct) }} off</span
                >
              </div>
              <div v-if="book.estimated_delivery" class="mt-1 text-xs text-gray-500">
                Due: {{ formatDate(book.estimated_delivery) }}
              </div>
              <div class="mt-3">
                <button
                  @click="handleMarkReceived(book.id)"
                  class="w-full px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                >
                  Mark Received
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
            <router-link
              v-for="book in received"
              :key="book.id"
              :to="`/books/${book.id}`"
              class="block bg-gray-50 rounded-lg p-3 border border-gray-200 hover:border-green-300 transition-colors"
            >
              <h3 class="font-medium text-gray-900 text-sm truncate">{{ book.title }}</h3>
              <p class="text-xs text-gray-600 truncate">
                {{ book.author?.name || "Unknown author" }}
              </p>
              <div class="mt-2 grid grid-cols-2 gap-1 text-xs">
                <span class="text-gray-500">Paid: {{ formatPrice(book.purchase_price) }}</span>
                <span class="text-green-600 font-medium"
                  >{{ formatDiscount(book.discount_pct) }} off</span
                >
              </div>
            </router-link>
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
  </div>
</template>
