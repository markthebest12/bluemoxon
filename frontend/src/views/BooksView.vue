<script setup lang="ts">
import { onMounted, ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useBooksStore } from "@/stores/books";
import { useReferencesStore } from "@/stores/references";
import BookThumbnail from "@/components/books/BookThumbnail.vue";
import ImageCarousel from "@/components/books/ImageCarousel.vue";

const route = useRoute();
const router = useRouter();
const booksStore = useBooksStore();
const referencesStore = useReferencesStore();

// Carousel state
const carouselVisible = ref(false);
const carouselBookId = ref<number | null>(null);

// Filter panel state
const showFilters = ref(false);

// Sort options
const sortOptions = [
  { value: "title", label: "Title" },
  { value: "value_mid", label: "Value" },
  { value: "publication_date", label: "Date" },
  { value: "created_at", label: "Recently Added" },
];

// Filter options
const publisherTiers = ["Tier 1", "Tier 2", "Tier 3"];
const provenanceTiers = ["Tier 1", "Tier 2", "Tier 3"];
const bindingTypes = [
  "Full leather",
  "Half leather",
  "Quarter leather",
  "Cloth",
  "Paper boards",
  "Vellum",
];
const conditionGrades = ["Fine", "Very Good", "Good", "Fair", "Poor"];

// Count active filters
const activeFilterCount = computed(() => {
  let count = 0;
  const f = booksStore.filters;
  if (f.binder_id) count++;
  if (f.publisher_id) count++;
  if (f.publisher_tier) count++;
  if (f.binding_authenticated !== undefined) count++;
  if (f.binding_type) count++;
  if (f.condition_grade) count++;
  if (f.has_images !== undefined) count++;
  if (f.has_analysis !== undefined) count++;
  if (f.has_provenance !== undefined) count++;
  if (f.provenance_tier) count++;
  if (f.is_first_edition !== undefined) count++;
  if (f.status) count++;
  if (f.category) count++;
  if (f.min_value !== undefined || f.max_value !== undefined) count++;
  if (f.year_start !== undefined || f.year_end !== undefined) count++;
  return count;
});

// Sync filters from URL query params - URL is source of truth
function syncFiltersFromUrl() {
  // URL is the source of truth - always read from it
  // "ALL" in URL means all collections (empty string in store)
  // No param defaults to PRIMARY
  const urlInventoryType = route.query.inventory_type as string;
  if (urlInventoryType === "ALL") {
    booksStore.filters.inventory_type = "";
  } else {
    booksStore.filters.inventory_type = urlInventoryType || "PRIMARY";
  }

  // Read search query from URL
  booksStore.filters.q = (route.query.q as string) || undefined;

  // Read binding_authenticated
  if (route.query.binding_authenticated) {
    booksStore.filters.binding_authenticated = route.query.binding_authenticated === "true";
  } else {
    booksStore.filters.binding_authenticated = undefined;
  }
}

// Track if we've initialized and if we're updating URL ourselves
const initialized = ref(false);
const isUpdatingUrl = ref(false);

// Watch for route changes (handles back button navigation)
watch(
  () => route.fullPath,
  (newPath) => {
    // Skip if we're the ones updating the URL, or not initialized yet
    if (isUpdatingUrl.value || !initialized.value) {
      return;
    }
    // Only sync if we're on the books list route
    if (newPath.startsWith("/books?") || newPath === "/books") {
      syncFiltersFromUrl();
      booksStore.fetchBooks();
    }
  }
);

onMounted(async () => {
  // Load reference data for filters
  await referencesStore.fetchAll();

  // Apply URL query params as filters
  syncFiltersFromUrl();
  await booksStore.fetchBooks();

  // Mark as initialized after first load
  initialized.value = true;
});

// Sync filters to URL for back button support
function updateUrlWithFilters() {
  const query: Record<string, string> = {};

  // Include inventory_type in URL (except PRIMARY which is default)
  // Empty string (All Collections) is stored as "ALL" in URL
  if (booksStore.filters.inventory_type === "") {
    query.inventory_type = "ALL";
  } else if (booksStore.filters.inventory_type && booksStore.filters.inventory_type !== "PRIMARY") {
    query.inventory_type = booksStore.filters.inventory_type;
  }
  if (booksStore.filters.q) {
    query.q = booksStore.filters.q;
  }
  if (booksStore.filters.binding_authenticated !== undefined) {
    query.binding_authenticated = String(booksStore.filters.binding_authenticated);
  }

  // Set flag to prevent watch from firing
  isUpdatingUrl.value = true;
  router.replace({ query }).finally(() => {
    // Reset flag after URL update completes
    setTimeout(() => {
      isUpdatingUrl.value = false;
    }, 100);
  });
}

