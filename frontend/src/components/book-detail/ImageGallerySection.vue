<script setup lang="ts">
import { ref } from "vue";
import { api } from "@/services/api";
import { getErrorMessage } from "@/types/errors";
import { handleApiError, handleSuccess } from "@/utils/errorHandler";
import { type BookImage } from "@/types/books";
import BookThumbnail from "@/components/books/BookThumbnail.vue";
import ImageReorderModal from "@/components/books/ImageReorderModal.vue";
import ImageUploadModal from "@/components/books/ImageUploadModal.vue";

const props = defineProps<{
  bookId: number;
  images: BookImage[];
  isEditor: boolean;
}>();

const emit = defineEmits<{
  "open-carousel": [index: number];
  "images-changed": [images: BookImage[]];
}>();

// Internal state
const uploadModalVisible = ref(false);
const reorderModalVisible = ref(false);
const deleteImageModalVisible = ref(false);
const imageToDelete = ref<BookImage | null>(null);
const deletingImage = ref(false);
const deleteImageError = ref<string | null>(null);

// Upload modal methods
function openUploadModal() {
  uploadModalVisible.value = true;
}

function closeUploadModal() {
  uploadModalVisible.value = false;
}

async function handleImagesUploaded() {
  try {
    const response = await api.get(`/books/${props.bookId}/images`);
    emit("images-changed", response.data);
    handleSuccess("Images uploaded");
  } catch (e) {
    handleApiError(e, "Refreshing images");
  }
}

// Reorder modal methods
function openReorderModal() {
  reorderModalVisible.value = true;
}

function closeReorderModal() {
  reorderModalVisible.value = false;
}

function handleImagesReordered(newImages: BookImage[]) {
  emit("images-changed", newImages);
}

// Delete image modal methods
function openDeleteImageModal(img: BookImage) {
  imageToDelete.value = img;
  deleteImageError.value = null;
  deleteImageModalVisible.value = true;
}

function closeDeleteImageModal() {
  deleteImageModalVisible.value = false;
  imageToDelete.value = null;
  deleteImageError.value = null;
}

async function confirmDeleteImage() {
  if (!imageToDelete.value) return;

  const imageId = imageToDelete.value.id;
  deletingImage.value = true;
  deleteImageError.value = null;

  try {
    await api.delete(`/books/${props.bookId}/images/${imageId}`);
    // Remove from local array and emit
    const updatedImages = props.images.filter((img) => img.id !== imageId);
    emit("images-changed", updatedImages);
    handleSuccess("Image deleted");
    closeDeleteImageModal();
  } catch (e) {
    deleteImageError.value = getErrorMessage(e);
    handleApiError(e, "Deleting image");
  } finally {
    deletingImage.value = false;
  }
}

// Open carousel
function openCarousel(index: number) {
  emit("open-carousel", index);
}
</script>

<template>
  <div class="card">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-800">Images</h2>
      <div v-if="isEditor" class="flex items-center gap-3 no-print">
        <button
          class="text-sm text-moxon-600 hover:text-moxon-800 flex items-center gap-1"
          @click="openUploadModal"
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
          class="text-sm text-moxon-600 hover:text-moxon-800 flex items-center gap-1"
          @click="openReorderModal"
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

    <!-- Image Grid -->
    <div v-if="images.length > 0" class="grid grid-cols-4 gap-3">
      <div
        v-for="(img, idx) in images"
        :key="img.id"
        class="relative group aspect-square rounded-sm overflow-hidden"
      >
        <button
          class="w-full h-full hover:ring-2 hover:ring-moxon-500 transition-all"
          @click="openCarousel(idx)"
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
          v-if="isEditor"
          class="absolute top-1 right-1 p-1 bg-[var(--color-status-error-solid)] text-[var(--color-status-error-solid-text)] rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:opacity-80 no-print"
          title="Delete image"
          @click.stop="openDeleteImageModal(img)"
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

    <!-- Empty State -->
    <div v-else class="flex items-center justify-center py-8">
      <div class="text-center">
        <div class="w-48">
          <BookThumbnail :book-id="bookId" />
        </div>
        <p class="text-sm text-gray-500 mt-3">No images available</p>
      </div>
    </div>
  </div>

  <!-- Image Reorder Modal -->
  <ImageReorderModal
    :book-id="bookId"
    :visible="reorderModalVisible"
    :images="images"
    @close="closeReorderModal"
    @reordered="handleImagesReordered"
  />

  <!-- Image Upload Modal -->
  <ImageUploadModal
    :book-id="bookId"
    :visible="uploadModalVisible"
    @close="closeUploadModal"
    @uploaded="handleImagesUploaded"
  />

  <!-- Delete Image Confirmation Modal -->
  <Teleport to="body">
    <div v-if="deleteImageModalVisible" class="fixed inset-0 z-50 flex items-center justify-center">
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
              class="w-32 h-32 object-cover rounded-sm"
            />
          </div>
          <p class="text-sm text-[var(--color-status-error-accent)] mt-3 text-center">
            This action cannot be undone.
          </p>
        </div>

        <div
          v-if="deleteImageError"
          class="mb-4 p-3 bg-[var(--color-status-error-bg)] border border-[var(--color-status-error-border)] rounded-sm text-[var(--color-status-error-text)] text-sm"
        >
          {{ deleteImageError }}
        </div>

        <div class="flex justify-end gap-3">
          <button :disabled="deletingImage" class="btn-secondary" @click="closeDeleteImageModal">
            Cancel
          </button>
          <button :disabled="deletingImage" class="btn-danger" @click="confirmDeleteImage">
            {{ deletingImage ? "Deleting..." : "Delete Image" }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
