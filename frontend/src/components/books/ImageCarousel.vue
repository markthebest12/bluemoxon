<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { api } from "@/services/api";
import { type BookImage } from "@/types/books";

const props = defineProps<{
  bookId: number;
  visible: boolean;
  initialIndex?: number;
}>();

const emit = defineEmits<{
  close: [];
}>();


const images = ref<BookImage[]>([]);
const currentIndex = ref(0);
const loading = ref(true);

// Touch/swipe handling
const touchStartX = ref(0);
const touchStartY = ref(0);
const touchEndX = ref(0);
const touchEndY = ref(0);
const minSwipeDistance = 50;

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

function handleTouchStart(e: TouchEvent) {
  touchStartX.value = e.touches[0].clientX;
  touchStartY.value = e.touches[0].clientY;
}

function handleTouchEnd(e: TouchEvent) {
  touchEndX.value = e.changedTouches[0].clientX;
  touchEndY.value = e.changedTouches[0].clientY;
  handleSwipe();
}

function handleSwipe() {
  const deltaX = touchEndX.value - touchStartX.value;
  const deltaY = touchEndY.value - touchStartY.value;

  // Only handle horizontal swipes (ignore if vertical movement is greater)
  if (Math.abs(deltaX) < minSwipeDistance || Math.abs(deltaY) > Math.abs(deltaX)) {
    return;
  }

  if (deltaX > 0) {
    // Swipe right -> previous image
    prev();
  } else {
    // Swipe left -> next image
    next();
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
          class="absolute top-4 right-4 text-white hover:text-gray-300 z-10"
          @click="emit('close')"
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
        <div v-else class="relative w-full max-w-5xl mx-4 flex flex-col items-center">
          <!-- Main image -->
          <div
            class="relative bg-black rounded-lg overflow-hidden"
            @touchstart="handleTouchStart"
            @touchend="handleTouchEnd"
          >
            <img
              :src="images[currentIndex].url"
              :alt="images[currentIndex].caption || `Image ${currentIndex + 1}`"
              decoding="async"
              fetchpriority="high"
              class="max-h-[70vh] max-w-full object-contain select-none"
              draggable="false"
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

          <!-- Navigation arrows - positioned inside on mobile, outside on desktop -->
          <button
            v-if="images.length > 1"
            class="absolute left-2 md:left-0 top-1/2 -translate-y-1/2 md:-translate-x-12 text-white hover:text-gray-300 bg-black/40 md:bg-transparent rounded-full p-1 md:p-0"
            @click="prev"
          >
            <svg
              class="w-8 h-8 md:w-10 md:h-10"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
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
            class="absolute right-2 md:right-0 top-1/2 -translate-y-1/2 md:translate-x-12 text-white hover:text-gray-300 bg-black/40 md:bg-transparent rounded-full p-1 md:p-0"
            @click="next"
          >
            <svg
              class="w-8 h-8 md:w-10 md:h-10"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>

          <!-- Dot indicators for mobile -->
          <div v-if="images.length > 1" class="flex justify-center gap-2 mt-3 md:hidden">
            <button
              v-for="(_, idx) in images"
              :key="idx"
              :class="[
                'w-2.5 h-2.5 rounded-full transition-all',
                idx === currentIndex ? 'bg-white scale-110' : 'bg-white/40 hover:bg-white/60',
              ]"
              :aria-label="`Go to image ${idx + 1}`"
              @click="goTo(idx)"
            />
          </div>

          <!-- Counter -->
          <div class="absolute top-4 left-4 bg-black/60 text-white px-3 py-1 rounded-full text-sm">
            {{ currentIndex + 1 }} / {{ images.length }}
          </div>

          <!-- Thumbnails -->
          <div
            v-if="images.length > 1"
            class="flex justify-center gap-2 mt-4 overflow-x-auto py-2 shrink-0"
          >
            <button
              v-for="(img, idx) in images"
              :key="img.id"
              :class="[
                'w-16 h-16 rounded-sm overflow-hidden border-2 transition-all shrink-0',
                idx === currentIndex
                  ? 'border-white'
                  : 'border-transparent opacity-60 hover:opacity-100',
              ]"
              @click="goTo(idx)"
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
