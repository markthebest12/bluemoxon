<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { api } from "@/services/api";

const props = defineProps<{
  bookId: number;
  visible: boolean;
  initialIndex?: number;
}>();

const emit = defineEmits<{
  close: [];
}>();

interface BookImage {
  id: number;
  url: string;
  thumbnail_url: string;
  image_type: string;
  caption: string | null;
  display_order: number;
  is_primary: boolean;
}

const images = ref<BookImage[]>([]);
const currentIndex = ref(0);
const loading = ref(true);

onMounted(async () => {
  await loadImages();
  document.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", handleKeydown);
});

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      currentIndex.value = props.initialIndex || 0;
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
  }
);

async function loadImages() {
  try {
    const response = await api.get(`/books/${props.bookId}/images`);
    images.value = response.data;
    if (props.initialIndex !== undefined) {
      currentIndex.value = props.initialIndex;
    }
  } catch {
    images.value = [];
  } finally {
    loading.value = false;
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (!props.visible) return;

  switch (e.key) {
    case "Escape":
      emit("close");
      break;
    case "ArrowLeft":
      prev();
      break;
    case "ArrowRight":
      next();
      break;
  }
}

function prev() {
  if (currentIndex.value > 0) {
    currentIndex.value--;
  } else {
    currentIndex.value = images.value.length - 1;
  }
}

function next() {
  if (currentIndex.value < images.value.length - 1) {
    currentIndex.value++;
  } else {
    currentIndex.value = 0;
  }
}

function goTo(index: number) {
  currentIndex.value = index;
}

function handleBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) {
    emit("close");
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="visible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
        @click="handleBackdropClick"
      >
        <!-- Close button -->
        <button
          @click="emit('close')"
          class="absolute top-4 right-4 text-white hover:text-gray-300 z-10"
        >
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>

        <!-- Loading -->
        <div v-if="loading" class="text-white text-center">
          <p>Loading images...</p>
        </div>

        <!-- No images -->
        <div v-else-if="images.length === 0" class="text-white text-center">
          <p>No images available</p>
        </div>

        <!-- Carousel -->
        <div v-else class="relative w-full max-w-5xl mx-4 flex flex-col max-h-[90vh]">
          <!-- Main image -->
          <div class="relative flex-1 min-h-0 bg-black rounded-lg overflow-hidden">
            <img
              :src="images[currentIndex].url"
              :alt="images[currentIndex].caption || `Image ${currentIndex + 1}`"
              decoding="async"
              fetchpriority="high"
              class="w-full h-full object-contain"
            />

            <!-- Caption -->
            <div
              v-if="images[currentIndex].caption || images[currentIndex].image_type"
              class="absolute bottom-0 left-0 right-0 bg-black/60 text-white p-3"
            >
              <p class="text-sm">
                {{ images[currentIndex].caption || images[currentIndex].image_type }}
              </p>
            </div>
          </div>

          <!-- Navigation arrows -->
          <button
            v-if="images.length > 1"
            @click="prev"
            class="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-12 text-white hover:text-gray-300"
          >
            <svg class="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>

          <button
            v-if="images.length > 1"
            @click="next"
            class="absolute right-0 top-1/2 -translate-y-1/2 translate-x-12 text-white hover:text-gray-300"
          >
            <svg class="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>

          <!-- Counter -->
          <div class="absolute top-4 left-4 bg-black/60 text-white px-3 py-1 rounded-full text-sm">
            {{ currentIndex + 1 }} / {{ images.length }}
          </div>

          <!-- Thumbnails -->
          <div
            v-if="images.length > 1"
            class="flex justify-center gap-2 mt-4 overflow-x-auto py-2 flex-shrink-0"
          >
            <button
              v-for="(img, idx) in images"
              :key="img.id"
              @click="goTo(idx)"
              :class="[
                'w-16 h-16 rounded overflow-hidden border-2 transition-all flex-shrink-0',
                idx === currentIndex
                  ? 'border-white'
                  : 'border-transparent opacity-60 hover:opacity-100',
              ]"
            >
              <img
                :src="img.thumbnail_url"
                :alt="`Thumbnail ${idx + 1}`"
                loading="lazy"
                decoding="async"
                class="w-full h-full object-cover"
              />
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
