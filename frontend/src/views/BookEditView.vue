<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import BookForm from '@/components/books/BookForm.vue'

const route = useRoute()
const bookId = computed(() => Number(route.params.id))
</script>

<template>
  <div>
    <div class="mb-8">
      <RouterLink :to="`/books/${bookId}`" class="text-moxon-600 hover:text-moxon-800 mb-4 inline-block">
        &larr; Back to Book
      </RouterLink>
      <h1 class="text-3xl font-bold text-gray-800">Edit Book</h1>
    </div>

    <BookForm :book-id="bookId" />
  </div>
</template>
