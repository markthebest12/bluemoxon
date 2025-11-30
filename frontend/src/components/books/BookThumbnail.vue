<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  bookId: number;
  imageUrl?: string | null;
  size?: "sm" | "md" | "lg";
}>();

const emit = defineEmits<{
  click: [];
}>();

const sizeClasses = computed(() => {
  switch (props.size) {
    case "sm":
      return "w-16 h-20";
    case "lg":
      return "w-48 h-64";
    default:
      return "w-24 h-32";
  }
});

const hasImage = computed(() => !!props.imageUrl);

// Use API placeholder for books without images
const API_URL = import.meta.env.VITE_API_URL || "/api/v1";
const placeholderUrl = `${API_URL}/images/placeholder`;

function handleClick() {
  if (hasImage.value) {
    emit("click");
  }
}
</script>

<template>
  <div
    :class="[
      sizeClasses,
      'relative rounded overflow-hidden bg-victorian-cream border border-gray-200',
      hasImage ? 'cursor-pointer hover:ring-2 hover:ring-moxon-500' : '',
    ]"
    @click="handleClick"
  >
    <!-- Image or Placeholder -->
    <img
      :src="imageUrl || placeholderUrl"
      alt="Book image"
      class="w-full h-full object-cover"
    />

    <!-- Image indicator badge (only for actual images) -->
    <div
      v-if="hasImage"
      class="absolute bottom-1 right-1 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded"
    >
      <svg
        class="w-3 h-3 inline"
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
    </div>
  </div>
</template>