function applyFilters() {
  booksStore.setFilters(booksStore.filters);
  updateUrlWithFilters();
}

function clearFilters() {
  booksStore.filters = { inventory_type: booksStore.filters.inventory_type };
  booksStore.setFilters(booksStore.filters);
  updateUrlWithFilters();
}

function toggleSort(field: string) {
  if (booksStore.sortBy === field) {
    booksStore.setSort(field, booksStore.sortOrder === "asc" ? "desc" : "asc");
  } else {
    booksStore.setSort(field, field === "value_mid" || field === "created_at" ? "desc" : "asc");
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function viewBook(id: number) {
  router.push(`/books/${id}`);
}

function openCarousel(bookId: number) {
  carouselBookId.value = bookId;
  carouselVisible.value = true;
}

function closeCarousel() {
  carouselVisible.value = false;
  carouselBookId.value = null;
}
</script>

<template>
  <div>
    <!-- Header with Search -->
    <div class="flex flex-col gap-3 mb-4 sm:mb-6">
      <!-- Title row -->
      <div class="flex justify-between items-center">
        <h1 class="text-xl sm:text-3xl font-bold text-gray-800">Collection</h1>
        <RouterLink to="/books/new" class="btn-primary text-sm px-3 py-1.5 sm:px-4 sm:py-2">
          + Add
        </RouterLink>
      </div>

      <!-- Search bar - stacked on mobile -->
      <div class="flex flex-col sm:flex-row gap-2">
        <div class="relative flex-1 flex gap-2">
          <div class="relative flex-1">
            <svg
              class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              v-model="booksStore.filters.q"
              type="text"
              placeholder="Search..."
              class="input pl-9 sm:pl-10 w-full text-sm sm:text-base"
              @keyup.enter="applyFilters"
            />
          </div>
          <button
            @click="applyFilters"
            class="btn-primary px-3 sm:px-4 text-sm"
            :disabled="booksStore.loading"
          >
            <svg class="w-4 h-4 sm:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <span class="hidden sm:inline">Search</span>
          </button>
        </div>
        <select
          v-model="booksStore.filters.inventory_type"
          @change="applyFilters"
          class="input text-sm sm:text-base w-full sm:w-40"
        >
          <option value="">All Collections</option>
          <option value="PRIMARY">Primary</option>
          <option value="EXTENDED">Extended</option>
        </select>
      </div>
    </div>

    <!-- Filter & Sort Bar -->
    <div class="flex items-center gap-2 sm:gap-4 mb-4 sm:mb-6 p-2 sm:p-4 bg-gray-50 rounded-lg">
      <!-- Filter Toggle Button -->
      <button
        @click="showFilters = !showFilters"
        class="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-1.5 sm:py-2 bg-white border rounded-lg hover:bg-gray-100 transition-colors text-sm"
      >
        <svg class="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
          />
        </svg>
        <span class="hidden sm:inline">Filters</span>
        <span
          v-if="activeFilterCount > 0"
          class="px-1.5 py-0.5 text-xs bg-moxon-600 text-white rounded-full"
        >
          {{ activeFilterCount }}
        </span>
      </button>

      <!-- Sort - Dropdown on mobile, buttons on desktop -->
      <div class="flex items-center gap-2">
        <!-- Mobile: Sort dropdown -->
        <select
          v-model="booksStore.sortBy"
          @change="booksStore.setSort(booksStore.sortBy, booksStore.sortOrder)"
          class="sm:hidden input text-sm py-1.5"
        >
          <option v-for="option in sortOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <button
          @click="
            booksStore.setSort(booksStore.sortBy, booksStore.sortOrder === 'asc' ? 'desc' : 'asc')
          "
          class="sm:hidden px-2 py-1.5 bg-white border rounded-lg text-sm"
        >
          {{ booksStore.sortOrder === "asc" ? "↑" : "↓" }}
        </button>

        <!-- Desktop: Sort buttons -->
        <span class="hidden sm:inline text-sm text-gray-600">Sort:</span>
        <div class="hidden sm:flex gap-1">
          <button
            v-for="option in sortOptions"
            :key="option.value"
            @click="toggleSort(option.value)"
            class="px-3 py-1.5 text-sm rounded-lg transition-colors"
            :class="
              booksStore.sortBy === option.value
                ? 'bg-moxon-600 text-white'
                : 'bg-white border hover:bg-gray-100'
            "
          >
            {{ option.label }}
            <span v-if="booksStore.sortBy === option.value" class="ml-1">
              {{ booksStore.sortOrder === "asc" ? "↑" : "↓" }}
            </span>
          </button>
        </div>
      </div>

      <!-- Results count -->
      <div class="ml-auto text-xs sm:text-sm text-gray-600">{{ booksStore.total }}</div>
    </div>

    <!-- Expandable Filter Panel -->
    <div v-if="showFilters" class="mb-6 p-4 bg-white border rounded-lg shadow-xs">
      <!-- Row 1: Reference Filters -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-4">
        <!-- Binder Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Bindery</label>
          <select v-model="booksStore.filters.binder_id" class="input text-sm">
            <option :value="undefined">All Binderies</option>
            <option v-for="binder in referencesStore.binders" :key="binder.id" :value="binder.id">
              {{ binder.name }} ({{ binder.book_count }})
            </option>
          </select>
        </div>

        <!-- Publisher Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Publisher</label>
          <select v-model="booksStore.filters.publisher_id" class="input text-sm">
            <option :value="undefined">All Publishers</option>
            <option
              v-for="pub in referencesStore.publishers.filter((p) => p.book_count > 0)"
              :key="pub.id"
              :value="pub.id"
            >
              {{ pub.name }} ({{ pub.book_count }})
            </option>
          </select>
        </div>

        <!-- Publisher Tier Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Publisher Tier</label>
          <select v-model="booksStore.filters.publisher_tier" class="input text-sm">
            <option :value="undefined">All Tiers</option>
            <option v-for="tier in publisherTiers" :key="tier" :value="tier">
              {{ tier }}
            </option>
          </select>
        </div>

        <!-- Binding Type Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Binding Type</label>
          <select v-model="booksStore.filters.binding_type" class="input text-sm">
            <option :value="undefined">All Types</option>
            <option v-for="type in bindingTypes" :key="type" :value="type">
              {{ type }}
            </option>
          </select>
        </div>

        <!-- Authenticated Binding Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Premium Binding</label>
          <select v-model="booksStore.filters.binding_authenticated" class="input text-sm">
            <option :value="undefined">Any</option>
            <option :value="true">Authenticated Only</option>
            <option :value="false">Non-Authenticated</option>
          </select>
        </div>

        <!-- Condition Grade Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Condition</label>
          <select v-model="booksStore.filters.condition_grade" class="input text-sm">
            <option :value="undefined">Any Condition</option>
            <option v-for="grade in conditionGrades" :key="grade" :value="grade">
              {{ grade }}
            </option>
          </select>
        </div>
      </div>

      <!-- Row 2: Status, Images, Analysis, Date/Value Ranges -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <!-- Status Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
          <select v-model="booksStore.filters.status" class="input text-sm">
            <option value="">All Statuses</option>
            <option value="ON_HAND">On Hand</option>
            <option value="IN_TRANSIT">In Transit</option>
            <option value="SOLD">Sold</option>
          </select>
        </div>

        <!-- Has Images Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Images</label>
          <select v-model="booksStore.filters.has_images" class="input text-sm">
            <option :value="undefined">Any</option>
            <option :value="true">With Images</option>
            <option :value="false">Missing Images</option>
          </select>
        </div>

        <!-- Has Analysis Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Analysis</label>
          <select v-model="booksStore.filters.has_analysis" class="input text-sm">
            <option :value="undefined">Any</option>
            <option :value="true">With Analysis</option>
            <option :value="false">Missing Analysis</option>
          </select>
        </div>

        <!-- Has Provenance Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Provenance</label>
          <select v-model="booksStore.filters.has_provenance" class="input text-sm">
            <option :value="undefined">Any</option>
            <option :value="true">With Provenance</option>
            <option :value="false">No Provenance</option>
          </select>
        </div>

        <!-- Provenance Tier Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Provenance Tier</label>
          <select v-model="booksStore.filters.provenance_tier" class="input text-sm">
            <option :value="undefined">Any</option>
            <option v-for="tier in provenanceTiers" :key="tier" :value="tier">
              {{ tier }}
            </option>
          </select>
        </div>

        <!-- First Edition Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">First Edition</label>
          <select v-model="booksStore.filters.is_first_edition" class="input text-sm">
            <option :value="undefined">Any</option>
            <option :value="true">First Editions Only</option>
            <option :value="false">Not First Edition</option>
          </select>
        </div>
      </div>

      <!-- Row 3: Year Range and Value Range -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mt-4">
        <!-- Year Range -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Year Range</label>
          <div class="flex gap-1">
            <input
              v-model.number="booksStore.filters.year_start"
              type="number"
              placeholder="From"
              class="input text-sm w-1/2"
              min="1400"
              max="2025"
            />
            <input
              v-model.number="booksStore.filters.year_end"
              type="number"
              placeholder="To"
              class="input text-sm w-1/2"
              min="1400"
              max="2025"
            />
          </div>
        </div>

        <!-- Value Range -->
        <div class="lg:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Value Range ($)</label>
          <div class="flex gap-1">
            <input
              v-model.number="booksStore.filters.min_value"
              type="number"
              placeholder="Min"
              class="input text-sm w-1/2"
              min="0"
              step="50"
            />
            <input
              v-model.number="booksStore.filters.max_value"
              type="number"
              placeholder="Max"
              class="input text-sm w-1/2"
              min="0"
              step="50"
            />
          </div>
        </div>
      </div>

      <!-- Filter Actions -->
      <div class="flex gap-2 mt-4 pt-4 border-t">
        <button @click="applyFilters" class="btn-primary text-sm">Apply Filters</button>
        <button @click="clearFilters" class="btn-secondary text-sm">Clear Filters</button>
      </div>
    </div>

    <!-- Loading state - skeleton cards -->
    <div v-if="booksStore.loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="n in 6" :key="n" class="card">
        <div class="flex gap-4">
          <div class="skeleton skeleton-image w-24 h-32"></div>
          <div class="flex-1">
            <div class="skeleton skeleton-title mb-2"></div>
            <div class="skeleton skeleton-text w-3/4"></div>
            <div class="skeleton skeleton-text w-1/2"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Books grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="book in booksStore.books"
        :key="book.id"
        class="card card-interactive cursor-pointer"
      >
        <div class="flex gap-4">
          <!-- Thumbnail -->
          <div class="w-24 shrink-0">
            <BookThumbnail
              :book-id="book.id"
              :image-url="book.primary_image_url"
              @click="openCarousel(book.id)"
            />
          </div>

          <!-- Book info -->
          <div class="flex-1 min-w-0" @click="viewBook(book.id)">
            <h3 class="text-lg font-semibold text-gray-800 line-clamp-2">
              {{ book.title }}
            </h3>
            <p class="text-gray-600 mt-1">
              {{ book.author?.name || "Unknown Author" }}
            </p>
            <p class="text-sm text-gray-500 mt-1">
              {{ book.publisher?.name }} ({{ book.publication_date }})
            </p>

            <div class="flex items-center justify-between mt-3">
              <span class="text-sm text-gray-600">
                {{ formatDate(book.purchase_date) }}
              </span>
              <div class="flex items-center gap-1">
                <span
                  v-if="book.binding_authenticated"
                  class="px-2 py-1 text-xs bg-victorian-burgundy text-white rounded-sm"
                  :title="book.binder?.name"
                >
                  {{ book.binder?.name }}
                </span>
                <span
                  v-if="book.volumes > 1"
                  class="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded-sm"
                >
                  {{ book.volumes }} vols
                </span>
                <span
                  v-if="book.has_analysis"
                  class="px-1.5 py-1 text-xs bg-green-100 text-green-700 rounded-sm"
                  title="Has analysis"
                >
                  A
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="booksStore.totalPages > 1" class="flex justify-center mt-8 gap-2">
      <button
        @click="booksStore.setPage(booksStore.page - 1)"
        :disabled="booksStore.page === 1"
        class="btn-secondary disabled:opacity-50"
      >
        Previous
      </button>
      <span class="px-4 py-2"> Page {{ booksStore.page }} of {{ booksStore.totalPages }} </span>
      <button
        @click="booksStore.setPage(booksStore.page + 1)"
        :disabled="booksStore.page === booksStore.totalPages"
        class="btn-secondary disabled:opacity-50"
      >
        Next
      </button>
    </div>

    <!-- Image Carousel Modal -->
    <ImageCarousel
      v-if="carouselBookId"
      :book-id="carouselBookId"
      :visible="carouselVisible"
      @close="closeCarousel"
    />
  </div>
</template>
