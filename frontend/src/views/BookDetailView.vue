<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useBooksStore } from "@/stores/books";
import { api } from "@/services/api";
import BookThumbnail from "@/components/books/BookThumbnail.vue";
import ImageCarousel from "@/components/books/ImageCarousel.vue";
import AnalysisViewer from "@/components/books/AnalysisViewer.vue";

const route = useRoute();
const router = useRouter();
const booksStore = useBooksStore();

// Image gallery state
const images = ref<any[]>([]);
const carouselVisible = ref(false);
const carouselInitialIndex = ref(0);

// Analysis state
const analysisVisible = ref(false);
const hasAnalysis = ref(false);

// Delete confirmation state
const deleteModalVisible = ref(false);
const deleting = ref(false);
const deleteError = ref<string | null>(null);

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

  // Check if analysis exists
  if (booksStore.currentBook?.has_analysis) {
    hasAnalysis.value = true;
  }
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

function openAnalysis() {
  analysisVisible.value = true;
}

function closeAnalysis() {
  analysisVisible.value = false;
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
</script>

<template>
  <div v-if="booksStore.loading" class="text-center py-12">
    <p class="text-gray-500">Loading book details...</p>
  </div>

  <div v-else-if="booksStore.currentBook" class="max-w-5xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex justify-between items-start">
        <RouterLink
          to="/books"
          class="text-moxon-600 hover:text-moxon-800 mb-4 inline-block"
        >
          &larr; Back to Collection
        </RouterLink>
        <div class="flex gap-2">
          <RouterLink
            :to="`/books/${booksStore.currentBook.id}/edit`"
            class="btn-secondary"
          >
            Edit Book
          </RouterLink>
          <button @click="openDeleteModal" class="btn-danger">Delete</button>
        </div>
      </div>
      <h1 class="text-3xl font-bold text-gray-800">
        {{ booksStore.currentBook.title }}
      </h1>
      <p class="text-xl text-gray-600 mt-2">
        {{ booksStore.currentBook.author?.name || "Unknown Author" }}
      </p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Main Content (2 columns) -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Image Gallery -->
        <div class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Images</h2>
          <div v-if="images.length > 0" class="grid grid-cols-4 gap-3">
            <button
              v-for="(img, idx) in images"
              :key="img.id"
              @click="openCarousel(idx)"
              class="aspect-square rounded overflow-hidden hover:ring-2 hover:ring-moxon-500 transition-all"
            >
              <img
                :src="img.thumbnail_url"
                :alt="img.caption || `Image ${idx + 1}`"
                class="w-full h-full object-cover"
              />
            </button>
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
          <h2 class="text-lg font-semibold text-gray-800 mb-4">
            Publication Details
          </h2>
          <dl class="grid grid-cols-2 gap-4">
            <div>
              <dt class="text-sm text-gray-500">Publisher</dt>
              <dd class="font-medium">
                {{ booksStore.currentBook.publisher?.name || "-" }}
                <span
                  v-if="booksStore.currentBook.publisher?.tier"
                  class="text-xs text-moxon-600"
                >
                  ({{ booksStore.currentBook.publisher.tier }})
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
              <dd class="font-medium">{{ booksStore.currentBook.status }}</dd>
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

        <!-- Analysis Button -->
        <div
          v-if="hasAnalysis"
          class="card bg-victorian-cream border-victorian-burgundy/20"
        >
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-lg font-semibold text-gray-800">
                Detailed Analysis
              </h2>
              <p class="text-sm text-gray-600 mt-1">
                View the full Napoleon-style acquisition analysis for this book.
              </p>
            </div>
            <button @click="openAnalysis" class="btn-primary">
              View Analysis
            </button>
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
            <div v-if="booksStore.currentBook.discount_pct">
              <dt class="text-sm text-gray-500">Discount</dt>
              <dd class="font-medium text-green-600">
                {{ booksStore.currentBook.discount_pct }}%
              </dd>
            </div>
            <div v-if="booksStore.currentBook.roi_pct">
              <dt class="text-sm text-gray-500">ROI</dt>
              <dd class="font-medium text-green-600">
                {{ booksStore.currentBook.roi_pct }}%
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

    <!-- Analysis Viewer Modal -->
    <AnalysisViewer
      :book-id="booksStore.currentBook.id"
      :visible="analysisVisible"
      @close="closeAnalysis"
    />

    <!-- Delete Confirmation Modal -->
    <Teleport to="body">
      <div
        v-if="deleteModalVisible"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/50"
          @click="closeDeleteModal"
        ></div>

        <!-- Modal -->
        <div
          class="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6"
        >
          <h3 class="text-xl font-semibold text-gray-800 mb-4">Delete Book</h3>

          <div class="mb-6">
            <p class="text-gray-600 mb-3">
              Are you sure you want to delete this book?
            </p>
            <p class="font-medium text-gray-800 mb-2">
              "{{ booksStore.currentBook.title }}"
            </p>
            <p class="text-sm text-red-600">
              This will permanently delete the book along with all associated
              images ({{ images.length }}) and analysis data.
            </p>
          </div>

          <div
            v-if="deleteError"
            class="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm"
          >
            {{ deleteError }}
          </div>

          <div class="flex justify-end gap-3">
            <button
              @click="closeDeleteModal"
              :disabled="deleting"
              class="btn-secondary"
            >
              Cancel
            </button>
            <button
              @click="confirmDelete"
              :disabled="deleting"
              class="btn-danger"
            >
              {{ deleting ? "Deleting..." : "Delete Book" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
