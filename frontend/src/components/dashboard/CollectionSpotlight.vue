<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/services/api";

// Spotlight book interface - matches API response (flat fields)
interface SpotlightBook {
  id: number;
  title: string;
  author_name: string | null;
  value_mid: number | null;
  primary_image_url: string | null;
  binder_name: string | null;
  binding_authenticated: boolean;
  binding_type: string | null;
  year_start: number | null;
  year_end: number | null;
  publisher_name: string | null;
  category: string | null;
}

const router = useRouter();

// State
const spotlightBooks = ref<SpotlightBook[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Constants
const SPOTLIGHT_COUNT = 3;
const SPOTLIGHT_LIMIT = 34; // Fetch top books from /books/top endpoint
const CACHE_KEY = "bmx_spotlight_cache";
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 500;

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

// Shuffle array (Fisher-Yates) with true random - different on each page load
function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

// Retry wrapper for API calls
async function withRetry<T>(
  fn: () => Promise<T>,
  retries: number = MAX_RETRIES,
  delay: number = RETRY_DELAY_MS
): Promise<T> {
  let lastError: Error | null = null;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (e) {
      lastError = e instanceof Error ? e : new Error(String(e));
      if (attempt < retries) {
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }
  throw lastError;
}

// Cache interface
interface SpotlightCache {
  books: SpotlightBook[];
  timestamp: number;
}

// Get cached data if valid
function getCachedBooks(): SpotlightBook[] | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;

    const data: SpotlightCache = JSON.parse(cached);
    const age = Date.now() - data.timestamp;
    if (age > CACHE_TTL_MS) {
      localStorage.removeItem(CACHE_KEY);
      return null;
    }
    return data.books;
  } catch {
    localStorage.removeItem(CACHE_KEY);
    return null;
  }
}

// Save books to cache
function setCachedBooks(books: SpotlightBook[]): void {
  try {
    const data: SpotlightCache = {
      books,
      timestamp: Date.now(),
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(data));
  } catch {
    // Ignore storage errors (e.g., quota exceeded)
  }
}

// Fetch spotlight books using /books/top endpoint
async function fetchSpotlightBooks(): Promise<void> {
  loading.value = true;
  error.value = null;

  try {
    // Check cache first
    const cachedBooks = getCachedBooks();
    let topBooks: SpotlightBook[];

    if (cachedBooks) {
      topBooks = cachedBooks;
    } else {
      // Fetch from API with retry logic
      const response = await withRetry(() =>
        api.get("/books/top", {
          params: { limit: SPOTLIGHT_LIMIT },
        })
      );

      topBooks = response.data; // /books/top returns array directly
      setCachedBooks(topBooks);
    }

    // Shuffle randomly and pick spotlight books (different on each page load)
    const shuffled = shuffleArray(topBooks);
    spotlightBooks.value = shuffled.slice(0, SPOTLIGHT_COUNT);
  } catch (e: unknown) {
    const message =
      e instanceof Error
        ? `Failed to load spotlight books: ${e.message}`
        : "Failed to load spotlight books. Please try again later.";
    error.value = message;
  } finally {
    loading.value = false;
  }
}

// High-quality binding keywords (show binder even if not authenticated)
const PREMIUM_BINDING_KEYWORDS = [
  "calf",
  "morocco",
  "levant",
  "vellum",
  "crushed",
  "tree calf",
  "polished calf",
];

// Check if book has notable binding worth displaying
const hasNotableBinding = (book: SpotlightBook): boolean => {
  // Always show if authenticated with known binder
  if (book.binding_authenticated && book.binder_name) {
    return true;
  }
  // Show if binding type contains premium keywords
  if (book.binding_type) {
    const bindingLower = book.binding_type.toLowerCase();
    return PREMIUM_BINDING_KEYWORDS.some((kw) => bindingLower.includes(kw));
  }
  return false;
};

// Get binding display text
const getBindingDisplay = (book: SpotlightBook): string => {
  if (book.binding_authenticated && book.binder_name) {
    return book.binder_name;
  }
  // For non-authenticated premium bindings, show binding type
  return book.binding_type || "";
};

// Format year display
const formatYear = (book: SpotlightBook): string => {
  if (!book.year_start) return "";
  if (book.year_end && book.year_end !== book.year_start) {
    return `${book.year_start}-${book.year_end}`;
  }
  return String(book.year_start);
};

// Get image URL with fallback
const getImageUrl = (book: SpotlightBook): string => {
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

          <!-- Notable Binding Badge -->
          <div
            v-if="hasNotableBinding(book)"
            class="absolute top-2 left-2 bg-victorian-burgundy text-victorian-paper-cream text-xs px-2 py-0.5 rounded-xs font-medium shadow-sm max-w-[calc(100%-1rem)] truncate"
          >
            {{ getBindingDisplay(book) }}
          </div>

          <!-- Category Badge -->
          <div
            v-if="book.category"
            class="absolute bottom-2 left-2 bg-victorian-hunter-800/90 text-victorian-paper-cream text-xs px-2 py-0.5 rounded-xs font-medium shadow-sm"
          >
            {{ book.category }}
          </div>
        </div>

        <!-- Book Info -->
        <div class="space-y-1">
          <!-- Title -->
          <h3 class="text-base font-display text-victorian-ink-black line-clamp-2 leading-tight">
            {{ book.title }}
          </h3>

          <!-- Author & Year -->
          <p class="text-sm text-victorian-ink-muted truncate">
            <span v-if="book.author_name">{{ book.author_name }}</span>
            <span v-if="book.author_name && formatYear(book)" class="mx-1">·</span>
            <span v-if="formatYear(book)">{{ formatYear(book) }}</span>
          </p>

          <!-- Publisher -->
          <p v-if="book.publisher_name" class="text-xs text-victorian-ink-muted/70 truncate">
            {{ book.publisher_name }}
          </p>

          <!-- Value (FMV) -->
          <p v-if="book.value_mid" class="text-lg font-display text-victorian-gold-dark">
            {{ formatCurrency(book.value_mid) }}
            <span class="text-xs text-victorian-ink-muted font-sans ml-1">FMV</span>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
