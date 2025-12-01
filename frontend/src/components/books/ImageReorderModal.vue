<script setup lang="ts">
import { ref, watch } from "vue";
import { api } from "@/services/api";

const props = defineProps<{
  bookId: number;
  visible: boolean;
  images: Array<{
    id: number;
    url: string;
    thumbnail_url: string;
    image_type: string;
    caption: string | null;
    display_order: number;
    is_primary: boolean;
  }>;
}>();

const emit = defineEmits<{
  close: [];
  reordered: [images: typeof props.images];
}>();

const orderedImages = ref<typeof props.images>([]);
const saving = ref(false);
const error = ref<string | null>(null);
const draggedIndex = ref<number | null>(null);
const dropTargetIndex = ref<number | null>(null);

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      // Clone the images array
      orderedImages.value = [...props.images].sort((a, b) => a.display_order - b.display_order);
      error.value = null;
    }
  }
);

function handleDragStart(e: DragEvent, index: number) {
  draggedIndex.value = index;
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = "move";
  }
}

function handleDragOver(e: DragEvent, index: number) {
  e.preventDefault();
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = "move";
  }
  dropTargetIndex.value = index;
}

function handleDragLeave() {
  dropTargetIndex.value = null;
}

function handleDrop(e: DragEvent, dropIndex: number) {
  e.preventDefault();

  if (draggedIndex.value === null || draggedIndex.value === dropIndex) {
    draggedIndex.value = null;
    dropTargetIndex.value = null;
    return;
  }

  // Reorder the array
  const items = [...orderedImages.value];
  const [draggedItem] = items.splice(draggedIndex.value, 1);
  items.splice(dropIndex, 0, draggedItem);

  orderedImages.value = items;
  draggedIndex.value = null;
  dropTargetIndex.value = null;
}

function handleDragEnd() {
  draggedIndex.value = null;
  dropTargetIndex.value = null;
}

function moveUp(index: number) {
  if (index === 0) return;
  const items = [...orderedImages.value];
  [items[index - 1], items[index]] = [items[index], items[index - 1]];
  orderedImages.value = items;
}

function moveDown(index: number) {
  if (index === orderedImages.value.length - 1) return;
  const items = [...orderedImages.value];
  [items[index], items[index + 1]] = [items[index + 1], items[index]];
  orderedImages.value = items;
}

async function save() {
  saving.value = true;
  error.value = null;

  try {
    const imageIds = orderedImages.value.map((img) => img.id);
    await api.put(`/books/${props.bookId}/images/reorder`, imageIds);

    // Update display_order in the local array
    const updatedImages = orderedImages.value.map((img, idx) => ({
      ...img,
      display_order: idx,
    }));

    emit("reordered", updatedImages);
    emit("close");
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || "Failed to save order";
  } finally {
    saving.value = false;
  }
}

function close() {
  emit("close");
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="close"
      >
        <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
          <!-- Header -->
          <div class="flex items-center justify-between p-4 border-b">
            <h2 class="text-lg font-semibold text-gray-800">Reorder Images</h2>
            <button @click="close" class="text-gray-500 hover:text-gray-700">
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
            <p class="text-sm text-gray-600 mb-4">
              Drag and drop images to reorder them. The first image will be shown as the primary
              thumbnail.
            </p>

            <div class="space-y-2">
              <div
                v-for="(img, index) in orderedImages"
                :key="img.id"
                :class="[
                  'flex items-center gap-3 p-3 rounded-lg border-2 transition-all cursor-move',
                  draggedIndex === index
                    ? 'opacity-50 border-moxon-300'
                    : dropTargetIndex === index
                      ? 'border-moxon-500 bg-moxon-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white',
                ]"
                draggable="true"
                @dragstart="handleDragStart($event, index)"
                @dragover="handleDragOver($event, index)"
                @dragleave="handleDragLeave"
                @drop="handleDrop($event, index)"
                @dragend="handleDragEnd"
              >
                <!-- Drag Handle -->
                <div class="text-gray-400 flex-shrink-0">
                  <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path
                      d="M8 6a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm0 6a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm0 6a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm8-12a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm0 6a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm0 6a2 2 0 1 1-4 0 2 2 0 0 1 4 0z"
                    />
                  </svg>
                </div>

                <!-- Order Number -->
                <div
                  class="w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 text-gray-600 font-medium text-sm flex-shrink-0"
                >
                  {{ index + 1 }}
                </div>

                <!-- Thumbnail -->
                <img
                  :src="img.thumbnail_url"
                  :alt="img.caption || `Image ${index + 1}`"
                  class="w-16 h-16 object-cover rounded flex-shrink-0"
                />

                <!-- Info -->
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-800 truncate">
                    {{ img.caption || img.image_type || `Image ${index + 1}` }}
                  </p>
                  <p v-if="index === 0" class="text-xs text-moxon-600">Primary thumbnail</p>
                </div>

                <!-- Up/Down Buttons -->
                <div class="flex flex-col gap-1 flex-shrink-0">
                  <button
                    @click.stop="moveUp(index)"
                    :disabled="index === 0"
                    :class="[
                      'p-1 rounded hover:bg-gray-100',
                      index === 0 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500',
                    ]"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M5 15l7-7 7 7"
                      />
                    </svg>
                  </button>
                  <button
                    @click.stop="moveDown(index)"
                    :disabled="index === orderedImages.length - 1"
                    :class="[
                      'p-1 rounded hover:bg-gray-100',
                      index === orderedImages.length - 1
                        ? 'text-gray-300 cursor-not-allowed'
                        : 'text-gray-500',
                    ]"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <!-- Error -->
            <div
              v-if="error"
              class="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm"
            >
              {{ error }}
            </div>
          </div>

          <!-- Footer -->
          <div class="flex justify-end gap-3 p-4 border-t">
            <button type="button" @click="close" :disabled="saving" class="btn-secondary">
              Cancel
            </button>
            <button type="button" @click="save" :disabled="saving" class="btn-primary">
              {{ saving ? "Saving..." : "Save Order" }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
