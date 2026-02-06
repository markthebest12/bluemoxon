<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useBooksStore } from "@/stores/books";
import { useAuthStore } from "@/stores/auth";
import { api } from "@/services/api";
import { handleApiError } from "@/utils/errorHandler";
import { type BookImage } from "@/types/books";
import { invalidateDashboardCache } from "@/stores/dashboard";
import ImageCarousel from "@/components/books/ImageCarousel.vue";

// Child components
import BookActionsBar from "@/components/book-detail/BookActionsBar.vue";
import ImageGallerySection from "@/components/book-detail/ImageGallerySection.vue";
import BookMetadataSection from "@/components/book-detail/BookMetadataSection.vue";
import ProvenanceSection from "@/components/book-detail/ProvenanceSection.vue";
import AnalysisSection from "@/components/book-detail/AnalysisSection.vue";
import BookSidebarSection from "@/components/book-detail/BookSidebarSection.vue";
import BookSocialCirclesSummary from "@/components/book-detail/BookSocialCirclesSummary.vue";
import ConfirmDeleteModal from "@/components/common/ConfirmDeleteModal.vue";

const route = useRoute();
const router = useRouter();
const booksStore = useBooksStore();
const authStore = useAuthStore();

// Image gallery state (owned by parent for carousel sharing)
const images = ref<BookImage[]>([]);
const carouselVisible = ref(false);
const carouselInitialIndex = ref(0);

// Delete book confirmation state (owned by parent - navigates on success)
const deleteModalVisible = ref(false);
const deleting = ref(false);
const deleteError = ref<string | null>(null);

// Status management state
const updatingStatus = ref(false);

// Component refs for callback pattern
const provenanceSectionRef = ref<InstanceType<typeof ProvenanceSection> | null>(null);

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

onMounted(async () => {
  const id = Number(route.params.id);
  await booksStore.fetchBook(id);

  // Fetch images
  try {
    const response = await api.get(`/books/${id}/images`);
    images.value = response.data;
  } catch (e) {
    images.value = [];
    handleApiError(e, "Loading images");
  }
});

// Carousel handlers
function handleOpenCarousel(index: number) {
  carouselInitialIndex.value = index;
  carouselVisible.value = true;
}

function closeCarousel() {
  carouselVisible.value = false;
}

// Images changed handler (from ImageGallerySection)
function handleImagesChanged(newImages: BookImage[]) {
  images.value = newImages;
}

// Status change handler (from BookMetadataSection)
async function handleStatusChanged(newStatus: string) {
  if (!booksStore.currentBook || updatingStatus.value) return;

  updatingStatus.value = true;
  try {
    await api.patch(`/books/${booksStore.currentBook.id}/status?status=${newStatus}`);
    booksStore.setCurrentBookStatus(newStatus);
  } catch (e: unknown) {
    handleApiError(e, "Updating status");
  } finally {
    updatingStatus.value = false;
  }
}

// Provenance save handler (from ProvenanceSection)
async function handleProvenanceSaved(newProvenance: string | null) {
  if (!booksStore.currentBook) return;

  try {
    await booksStore.updateBook(booksStore.currentBook.id, {
      provenance: newProvenance,
    });
    // Notify child of success - closes edit mode
    provenanceSectionRef.value?.onSaveSuccess();
  } catch (e: unknown) {
    handleApiError(e, "Saving provenance");
    // Notify child of error - keeps edit mode open for retry
    provenanceSectionRef.value?.onSaveError();
  }
}

// Delete book handlers
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

    // Invalidate dashboard cache since book data changed
    invalidateDashboardCache();

    void router.push("/books");
  } catch (e: unknown) {
    deleteError.value = e instanceof Error ? e.message : "Failed to delete book";
  } finally {
    deleting.value = false;
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
          class="text-moxon-600 hover:text-moxon-800 inline-block no-print"
        >
          &larr; Back to Collection
        </RouterLink>
        <BookActionsBar
          :book="booksStore.currentBook"
          :is-editor="authStore.isEditor"
          @delete="openDeleteModal"
          @print="printPage"
        />
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
      <div class="lg:col-span-2 flex flex-col gap-6">
        <ImageGallerySection
          :book-id="booksStore.currentBook.id"
          :images="images"
          :is-editor="authStore.isEditor"
          @open-carousel="handleOpenCarousel"
          @images-changed="handleImagesChanged"
        />

        <BookMetadataSection
          :book="booksStore.currentBook"
          :is-editor="authStore.isEditor"
          :updating-status="updatingStatus"
          @status-changed="handleStatusChanged"
        />

        <ProvenanceSection
          ref="provenanceSectionRef"
          :book-id="booksStore.currentBook.id"
          :provenance="booksStore.currentBook.provenance"
          :is-editor="authStore.isEditor"
          @provenance-saved="handleProvenanceSaved"
        />

        <AnalysisSection :book="booksStore.currentBook" :is-editor="authStore.isEditor" />

        <BookSocialCirclesSummary
          :book-id="booksStore.currentBook.id"
          :book-status="booksStore.currentBook.status"
        />
      </div>

      <!-- Sidebar -->
      <BookSidebarSection :book="booksStore.currentBook" :image-count="images.length" />
    </div>

    <!-- Image Carousel Modal -->
    <ImageCarousel
      :book-id="booksStore.currentBook.id"
      :visible="carouselVisible"
      :initial-index="carouselInitialIndex"
      @close="closeCarousel"
    />

    <!-- Delete Confirmation Modal -->
    <ConfirmDeleteModal
      :visible="deleteModalVisible"
      title="Delete Book"
      message="Are you sure you want to delete this book?"
      :warning-text="`This will permanently delete the book along with all associated images (${images.length}) and analysis data.`"
      confirm-button-text="Delete Book"
      :loading="deleting"
      :error="deleteError"
      @close="closeDeleteModal"
      @confirm="confirmDelete"
    >
      <p class="font-medium text-gray-800 mb-2">"{{ booksStore.currentBook.title }}"</p>
    </ConfirmDeleteModal>
  </div>
</template>

<style scoped>
/* Print styles */
@media print {
  /* Remove top margin to prevent blank first page */
  .max-w-5xl {
    max-width: none !important;
    margin-top: 0 !important;
    padding-top: 0 !important;
  }

  .card {
    break-inside: avoid;
    box-shadow: none !important;
    border: 1px solid #ddd !important;
  }

  /* Hide select dropdowns in child components - use :deep() to pierce scoping */
  :deep(select) {
    display: none !important;
  }

  /* Show print-only status text in child components */
  :deep(.print-only) {
    display: inline !important;
  }

  /* Hide image hover overlays */
  :deep(.group > button > div) {
    display: none !important;
  }

  /* Ensure images print */
  img {
    max-width: 100% !important;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
}
</style>
