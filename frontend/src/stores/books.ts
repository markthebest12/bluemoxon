import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { api } from "@/services/api";

export interface Book {
  id: number;
  title: string;
  author: { id: number; name: string } | null;
  publisher: { id: number; name: string; tier: string | null } | null;
  binder: { id: number; name: string } | null;
  publication_date: string | null;
  edition: string | null;
  volumes: number;
  category: string | null;
  inventory_type: string;
  binding_type: string | null;
  binding_authenticated: boolean;
  binding_description: string | null;
  condition_grade: string | null;
  condition_notes: string | null;
  value_low: number | null;
  value_mid: number | null;
  value_high: number | null;
  purchase_price: number | null;
  purchase_date: string | null;
  purchase_source: string | null;
  discount_pct: number | null;
  roi_pct: number | null;
  status: string;
  notes: string | null;
  provenance: string | null;
  has_analysis: boolean;
  image_count: number;
  primary_image_url: string | null;
}

interface Filters {
  q?: string;
  inventory_type?: string;
  category?: string;
  status?: string;
  publisher_id?: number;
  publisher_tier?: string;
  author_id?: number;
  binder_id?: number;
  binding_authenticated?: boolean;
  binding_type?: string;
  condition_grade?: string;
  min_value?: number;
  max_value?: number;
  year_start?: number;
  year_end?: number;
  has_images?: boolean;
  has_analysis?: boolean;
  has_provenance?: boolean;
}

export const useBooksStore = defineStore("books", () => {
  const books = ref<Book[]>([]);
  const currentBook = ref<Book | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const page = ref(1);
  const perPage = ref(20);
  const total = ref(0);
  const filters = ref<Filters>({});
  const sortBy = ref("title");
  const sortOrder = ref<"asc" | "desc">("asc");

  const totalPages = computed(() => Math.ceil(total.value / perPage.value));

  async function fetchBooks() {
    loading.value = true;
    error.value = null;
    try {
      const params = {
        page: page.value,
        per_page: perPage.value,
        sort_by: sortBy.value,
        sort_order: sortOrder.value,
        ...filters.value,
      };
      const response = await api.get("/books", { params });
      books.value = response.data.items;
      total.value = response.data.total;
    } catch (e: any) {
      error.value = e.message || "Failed to fetch books";
    } finally {
      loading.value = false;
    }
  }

  async function fetchBook(id: number) {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.get(`/books/${id}`);
      currentBook.value = response.data;
    } catch (e: any) {
      error.value = e.message || "Failed to fetch book";
    } finally {
      loading.value = false;
    }
  }

  async function createBook(bookData: Partial<Book>) {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.post("/books", bookData);
      return response.data;
    } catch (e: any) {
      error.value = e.message || "Failed to create book";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateBook(id: number, bookData: Partial<Book>) {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.put(`/books/${id}`, bookData);
      currentBook.value = response.data;
      return response.data;
    } catch (e: any) {
      error.value = e.message || "Failed to update book";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function deleteBook(id: number) {
    loading.value = true;
    error.value = null;
    try {
      await api.delete(`/books/${id}`);
    } catch (e: any) {
      error.value = e.message || "Failed to delete book";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateAnalysis(bookId: number, markdown: string) {
    try {
      await api.put(`/books/${bookId}/analysis`, markdown, {
        headers: { "Content-Type": "text/plain" },
      });
      // Update has_analysis flag on current book if loaded
      if (currentBook.value && currentBook.value.id === bookId) {
        currentBook.value.has_analysis = true;
      }
    } catch (e: any) {
      error.value = e.message || "Failed to update analysis";
      throw e;
    }
  }

  async function generateAnalysis(
    bookId: number,
    model: "sonnet" | "opus" = "sonnet"
  ): Promise<{
    id: number;
    book_id: number;
    model_used: string;
    full_markdown: string;
    generated_at: string;
  }> {
    const response = await api.post(`/books/${bookId}/analysis/generate`, {
      model,
    });

    // Update currentBook if it matches
    if (currentBook.value?.id === bookId) {
      currentBook.value.has_analysis = true;
    }

    return response.data;
  }

  function setFilters(newFilters: Filters) {
    filters.value = newFilters;
    page.value = 1;
    fetchBooks();
  }

  function setSort(field: string, order: "asc" | "desc") {
    sortBy.value = field;
    sortOrder.value = order;
    fetchBooks();
  }

  function setPage(newPage: number) {
    page.value = newPage;
    fetchBooks();
  }

  return {
    books,
    currentBook,
    loading,
    error,
    page,
    perPage,
    total,
    totalPages,
    filters,
    sortBy,
    sortOrder,
    fetchBooks,
    fetchBook,
    createBook,
    updateBook,
    deleteBook,
    updateAnalysis,
    generateAnalysis,
    setFilters,
    setSort,
    setPage,
  };
});
