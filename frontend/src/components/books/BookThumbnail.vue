<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/services/api'

const props = defineProps<{
  bookId: number
  size?: 'sm' | 'md' | 'lg'
}>()

const emit = defineEmits<{
  click: []
}>()

interface ImageInfo {
  id: number | null
  url: string
  thumbnail_url: string
  image_type: string
  caption: string | null
}

const imageInfo = ref<ImageInfo | null>(null)
const loading = ref(true)
const error = ref(false)

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'w-16 h-20'
    case 'lg':
      return 'w-48 h-64'
    default:
      return 'w-24 h-32'
  }
})

onMounted(async () => {
  try {
    const response = await api.get(`/books/${props.bookId}/images/primary`)
    imageInfo.value = response.data
  } catch {
    // No image, will use placeholder
    imageInfo.value = {
      id: null,
      url: '/api/v1/images/placeholder',
      thumbnail_url: '/api/v1/images/placeholder',
      image_type: 'placeholder',
      caption: null,
    }
  } finally {
    loading.value = false
  }
})

function handleClick() {
  if (imageInfo.value?.id) {
    emit('click')
  }
}

function handleImageError() {
  error.value = true
  // Fallback to placeholder on error
  if (imageInfo.value) {
    imageInfo.value.thumbnail_url = '/api/v1/images/placeholder'
  }
}
</script>

<template>
  <div
    :class="[
      sizeClasses,
      'relative rounded overflow-hidden bg-victorian-cream border border-gray-200',
      imageInfo?.id ? 'cursor-pointer hover:ring-2 hover:ring-moxon-500' : ''
    ]"
    @click="handleClick"
  >
    <!-- Loading skeleton -->
    <div v-if="loading" class="absolute inset-0 animate-pulse bg-gray-200" />

    <!-- Image -->
    <img
      v-else-if="imageInfo"
      :src="imageInfo.thumbnail_url"
      :alt="imageInfo.caption || 'Book image'"
      class="w-full h-full object-cover"
      @error="handleImageError"
    />

    <!-- Image count badge (if has multiple images) -->
    <div
      v-if="imageInfo?.id"
      class="absolute bottom-1 right-1 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded"
    >
      <svg class="w-3 h-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    </div>
  </div>
</template>
