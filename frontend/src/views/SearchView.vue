<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'

const router = useRouter()
const query = ref('')
const scope = ref('all')
const results = ref<any[]>([])
const loading = ref(false)
const searched = ref(false)

async function search() {
  if (!query.value.trim()) return

  loading.value = true
  searched.value = true
  try {
    const response = await api.get('/search', {
      params: {
        q: query.value,
        scope: scope.value
      }
    })
    results.value = response.data.results
  } catch (e) {
    console.error('Search failed', e)
    results.value = []
  } finally {
    loading.value = false
  }
}

function viewResult(result: any) {
  if (result.type === 'book') {
    router.push(`/books/${result.id}`)
  } else if (result.type === 'analysis') {
    router.push(`/books/${result.book_id}`)
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold text-gray-800 mb-8">Search</h1>

    <!-- Search Form -->
    <div class="card mb-8">
      <form @submit.prevent="search" class="flex gap-4">
        <input
          v-model="query"
          type="text"
          placeholder="Search books, authors, notes, analysis..."
          class="input flex-1"
        />
        <select v-model="scope" class="input w-40">
          <option value="all">All</option>
          <option value="books">Books Only</option>
          <option value="analyses">Analyses Only</option>
        </select>
        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? 'Searching...' : 'Search' }}
        </button>
      </form>
    </div>

    <!-- Results -->
    <div v-if="loading" class="text-center py-12">
      <p class="text-gray-500">Searching...</p>
    </div>

    <div v-else-if="searched && results.length === 0" class="text-center py-12">
      <p class="text-gray-500">No results found for "{{ query }}"</p>
    </div>

    <div v-else-if="results.length > 0" class="space-y-4">
      <p class="text-sm text-gray-500 mb-4">{{ results.length }} results found</p>

      <div
        v-for="result in results"
        :key="`${result.type}-${result.id}`"
        @click="viewResult(result)"
        class="card cursor-pointer hover:shadow-lg transition-shadow"
      >
        <div class="flex items-start justify-between">
          <div>
            <span
              :class="[
                'px-2 py-1 text-xs rounded uppercase',
                result.type === 'book' ? 'bg-moxon-100 text-moxon-700' : 'bg-gray-100 text-gray-700'
              ]"
            >
              {{ result.type }}
            </span>
            <h3 class="text-lg font-semibold text-gray-800 mt-2">
              {{ result.title }}
            </h3>
            <p v-if="result.author" class="text-gray-600">{{ result.author }}</p>
          </div>
        </div>
        <p v-if="result.snippet" class="text-gray-500 text-sm mt-2 line-clamp-2">
          {{ result.snippet }}
        </p>
      </div>
    </div>
  </div>
</template>
