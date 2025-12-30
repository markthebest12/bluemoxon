<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { api } from "@/services/api";
import TransitionModal from "../TransitionModal.vue";

const props = defineProps<{
  bookId: number;
  visible: boolean;
}>();

const emit = defineEmits<{
  close: [];
  uploaded: [];
}>();

interface UploadFile {
  file: File;
  id: string;
  status: "pending" | "uploading" | "success" | "error";
  progress: number;
  error?: string;
}

const files = ref<UploadFile[]>([]);
const isDragging = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);

// Reset files when modal opens
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      files.value = [];
    }
  }
);

const hasFiles = computed(() => files.value.length > 0);
const isUploading = computed(() => files.value.some((f) => f.status === "uploading"));
const allComplete = computed(() =>
  files.value.every((f) => f.status === "success" || f.status === "error")
);
const successCount = computed(() => files.value.filter((f) => f.status === "success").length);
const errorCount = computed(() => files.value.filter((f) => f.status === "error").length);

function generateId(): string {
  return Math.random().toString(36).substring(2, 11);
}

function isValidImageType(file: File): boolean {
  const validTypes = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/heic"];
  return validTypes.includes(file.type) || file.name.toLowerCase().endsWith(".heic");
}

function addFiles(newFiles: FileList | null) {
  if (!newFiles) return;

  for (const file of Array.from(newFiles)) {
    if (!isValidImageType(file)) {
      continue; // Skip non-image files
    }

    // Check for duplicates
    const exists = files.value.some((f) => f.file.name === file.name && f.file.size === file.size);
    if (exists) continue;

    files.value.push({
      file,
      id: generateId(),
      status: "pending",
      progress: 0,
    });
  }
}

function removeFile(id: string) {
  files.value = files.value.filter((f) => f.id !== id);
}

function handleDragOver(e: DragEvent) {
  e.preventDefault();
  isDragging.value = true;
}

function handleDragLeave(e: DragEvent) {
  e.preventDefault();
  isDragging.value = false;
}

function handleDrop(e: DragEvent) {
  e.preventDefault();
  isDragging.value = false;
  addFiles(e.dataTransfer?.files ?? null);
}

function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement;
  addFiles(target.files);
  // Reset input so same file can be selected again
  target.value = "";
}

function openFileDialog() {
  fileInputRef.value?.click();
}

async function uploadFile(uploadFile: UploadFile) {
  uploadFile.status = "uploading";
  uploadFile.progress = 0;

  try {
    const formData = new FormData();
    formData.append("file", uploadFile.file);

    await api.post(`/books/${props.bookId}/images`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          uploadFile.progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        }
      },
    });

    uploadFile.status = "success";
    uploadFile.progress = 100;
  } catch (e: any) {
    uploadFile.status = "error";
    uploadFile.error = e.response?.data?.detail || e.message || "Upload failed";
  }
}

async function uploadAll() {
  const pendingFiles = files.value.filter((f) => f.status === "pending");

  // Upload files sequentially to avoid overwhelming the server
  for (const file of pendingFiles) {
    await uploadFile(file);
  }

  // If any succeeded, emit uploaded event
  if (successCount.value > 0) {
    emit("uploaded");
  }
}

function close() {
  if (!isUploading.value) {
    emit("close");
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}
</script>

<template>
  <TransitionModal :visible="visible" @backdrop-click="close">
    <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b">
        <h2 class="text-lg font-semibold text-gray-800">Upload Images</h2>
        <button
          @click="close"
          :disabled="isUploading"
          class="text-gray-500 hover:text-gray-700 disabled:opacity-50"
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

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-4">
        <!-- Drop Zone -->
        <div
          :class="[
            'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
            isDragging ? 'border-moxon-500 bg-moxon-50' : 'border-gray-300 hover:border-gray-400',
          ]"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @drop="handleDrop"
        >
          <svg
            class="w-12 h-12 mx-auto text-gray-400 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <p class="text-gray-600 mb-2">
            Drag and drop images here, or
            <button @click="openFileDialog" class="text-moxon-600 hover:text-moxon-800 font-medium">
              browse
            </button>
          </p>
          <p class="text-sm text-gray-500">Supports JPEG, PNG, GIF, WebP, HEIC</p>
          <input
            ref="fileInputRef"
            type="file"
            accept="image/*,.heic"
            multiple
            class="hidden"
            @change="handleFileSelect"
          />
        </div>

        <!-- File List -->
        <div v-if="hasFiles" class="mt-4 flex flex-col gap-2">
          <div
            v-for="file in files"
            :key="file.id"
            class="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
          >
            <!-- Status Icon -->
            <div class="shrink-0">
              <svg
                v-if="file.status === 'pending'"
                class="w-5 h-5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <svg
                v-else-if="file.status === 'uploading'"
                class="w-5 h-5 text-moxon-600 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <svg
                v-else-if="file.status === 'success'"
                class="w-5 h-5 text-[var(--color-status-success-accent)]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <svg
                v-else-if="file.status === 'error'"
                class="w-5 h-5 text-[var(--color-status-error-accent)]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>

            <!-- File Info -->
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-800 truncate">
                {{ file.file.name }}
              </p>
              <p
                v-if="file.status === 'error'"
                class="text-xs text-[var(--color-status-error-accent)]"
              >
                {{ file.error }}
              </p>
              <p v-else class="text-xs text-gray-500">
                {{ formatFileSize(file.file.size) }}
              </p>
            </div>

            <!-- Progress Bar -->
            <div v-if="file.status === 'uploading'" class="w-20 shrink-0">
              <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  class="h-full bg-moxon-600 transition-all duration-300"
                  :style="{ width: file.progress + '%' }"
                />
              </div>
              <p class="text-xs text-gray-500 text-center mt-1">{{ file.progress }}%</p>
            </div>

            <!-- Remove Button (only if pending or error) -->
            <button
              v-if="file.status === 'pending' || file.status === 'error'"
              @click="removeFile(file.id)"
              class="shrink-0 p-1 text-gray-400 hover:text-gray-600"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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

        <!-- Summary -->
        <div
          v-if="allComplete && hasFiles"
          class="mt-4 p-3 rounded-lg"
          :class="
            errorCount > 0
              ? 'bg-[var(--color-status-warning-bg)]'
              : 'bg-[var(--color-status-success-bg)]'
          "
        >
          <p class="text-sm">
            <span v-if="successCount > 0" class="text-[var(--color-status-success-text)]">
              {{ successCount }} image{{ successCount !== 1 ? "s" : "" }} uploaded successfully.
            </span>
            <span v-if="errorCount > 0" class="text-[var(--color-status-error-text)]">
              {{ errorCount }} upload{{ errorCount !== 1 ? "s" : "" }} failed.
            </span>
          </p>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex justify-end gap-3 p-4 border-t">
        <button type="button" @click="close" :disabled="isUploading" class="btn-secondary">
          {{ allComplete ? "Close" : "Cancel" }}
        </button>
        <button
          v-if="!allComplete"
          type="button"
          @click="uploadAll"
          :disabled="!hasFiles || isUploading || files.every((f) => f.status !== 'pending')"
          class="btn-primary"
        >
          {{
            isUploading
              ? "Uploading..."
              : `Upload ${files.filter((f) => f.status === "pending").length} Image${files.filter((f) => f.status === "pending").length !== 1 ? "s" : ""}`
          }}
        </button>
      </div>
    </div>
  </TransitionModal>
</template>
