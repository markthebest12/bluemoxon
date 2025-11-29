<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useBooksStore } from '@/stores/books'
import { api } from '@/services/api'

const route = useRoute()
const booksStore = useBooksStore()
const analysis = ref<string | null>(null)
const showAnalysis = ref(false)

onMounted(async () => {
  const id = Number(route.params.id)
  await booksStore.fetchBook(id)

  // Fetch analysis if available
  if (booksStore.currentBook?.has_analysis) {
    try {
      const response = await api.get(`/books/${id}/analysis/raw`)
      analysis.value = response.data
    } catch {
      // No analysis available
    }
  }
})

function formatCurrency(value: number | null): string {
  if (value === null) return '-'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0
  }).format(value)
}
</script>

<template>
  <div v-if="booksStore.loading" class="text-center py-12">
    <p class="text-gray-500">Loading book details...</p>
  </div>

  <div v-else-if="booksStore.currentBook" class="max-w-4xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <RouterLink to="/books" class="text-moxon-600 hover:text-moxon-800 mb-4 inline-block">
        &larr; Back to Collection
      </RouterLink>
      <h1 class="text-3xl font-bold text-gray-800">
        {{ booksStore.currentBook.title }}
      </h1>
      <p class="text-xl text-gray-600 mt-2">
        {{ booksStore.currentBook.author?.name || 'Unknown Author' }}
      </p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Main Info -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Publication Details -->
        <div class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Publication Details</h2>
          <dl class="grid grid-cols-2 gap-4">
            <div>
              <dt class="text-sm text-gray-500">Publisher</dt>
              <dd class="font-medium">
                {{ booksStore.currentBook.publisher?.name || '-' }}
                <span v-if="booksStore.currentBook.publisher?.tier" class="text-xs text-moxon-600">
                  ({{ booksStore.currentBook.publisher.tier }})
                </span>
              </dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Date</dt>
              <dd class="font-medium">{{ booksStore.currentBook.publication_date || '-' }}</dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Edition</dt>
              <dd class="font-medium">{{ booksStore.currentBook.edition || '-' }}</dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Volumes</dt>
              <dd class="font-medium">{{ booksStore.currentBook.volumes }}</dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Category</dt>
              <dd class="font-medium">{{ booksStore.currentBook.category || '-' }}</dd>
            </div>
            <div>
              <dt class="text-sm text-gray-500">Status</dt>
              <dd class="font-medium">{{ booksStore.currentBook.status }}</dd>
            </div>
          </dl>
        </div>

        <!-- Binding -->
        <div class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Binding</h2>
          <dl class="space-y-2">
            <div>
              <dt class="text-sm text-gray-500">Type</dt>
              <dd class="font-medium">{{ booksStore.currentBook.binding_type || '-' }}</dd>
            </div>
            <div v-if="booksStore.currentBook.binding_authenticated">
              <dt class="text-sm text-gray-500">Bindery</dt>
              <dd class="font-medium text-victorian-burgundy">
                {{ booksStore.currentBook.binder?.name }} (Authenticated)
              </dd>
            </div>
            <div v-if="booksStore.currentBook.binding_description">
              <dt class="text-sm text-gray-500">Description</dt>
              <dd class="text-gray-700">{{ booksStore.currentBook.binding_description }}</dd>
            </div>
          </dl>
        </div>

        <!-- Notes -->
        <div v-if="booksStore.currentBook.notes" class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Notes</h2>
          <p class="text-gray-700 whitespace-pre-wrap">{{ booksStore.currentBook.notes }}</p>
        </div>

        <!-- Analysis -->
        <div v-if="analysis" class="card">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-lg font-semibold text-gray-800">Analysis</h2>
            <button
              @click="showAnalysis = !showAnalysis"
              class="text-moxon-600 hover:text-moxon-800 text-sm"
            >
              {{ showAnalysis ? 'Hide' : 'Show' }} Full Analysis
            </button>
          </div>
          <div v-if="showAnalysis" class="prose max-w-none">
            <pre class="whitespace-pre-wrap text-sm">{{ analysis }}</pre>
          </div>
        </div>
      </div>

      <!-- Sidebar - Valuation -->
      <div class="space-y-6">
        <div class="card bg-victorian-cream">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Valuation</h2>
          <div class="text-center">
            <p class="text-3xl font-bold text-victorian-gold">
              {{ formatCurrency(booksStore.currentBook.value_mid) }}
            </p>
            <p class="text-sm text-gray-500 mt-1">Mid Estimate</p>
          </div>
          <div class="flex justify-between mt-4 text-sm">
            <div class="text-center">
              <p class="font-medium">{{ formatCurrency(booksStore.currentBook.value_low) }}</p>
              <p class="text-gray-500">Low</p>
            </div>
            <div class="text-center">
              <p class="font-medium">{{ formatCurrency(booksStore.currentBook.value_high) }}</p>
              <p class="text-gray-500">High</p>
            </div>
          </div>
        </div>

        <div v-if="booksStore.currentBook.purchase_price" class="card">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Acquisition</h2>
          <dl class="space-y-2">
            <div>
              <dt class="text-sm text-gray-500">Purchase Price</dt>
              <dd class="font-medium">{{ formatCurrency(booksStore.currentBook.purchase_price) }}</dd>
            </div>
            <div v-if="booksStore.currentBook.discount_pct">
              <dt class="text-sm text-gray-500">Discount</dt>
              <dd class="font-medium text-green-600">{{ booksStore.currentBook.discount_pct }}%</dd>
            </div>
            <div v-if="booksStore.currentBook.roi_pct">
              <dt class="text-sm text-gray-500">ROI</dt>
              <dd class="font-medium text-green-600">{{ booksStore.currentBook.roi_pct }}%</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  </div>
</template>
