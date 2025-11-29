<script setup lang="ts">
import BookForm from '@/components/books/BookForm.vue'
</script>

<template>
  <div>
    <div class="mb-8">
      <RouterLink to="/books" class="text-moxon-600 hover:text-moxon-800 mb-4 inline-block">
        &larr; Back to Collection
      </RouterLink>
      <h1 class="text-3xl font-bold text-gray-800">Add New Book</h1>
    </div>

    <BookForm />
  </div>
</template>
