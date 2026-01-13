<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/services/api";
import type { Book } from "@/stores/books";

const router = useRouter();

// State
const spotlightBooks = ref<Book[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Constants
const SPOTLIGHT_COUNT = 3;
const TOP_PERCENT = 0.2; // Top 20%
const PAGE_SIZE = 20; // API default page size

// Use API placeholder for books without images
const API_URL = import.meta.env.VITE_API_URL || "/api/v1";
const placeholderUrl = `${API_URL}/images/placeholder`;

// Format currency
function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
  }).format(value);
}

// Navigate to book detail
function navigateToBook(bookId: number, event?: MouseEvent): void {
  const url = `/books/${bookId}`;
  if (event?.metaKey || event?.ctrlKey) {
    window.open(url, "_blank");
  } else {
    void router.push(url);
  }
}

// Shuffle array (Fisher-Yates)
function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

// Fetch all books and select spotlight
async function fetchSpotlightBooks(): Promise<void> {
  loading.value = true;
  error.value = null;

  try {
    // First, get the first page to know total count
    const firstResponse = await api.get("/books", {
      params: {
        inventory_type: "PRIMARY",
        page: 1,
        per_page: PAGE_SIZE,
      },
    });

    const totalCount = firstResponse.data.total;
    const totalPages = Math.ceil(totalCount / PAGE_SIZE);
    let allBooks: Book[] = firstResponse.data.items;

    // Fetch remaining pages if needed
    if (totalPages > 1) {
      const pagePromises = [];
      for (let page = 2; page <= totalPages; page++) {
        pagePromises.push(
          api.get("/books", {
            params: {
              inventory_type: "PRIMARY",
              page,
              per_page: PAGE_SIZE,
            },
          })
        );
      }

      const responses = await Promise.all(pagePromises);
      for (const response of responses) {
        allBooks = allBooks.concat(response.data.items);
      }
    }

    // Sort by value_mid descending and take top 20%
    const sortedBooks = allBooks
      .filter((book) => book.value_mid !== null && book.value_mid > 0)
      .sort((a, b) => (b.value_mid || 0) - (a.value_mid || 0));

    const topCount = Math.ceil(sortedBooks.length * TOP_PERCENT);
    const pool = sortedBooks.slice(0, topCount);

    // Shuffle and pick spotlight books
    const shuffled = shuffleArray(pool);
    spotlightBooks.value = shuffled.slice(0, SPOTLIGHT_COUNT);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Failed to load spotlight books";
    error.value = message;
  } finally {
    loading.value = false;
  }
}

// Check if book has premium binding
const hasPremiumBinding = (book: Book): boolean => {
  return book.binding_authenticated && book.binder !== null;
};

// Get image URL with fallback
const getImageUrl = (book: Book): string => {
  return book.primary_image_url || placeholderUrl;
};

// Computed for showing skeleton vs content
const showSkeleton = computed(() => loading.value);
const showContent = computed(
  () => !loading.value && !error.value && spotlightBooks.value.length > 0
);
const showEmpty = computed(
  () => !loading.value && !error.value && spotlightBooks.value.length === 0
);

onMounted(() => {
  void fetchSpotlightBooks();
});
</script>

<template>
  <div class="mt-8 md:mt-12">
    <!-- Section Header -->
    <div class="flex items-center gap-3 mb-4">
      <h2 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider">
        Collection Spotlight
      </h2>
      <div class="flex-1 h-px bg-victorian-paper-antique"></div>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="showSkeleton" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
      <div v-for="i in 3" :key="i" class="card-static p-4 animate-pulse">
        <!-- Image skeleton -->
        <div class="aspect-[4/5] w-full bg-victorian-paper-antique rounded-xs mb-3"></div>
        <!-- Title skeleton -->
        <div class="h-5 bg-victorian-paper-antique rounded w-3/4 mb-2"></div>
        <!-- Author skeleton -->
        <div class="h-4 bg-victorian-paper-antique rounded w-1/2 mb-2"></div>
        <!-- Value skeleton -->
        <div class="h-5 bg-victorian-paper-antique rounded w-1/4"></div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="card-static p-6 text-center">
      <p class="text-victorian-burgundy text-sm">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="showEmpty" class="card-static p-6 text-center">
      <p class="text-victorian-ink-muted text-sm">No books available for spotlight</p>
    </div>

    <!-- Spotlight Cards -->
    <div
      v-else-if="showContent"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6"
    >
      <div
        v-for="book in spotlightBooks"
        :key="book.id"
        class="card-static p-4 cursor-pointer hover:ring-2 hover:ring-victorian-hunter-600/30 transition-all"
        @click="navigateToBook(book.id, $event)"
      >
        <!-- Book Thumbnail -->
        <div
          class="aspect-[4/5] w-full relative rounded-xs overflow-hidden bg-victorian-paper-cream border border-victorian-paper-antique mb-3"
        >
          <img
            :src="getImageUrl(book)"
            :alt="book.title"
            loading="lazy"
            decoding="async"
            class="w-full h-full object-cover"
          />

          <!-- Premium Binding Badge -->
          <div
            v-if="hasPremiumBinding(book)"
            class="absolute top-2 left-2 bg-victorian-burgundy text-victorian-paper-cream text-xs px-2 py-0.5 rounded-xs font-medium shadow-sm"
          >
            {{ book.binder?.name }}
          </div>
        </div>

        <!-- Book Info -->
        <div class="space-y-1">
          <!-- Title -->
          <h3 class="text-base font-display text-victorian-ink-black line-clamp-2 leading-tight">
            {{ book.title }}
          </h3>

          <!-- Author -->
          <p v-if="book.author" class="text-sm text-victorian-ink-muted truncate">
            {{ book.author.name }}
          </p>

          <!-- Value -->
          <p v-if="book.value_mid" class="text-lg font-display text-victorian-gold-dark">
            {{ formatCurrency(book.value_mid) }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Line clamp for title truncation */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
