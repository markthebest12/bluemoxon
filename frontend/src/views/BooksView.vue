<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBooksStore } from '@/stores/books'

const route = useRoute()
const router = useRouter()
const booksStore = useBooksStore()

onMounted(() => {
  // Apply URL query params as filters
  if (route.query.inventory_type) {
    booksStore.filters.inventory_type = route.query.inventory_type as string
  }
  if (route.query.binding_authenticated) {
    booksStore.filters.binding_authenticated = route.query.binding_authenticated === 'true'
  }
  booksStore.fetchBooks()
})

function formatCurrency(value: number | null): string {
  if (value === null) return '-'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0
  }).format(value)
}

function viewBook(id: number) {
  router.push(`/books/${id}`)
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold text-gray-800">Book Collection</h1>
      <div class="flex items-center space-x-4">
        <!-- Filter by inventory type -->
        <select
          v-model="booksStore.filters.inventory_type"
          @change="booksStore.setFilters(booksStore.filters)"
          class="input w-48"
        >
          <option value="">All Inventories</option>
          <option value="PRIMARY">Primary Collection</option>
          <option value="EXTENDED">Extended Inventory</option>
          <option value="FLAGGED">Flagged for Removal</option>
        </select>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="booksStore.loading" class="text-center py-12">
      <p class="text-gray-500">Loading books...</p>
    </div>

    <!-- Books grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="book in booksStore.books"
        :key="book.id"
        @click="viewBook(book.id)"
        class="card cursor-pointer hover:shadow-lg transition-shadow"
      >
        <h3 class="text-lg font-semibold text-gray-800 line-clamp-2">
          {{ book.title }}
        </h3>
        <p class="text-gray-600 mt-1">
          {{ book.author?.name || 'Unknown Author' }}
        </p>
        <p class="text-sm text-gray-500 mt-1">
          {{ book.publisher?.name }} ({{ book.publication_date }})
        </p>

        <div class="flex items-center justify-between mt-4">
          <span class="text-lg font-bold text-victorian-gold">
            {{ formatCurrency(book.value_mid) }}
          </span>
          <div class="flex items-center space-x-2">
            <span
              v-if="book.binding_authenticated"
              class="px-2 py-1 text-xs bg-victorian-burgundy text-white rounded"
            >
              {{ book.binder?.name }}
            </span>
            <span
              v-if="book.volumes > 1"
              class="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded"
            >
              {{ book.volumes }} vols
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="booksStore.totalPages > 1" class="flex justify-center mt-8 space-x-2">
      <button
        @click="booksStore.setPage(booksStore.page - 1)"
        :disabled="booksStore.page === 1"
        class="btn-secondary disabled:opacity-50"
      >
        Previous
      </button>
      <span class="px-4 py-2">
        Page {{ booksStore.page }} of {{ booksStore.totalPages }}
      </span>
      <button
        @click="booksStore.setPage(booksStore.page + 1)"
        :disabled="booksStore.page === booksStore.totalPages"
        class="btn-secondary disabled:opacity-50"
      >
        Next
      </button>
    </div>
  </div>
</template>
